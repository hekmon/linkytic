"""The linkytic integration serial reader."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import cast

import serial
import serial.serialutil
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback

from .const import (
    BYTESIZE,
    CONSTRUCTORS_CODES,
    DATASET_SEPARATOR,
    DEVICE_TYPES,
    DID_CONSTRUCTOR,
    DID_CONSTRUCTOR_CODE,
    DID_REGNUMBER,
    DID_TYPE,
    DID_TYPE_CODE,
    DID_YEAR,
    FRAME_END,
    MODE_HISTORIC_BAUD_RATE,
    MODE_HISTORIC_FIELD_SEPARATOR,
    MODE_STANDARD_BAUD_RATE,
    MODE_STANDARD_FIELD_SEPARATOR,
    OPTIONS_REALTIME,
    PARITY,
    SETUP_PRODUCER,
    SETUP_SERIAL,
    SETUP_THREEPHASE,
    SETUP_TICMODE,
    SHORT_FRAME_DETECTION_TAGS,
    SHORT_FRAME_FORCED_UPDATE_TAGS,
    STOPBITS,
    TICMODE_STANDARD,
)

_LOGGER = logging.getLogger(__name__)


class MalformatedDatasetException(Exception):
    """Dataset is malformated."""

    def __init__(self, raw_dataset: bytes) -> None:
        """Init the exception."""
        self.msg = f"Dataset is malformated: {raw_dataset!r}"
        super().__init__(self.msg)


class InvalidChecksumException(Exception):
    """Checksum of dataset is invalid."""

    def __init__(self, raw_dataset: bytes) -> None:
        """Init the exception."""
        self.msg = f"Dataset checksum is invalid: {raw_dataset!r}"
        super().__init__(self.msg)


@dataclass
class Dataset:
    """Represents a dataset from a Linky TIC frame, containing a tag, value, and timestamp (only for standard)."""

    tag: str
    value: str
    timestamp: str | None

    @classmethod
    def from_raw(cls, raw_dataset: bytes) -> Dataset:
        """Create a dataset from a raw TIC frame line."""
        raise NotImplementedError

    @staticmethod
    def compute_checksum(control_data: bytes) -> int:
        """Compute the checksum of a given control data."""
        return (sum(control_data) & 0x3F) + 0x20


class HistoricDataset(Dataset):
    """Represents a dataset from a historic Linky TIC frame."""

    @classmethod
    def from_raw(cls, raw_dataset: bytes) -> Dataset:
        """Create a dataset from a raw TIC frame line."""
        try:
            (raw_tag, raw_value, raw_checksum) = raw_dataset.split(
                MODE_HISTORIC_FIELD_SEPARATOR
            )
            tag = raw_tag.decode("ascii")
            value = raw_value.decode("ascii")
            checksum = ord(raw_checksum)
            if not 0x20 <= checksum <= 0x5F:
                raise ValueError(  # noqa: TRY301
                    f"Checksum {checksum} is not in the valid range (0x20-0x5F)"
                )

        except (ValueError, TypeError, UnicodeDecodeError) as e:
            raise MalformatedDatasetException(raw_dataset) from e

        if (
            cls.compute_checksum(raw_tag + MODE_HISTORIC_FIELD_SEPARATOR + raw_value)
            != checksum
        ):
            raise InvalidChecksumException(raw_dataset)

        return Dataset(tag, value, None)


class StandardDataset(Dataset):
    """Represents a dataset from a standard Linky TIC frame."""

    @classmethod
    def from_raw(cls, raw_dataset: bytes) -> Dataset:
        """Create a dataset from a raw TIC frame line."""
        try:
            match raw_dataset.split(MODE_STANDARD_FIELD_SEPARATOR):
                case [raw_tag, raw_timestamp, raw_value, raw_checksum]:
                    pass
                case [raw_tag, raw_value, raw_checksum]:
                    raw_timestamp = b""
                case _:
                    raise ValueError(  # noqa: TRY301
                        f"Unexpected number of fields in standard dataset: {raw_dataset!r}"
                    )
            tag = raw_tag.decode("ascii")
            timestamp = raw_timestamp.decode("ascii") if raw_timestamp else None
            value = raw_value.decode("ascii")
            checksum = ord(raw_checksum)
            if not 0x20 <= checksum <= 0x5F:
                raise ValueError(  # noqa: TRY301
                    f"Checksum {checksum} is not in the valid range (0x20-0x5F)"
                )

        except (ValueError, TypeError, UnicodeDecodeError) as e:
            raise MalformatedDatasetException(raw_dataset) from e

        if (
            cls.compute_checksum(
                raw_tag
                + MODE_STANDARD_FIELD_SEPARATOR
                + (
                    raw_timestamp + MODE_STANDARD_FIELD_SEPARATOR
                    if raw_timestamp
                    else b""
                )
                + raw_value
                + MODE_STANDARD_FIELD_SEPARATOR
            )
            != checksum
        ):
            raise InvalidChecksumException(raw_dataset)

        return Dataset(tag, value, timestamp)


class LinkQualityIndicator:
    """Link Quality Indicator, IIR low pass filter."""

    def __init__(self) -> None:
        """Init the IIR filter."""
        self._alpha = 1 / 16
        self._y1 = 1.0
        self._y0 = 1.0

    def update(self, correct: bool) -> None:
        """Update the LQI with a new packet."""
        self._y0 = self._alpha * (1 if correct else 0) + (1 - self._alpha) * self._y1
        self._y1 = self._y0

    def get_value(self) -> int:
        """Get the current LQI value, in percent."""
        return round(self._y0 * 100)


class LinkyTICReader(threading.Thread):
    """Implements the reading of a serial Linky TIC."""

    def __init__(
        self,
        title: str,
        meter: LinkyMeter,
        port: str,
        std_mode: bool,
        producer_mode: bool,
        three_phase: bool,
        real_time: bool | None = False,
    ) -> None:
        """Init the LinkyTIC thread serial reader."""  # Thread
        self._setup_error: Exception | None = None
        self._stopsignal = False
        self._title = title
        self._meter = meter
        # Options
        if real_time is None:
            real_time = False
        self._realtime = real_time
        # Build
        self._port = port
        self._baudrate = (
            MODE_STANDARD_BAUD_RATE if std_mode else MODE_HISTORIC_BAUD_RATE
        )
        self._std_mode = std_mode
        self._producer_mode = producer_mode if std_mode else False
        self._three_phase = three_phase
        # Run
        self._reader: serial.Serial | None = None
        self._values: dict[str, Dataset | None] = {}
        self._dataset_type: type[Dataset] = (
            StandardDataset if std_mode else HistoricDataset
        )
        self._first_read = True
        self._frames_read = -1  # we consider that the first frame will be incomplete
        self._within_short_frame = False
        self._tags_seen: list[str] = []
        self.device_identification: dict[
            str, str | None
        ] = {}  # will be set by the ADCO/ADSC tag
        self._notif_callbacks: dict[str, Callable[[bool], None]] = {}
        # Init parent thread class
        self._serial_number = None
        super().__init__(name=f"LinkyTIC for {title}")

        # Link quality indicator, reset at each reload
        self._lqi = LinkQualityIndicator()

    def get_values(self, tag: str) -> tuple[str | None, str | None]:
        """Get tag value and timestamp from the thread memory cache."""
        if not self.is_connected:
            return None, None

        dataset = self._values.get(tag)
        if dataset:
            return dataset.value, dataset.timestamp
        return None, None

    @property
    def has_read_full_frame(self) -> bool:
        """Use to known if at least one complete frame has been read on the serial connection."""
        return self._frames_read >= 1

    @property
    def is_connected(self) -> bool:
        """Use to know if the reader is actually connected to a serial connection."""
        if self._reader is None:
            return False
        return cast(bool, self._reader.is_open)

    @property
    def serial_number(self) -> str | None:
        """Returns meter serial number (ADSC or ADCO tag)."""
        return self._serial_number

    @property
    def port(self) -> str:
        """Returns serial port."""
        return self._port

    @property
    def setup_error(self) -> Exception | None:
        """If the reader thread terminates due to a serial exception, this property will contain the raised exception."""
        return self._setup_error

    @property
    def link_quality(self) -> int:
        """Returns link quality indicator."""
        return self._lqi.get_value()

    def run(self) -> None:
        """Continuously read the the serial connection and extract TIC values."""

        if not self._open_serial():
            # Serial error, do not start reader thread
            return

        with self._get_serial() as serial:
            while not self._stopsignal:
                # Explicit use of read_until() instead of readline()
                # Frame format is 0x02 (STX) + dataset + ... + 0x03 (ETX)
                # Dataset format depends on historic or standard mode but starts with 0x0A (LF) and ends with 0x0D (CR)
                # Reading until 0x0A (LF) ensure that a full dataset is read, but the format of the raw dataset read is
                # dataset_content + 0x0D (CR) [ + 0x03 (ETX) + 0x02 (STX) ] (if it is the last dataset of the frame) + 0x0A (LF)
                dataset_raw = serial.read_until(b"\n")

                # Parse the line if non empty (prevent errors from read timeout that returns empty byte string)
                if not dataset_raw.rstrip(DATASET_SEPARATOR):
                    continue
                # Skip the first line, which is often a partial line due to the serial connection being opened in the middle of a frame.
                if self._first_read:
                    self._first_read = False
                    continue

                # Parsing raw dataset
                try:
                    dataset = self._dataset_type.from_raw(
                        dataset_raw.rstrip(FRAME_END)
                    )  # stripping FRAME_END will also strip dataset separators
                except (MalformatedDatasetException, InvalidChecksumException) as e:
                    # Silently discard parsing and checksum errors, use the link quality indicator to monitor the quality of the serial connection.
                    _LOGGER.debug(
                        "Failed to parse dataset '%s' from %s: %s",
                        repr(dataset_raw),
                        self._title,
                        e,
                    )
                    self._lqi.update(False)
                    continue

                self._lqi.update(True)
                self._handle_dataset(dataset)

                # Handle end of frame
                if FRAME_END in dataset_raw:
                    if not self._within_short_frame:
                        self._frames_read += 1
                        self._cleanup_cache()
                    self._within_short_frame = False

        # Stop flag as been raised
        _LOGGER.info("Thread stop: closing the serial connection")

    def _handle_dataset(self, dataset: Dataset) -> None:
        """Handle a dataset that has been read from the serial connection."""
        # Mark this tag as seen for end of frame cache cleanup
        self._tags_seen.append(dataset.tag)

        _LOGGER.debug(
            "Parsed dataset from %s: %s -> %s (%s)",
            self._title,
            dataset.tag,
            dataset.value,
            dataset.timestamp,
        )

        # Save in internal cache for async retrieval by sensors
        self._values[dataset.tag] = dataset

        # Parse linky ADS tag for device identification
        if dataset.tag in ("ADSC", "ADCO"):
            self.parse_ads(dataset.value)

        # Detect short frame bursts and switch to forced update mode
        if dataset.tag in SHORT_FRAME_DETECTION_TAGS and not self._within_short_frame:
            self._within_short_frame = True
            _LOGGER.info(
                "Short trame burst detected (%s): switching to forced update mode",
                dataset.tag,
            )

        # Real-time update: call the registered callback
        callback = self._notif_callbacks.get(dataset.tag)
        if callback:
            _LOGGER.debug(
                "We have a notification callback for %s: executing", dataset.tag
            )
            forced_update = (
                self._realtime
                or (
                    self._within_short_frame
                    and dataset.tag in SHORT_FRAME_FORCED_UPDATE_TAGS
                )
                or dataset.tag == "ADPS"
            )
            callback(forced_update)

    def register_push_notif(
        self, tag: str, notif_callback: Callable[[bool], None]
    ) -> None:
        """Call to register a callback notification when a certain tag is parsed."""
        _LOGGER.debug("Registering a callback for %s tag", tag)
        self._notif_callbacks[tag] = notif_callback

    @callback
    def signalstop(self, event: Event | str) -> None:
        """Activate the stop flag in order to stop the thread from within."""
        if self.is_alive():
            _LOGGER.info(
                "Stopping %s serial thread reader (received %s)", self._title, event
            )
            self._stopsignal = True

    def update_options(self, real_time: bool) -> None:
        """Setter to update serial reader options."""
        _LOGGER.debug("%s: new real time option value: %s", self._title, real_time)
        self._realtime = real_time

    def _cleanup_cache(self) -> None:
        """Call to cleanup the data cache to allow some sensors to get back to undefined/unavailable if they are not present in the last frame."""
        for cached_tag in list(self._values.keys()):  # pylint: disable=consider-using-dict-items,consider-iterating-dictionary
            if cached_tag not in self._tags_seen:
                _LOGGER.debug(
                    "tag %s was present in cache but has not been seen in previous frame: removing from cache",
                    cached_tag,
                )
                # Clean serial controller data cache for this tag
                del self._values[cached_tag]
                # Inform entity of a new value available (None) if in push mode
                try:
                    notif_callback = self._notif_callbacks[cached_tag]
                    notif_callback(self._realtime)
                except KeyError:
                    pass
        self._tags_seen = []

    def _open_serial(self) -> bool:
        """Create (and open) the serial connection."""

        # Because we run in the thread context, we need to catch any exceptions and save them to report to the main thread.
        try:
            self._reader = serial.serial_for_url(
                url=self._port,
                baudrate=self._baudrate,
                bytesize=BYTESIZE,
                parity=PARITY,
                stopbits=STOPBITS,
                timeout=1,
            )
        except Exception as e:  # noqa: BLE001
            self._setup_error = e
            self._stopsignal = True
            return False
        else:
            _LOGGER.info("Serial connection is now open at %s", self._port)
            return True

    @contextlib.contextmanager
    def _get_serial(self) -> Generator[serial.Serial]:
        """Serial instance getter, wrapped in a context manager."""
        assert self._reader
        try:
            yield self._reader
        except Exception as e:  # noqa: BLE001
            self._meter.on_connection_lost(e)
        finally:
            self._reader.close()

    def parse_ads(self, ads: str | None) -> None:
        """Extract information contained in the ADS as EURIDIS."""

        # Because S/N is a device identifier, only parse it once.
        if self.serial_number:
            return

        if not ads or len(ads) != 12:
            _LOGGER.error(
                "%s: ADS should be 12 char long, actually %d cannot parse: %s",
                self._title,
                len(ads or ""),
                ads,
            )
            return

        # Save serial number
        self._serial_number = ads  # type: ignore[assignment]  # mypy complains because we checked prior that self._serial_number is None
        self._meter.on_connection_made()
        # let's parse ADS as EURIDIS
        const_code = ads[0:2]
        type_code = ads[4:6]

        device_identification = {
            DID_YEAR: ads[2:4],
            DID_REGNUMBER: ads[6:],
            DID_CONSTRUCTOR_CODE: const_code,
            DID_CONSTRUCTOR: CONSTRUCTORS_CODES.get(const_code),
            DID_TYPE_CODE: type_code,
            DID_TYPE: DEVICE_TYPES.get(type_code),
        }

        self.device_identification = device_identification
        # Parsing done
        _LOGGER.debug(
            "%s: parsed ADS: %s", self._title, repr(self.device_identification)
        )


class LinkyMeter:
    """Linky energy meter representation, for interacting with Home Assistant."""

    _reader: LinkyTICReader
    _hass: HomeAssistant
    _config: ConfigEntry

    def __init__(self) -> None:
        """Instantiation of a meter, from_config must be used."""
        self._update_callbacks: dict[str, Callable[[bool], None]] = {}
        self._connected = asyncio.Event()

    @classmethod
    async def probe_serial_number(cls, port: str, mode: bool) -> str:
        """Probes a serial connection for a meter, and return its S/N if found.

        Raise LINKY_IO_ERROR or TimeoutError on failure.
        """

        meter = cls()
        meter._reader = LinkyTICReader("Probe", meter, port, mode, False, False)
        s_n = await meter._connect_and_wait_for_serial_number()
        await meter.disconnect(Event("probe_end"))
        return s_n

    @classmethod
    async def connect_from_config(
        cls, hass: HomeAssistant, config: ConfigEntry
    ) -> LinkyMeter:
        """Connects to a meter from a given entry configuration. Return the meter when a serial number has been read.

        Raise LINKY_IO_ERROR or TimeoutError on failure.
        """

        meter = cls()
        meter._hass = hass
        meter._config = config
        meter._reader = LinkyTICReader(
            title=config.title,
            meter=meter,
            port=config.data[SETUP_SERIAL],
            std_mode=config.data[SETUP_TICMODE] == TICMODE_STANDARD,
            three_phase=config.data.get(SETUP_THREEPHASE, False),
            producer_mode=config.data.get(SETUP_PRODUCER, False),
            real_time=config.options.get(OPTIONS_REALTIME, False),
        )
        await meter._connect_and_wait_for_serial_number()
        return meter

    async def _connect_and_wait_for_serial_number(self) -> str:
        """Coroutine for waiting for the serial number to be read by the reader thread."""
        assert self._reader is not None
        async with asyncio.timeout(5):
            self._reader.start()
            # If there is a S/N, the reader is connected successfully
            while not self._reader.serial_number:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._connected.wait(), 1)
                # Check for any exception in the thread
                if self._reader.setup_error:
                    raise self._reader.setup_error
            return self._reader.serial_number

    async def disconnect(self, event: Event) -> None:
        """Disconnect the meter."""
        self._reader.signalstop(event)
        # TODO: graceful terminate?

    @callback
    def get_value(self, tag: str) -> tuple[str | None, str | None]:
        """Get the value (and/or timestamp) for a given tag."""
        return self._reader.get_values(tag)

    @property
    def name(self) -> str:
        """Return the name of the reader."""
        return self._config.title

    @property
    def is_connected(self) -> bool:
        """Return whether connection is active or not."""
        return self._reader.is_connected

    @property
    def serial_number(self) -> str:
        """Return the serial number of the linky meter."""
        assert self._reader.serial_number
        return self._reader.serial_number

    @property
    def device_identification(self) -> dict[str, str | None]:
        """Return the device identification, derived from its serial number."""
        return self._reader.device_identification

    @property
    def link_quality_indicator(self) -> int:
        """Return the reader LQI, in percent."""
        return self._reader.link_quality

    @property
    def is_tic_mode_standard(self) -> bool:
        """Return whether the tic is in standard (True) or historic (False) mode."""
        return bool(self._config.data[SETUP_TICMODE] == TICMODE_STANDARD)

    @callback
    def register_update_callback(
        self, tag: str, callback: Callable[[bool], None]
    ) -> None:
        """Register a callback for the given tag. Overwrites any precedent registered callback."""
        self._update_callbacks[tag] = callback

    @callback
    def update_options(self) -> None:
        """Callback for HASS to signal that config options has been updated."""
        self._reader.update_options(self._config.options.get(OPTIONS_REALTIME, False))

    def on_connection_made(self) -> None:
        """Callback for the reader when connection has been established (serial number read)."""
        # Wrap asyncio.Event.set in a callback so HA calls it from the event loop and not from an executor
        # that would result in a non-thread-safe call from another thread.
        self._hass.add_job(callback(lambda: self._connected.set()))

    def on_connection_lost(self, e: Exception) -> None:
        """Callback for the reader when connection has been lost."""
        if self._connected.is_set():
            _LOGGER.warning("Connection to Linky meter has been lost: %s", e)
            self._hass.add_job(
                self._hass.config_entries.async_schedule_reload, self._config.entry_id
            )

    def on_frame_read(self) -> None:
        """Callback for the reader when a frame has been read."""
