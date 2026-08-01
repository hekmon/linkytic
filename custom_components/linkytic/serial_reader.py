"""The linkytic integration serial reader."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

import serial
import serial.serialutil
from homeassistant.core import Event, callback

from .const import (
    BYTESIZE,
    CONSTRUCTORS_CODES,
    DEVICE_TYPES,
    DID_CONSTRUCTOR,
    DID_CONSTRUCTOR_CODE,
    DID_REGNUMBER,
    DID_TYPE,
    DID_TYPE_CODE,
    DID_YEAR,
    FRAME_END,
    LINKY_IO_ERRORS,
    MODE_HISTORIC_BAUD_RATE,
    MODE_HISTORIC_FIELD_SEPARATOR,
    MODE_STANDARD_BAUD_RATE,
    MODE_STANDARD_FIELD_SEPARATOR,
    PARITY,
    SHORT_FRAME_DETECTION_TAGS,
    SHORT_FRAME_FORCED_UPDATE_TAGS,
    STOPBITS,
)

_LOGGER = logging.getLogger(__name__)


class MalformatedDatasetException(Exception):
    pass


class InvalidChecksumException(Exception):
    pass


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
        sum1 = 0
        for byte in control_data:
            sum1 += byte
        truncated = sum1 & 0x3F
        computed_checksum = truncated + 0x20
        return computed_checksum


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
                raise ValueError(
                    f"Checksum {checksum} is not in the valid range (0x20-0x5F)"
                )

        except (ValueError, TypeError, UnicodeDecodeError) as e:
            raise MalformatedDatasetException from e

        if (
            cls.compute_checksum(raw_tag + MODE_HISTORIC_FIELD_SEPARATOR + raw_value)
            != checksum
        ):
            raise InvalidChecksumException(tag, value, checksum)

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
                    raise ValueError(
                        f"Unexpected number of fields in standard dataset: {raw_dataset!r}"
                    )
            tag = raw_tag.decode("ascii")
            timestamp = raw_timestamp.decode("ascii") if raw_timestamp else None
            value = raw_value.decode("ascii")
            checksum = ord(raw_checksum)
            if not 0x20 <= checksum <= 0x5F:
                raise ValueError(
                    f"Checksum {checksum} is not in the valid range (0x20-0x5F)"
                )

        except (ValueError, TypeError, UnicodeDecodeError) as e:
            raise MalformatedDatasetException from e

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
            raise InvalidChecksumException(tag, value, checksum)

        return Dataset(tag, value, timestamp)


class LinkyTICReader(threading.Thread):
    """Implements the reading of a serial Linky TIC."""

    def __init__(
        self,
        title: str,
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
        self.device_identification: dict[str, str | None] = {
            DID_CONSTRUCTOR: None,
            DID_REGNUMBER: None,
            DID_TYPE: None,
            DID_YEAR: None,
        }  # will be set by the ADCO/ADSC tag
        self._notif_callbacks: dict[str, Callable[[bool], None]] = {}
        # Init parent thread class
        self._serial_number = None
        super().__init__(name=f"LinkyTIC for {title}")

        # Link quality indicator, reset at each reload
        self._dataset_total_read = 0
        self._dataset_total_error = 0

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
    def link_quality(self) -> int | None:
        """Returns link quality indicator."""
        if self._dataset_total_read == 0:
            return None
        return round(
            (self._dataset_total_read - self._dataset_total_error)
            / self._dataset_total_read
            * 100
        )

    def run(self) -> None:
        """Continuously read the the serial connection and extract TIC values."""

        if not self._open_serial():
            # Serial error, do not start reader thread
            return

        while not self._stopsignal:
            # Reader should have been opened.
            assert self._reader is not None
            if not self._reader.is_open:
                # NOTE: implement a maximum retry, and go in failure mode if the connection can't be renewed?
                try:
                    self._reader.open()
                except LINKY_IO_ERRORS:
                    time.sleep(5)  # Cooldown to prevent spamming logs.
                    _LOGGER.warning("Could not open serial port")
                    continue
            try:
                # Explicit use of read_until() instead of readline()
                # Frame format is 0x02 (STX) + dataset + ... + 0x03 (ETX)
                # Dataset format depends on historic or standard mode but starts with 0x0A (LF) and ends with 0x0D (CR)
                # Reading until 0x0A (LF) ensure that a full dataset is read, but the format of the raw dataset read is
                # dataset_content + 0x0D (CR) [ + 0x03 (ETX) + 0x02 (STX) ] (if it is the last dataset of the frame) + 0x0A (LF)
                dataset_raw = self._reader.read_until(b"\n")
            except LINKY_IO_ERRORS as exc:
                _LOGGER.error(
                    "Connection lost with device %s: %s. Will retry in 5s",
                    self._port,
                    exc,
                )
                self._reset_state()
                self._reader.close()
                continue

            # Parse the line if non empty (prevent errors from read timeout that returns empty byte string)
            if not dataset_raw:
                continue
            # Skip the first line, which is often a partial line due to the serial connection being opened in the middle of a frame.
            if self._first_read:
                self._first_read = False
                continue

            self._dataset_total_read += 1
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
                self._dataset_total_error += 1
                continue

            self._handle_dataset(dataset)

            # Handle end of frame
            if FRAME_END in dataset_raw:
                if not self._within_short_frame:
                    self._frames_read += 1
                    self._cleanup_cache()
                self._within_short_frame = False

        # Stop flag as been raised
        _LOGGER.info("Thread stop: closing the serial connection")
        if self._reader:
            self._reader.close()

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
        self._reset_state()

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

    def _reset_state(self) -> None:
        """Reinitialize the controller (by nullifying it) and wait 5s for other methods to re start init after a pause."""
        _LOGGER.debug("Resetting serial reader state and wait 10s")
        self._values = {}
        self._serial_number = None
        # Inform sensor in push mode to come fetch data (will get None and switch to unavailable)
        for notif_callback in self._notif_callbacks.values():
            notif_callback(self._realtime)
        self._first_read = True
        self._frames_read = -1
        self._within_short_frame = False
        self.device_identification = {
            DID_CONSTRUCTOR: None,
            DID_CONSTRUCTOR_CODE: None,
            DID_REGNUMBER: None,
            DID_TYPE: None,
            DID_TYPE_CODE: None,
            DID_YEAR: None,
        }

    def parse_ads(self, ads: str | None) -> None:
        """Extract information contained in the ADS as EURIDIS."""
        _LOGGER.debug(
            "%s: parsing ADS: %s",
            self._title,
            ads,
        )
        if ads is None or len(ads) != 12:
            _LOGGER.error(
                "%s: ADS should be 12 char long, actually %d cannot parse: %s",
                self._title,
                len(ads or ""),
                ads,
            )
            return

        # Because S/N is a device identifier, only parse it once.
        if self.serial_number:
            return

        # Save serial number
        self._serial_number = ads  # type: ignore[assignment]  # mypy complains because we checked prior that self._serial_number is None

        # let's parse ADS as EURIDIS
        device_identification: dict[str, str | None] = {
            DID_YEAR: ads[2:4],
            DID_REGNUMBER: ads[6:],
        }
        const_code = ads[0:2]
        type_code = ads[4:6]

        # # Parse constructor code

        device_identification[DID_CONSTRUCTOR_CODE] = const_code
        try:
            device_identification[DID_CONSTRUCTOR] = CONSTRUCTORS_CODES[const_code]
        except KeyError:
            _LOGGER.warning(
                "%s: constructor code is unknown: %s",
                self._title,
                device_identification[DID_CONSTRUCTOR_CODE],
            )
            device_identification[DID_CONSTRUCTOR] = None
        # # Parse device type code
        device_identification[DID_TYPE_CODE] = type_code
        try:
            device_identification[DID_TYPE] = f"{DEVICE_TYPES[type_code]}"
        except KeyError:
            _LOGGER.warning(
                "%s: ADS device type is unknown: %s",
                self._title,
                device_identification[DID_TYPE_CODE],
            )
            device_identification[DID_TYPE] = None
        # # Update device infos
        self.device_identification = device_identification
        # Parsing done
        _LOGGER.debug(
            "%s: parsed ADS: %s", self._title, repr(self.device_identification)
        )
