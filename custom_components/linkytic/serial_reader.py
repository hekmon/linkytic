"""The linkytic integration serial reader."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import serialx
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
    MODE_HISTORIC_BAUD_RATE,
    MODE_HISTORIC_FIELD_SEPARATOR,
    MODE_STANDARD_BAUD_RATE,
    MODE_STANDARD_FIELD_SEPARATOR,
    OPTIONS_REALTIME,
    PARITY,
    SETUP_SERIAL,
    SETUP_TICMODE,
    SHORT_FRAME_DETECTION_TAGS,
    SHORT_FRAME_FORCED_UPDATE_TAGS,
    STOPBITS,
    TICMODE_STANDARD,
)

_LOGGER = logging.getLogger(__name__)

SOF = b"\x02"
EOF = b"\x03"
EOD = b"\x0d"

SN_TAG_STANDARD = "ADSC"
SN_TAG_HISTORIC = "ADCO"

HISTORIC_OVERPOWER_TAG = "ADPS"

CONNECTION_TIMEOUT = 5


class SerialNumberMismatch(Exception):
    """Serial Number Mismatch."""

    def __init__(self, s_n: str) -> None:
        self.s_n = s_n
        self.msg = f"Unexpected serial number {s_n}"
        super().__init__(self.msg)


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
            (raw_tag, raw_value, raw_checksum) = raw_dataset.strip(
                DATASET_SEPARATOR
            ).split(MODE_HISTORIC_FIELD_SEPARATOR)
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
            match raw_dataset.strip(DATASET_SEPARATOR).split(
                MODE_STANDARD_FIELD_SEPARATOR
            ):
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


class TICProtocol(asyncio.Protocol):
    """Protocol for reading a Linky TIC serial connection."""

    def __init__(self, meter: LinkyMeter, dataset_type: type[Dataset]) -> None:
        """Init the protocol."""
        self._meter = meter
        self._buffer = bytearray()
        self._transport: asyncio.BaseTransport | None = None
        self._lqi = LinkQualityIndicator()
        self._dataset_type = dataset_type

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Called when the connection is made."""
        self._transport = transport
        self._meter.on_connection_made()

    def data_received(self, data: bytes) -> None:
        """Called when data is received from the serial connection."""
        _LOGGER.debug("Received data: %s", data)
        self._buffer += data

        for frame in self._extract_frames():
            self._meter.frame_received(frame)

    @property
    def link_quality_indicator(self) -> int:
        """Return the LQI value, in percent."""
        return self._lqi.get_value()

    def _extract_frames(self) -> Iterator[list[Dataset]]:
        """Extract complete frames from the buffer."""
        while True:
            sof_index = self._buffer.find(SOF)
            if sof_index < 0:
                self._buffer.clear()
                break
            if sof_index > 0:
                del self._buffer[:sof_index]

            # At this point, the buffer starts with SOF.
            eof_index = self._buffer.find(EOF, 1)
            if eof_index < 0:
                break

            yield self._deserialize(self._buffer[: eof_index + 1])
            del self._buffer[: eof_index + 1]

    def _deserialize(self, frame: bytearray) -> list[Dataset]:
        """Deserialize the frame into datasets. Only valid dataset are reported."""

        _LOGGER.debug("Received frame: %s", frame)
        datasets = []
        for raw_dataset in frame.strip(SOF + EOF).split(EOD):
            if not raw_dataset:
                # Pass last empty data
                continue
            try:
                dataset = self._dataset_type.from_raw(bytes(raw_dataset))
            except (MalformatedDatasetException, InvalidChecksumException) as e:
                _LOGGER.debug("Malformed dataset: %s", e)
                self._lqi.update(False)
            else:
                datasets.append(dataset)
                self._lqi.update(True)

        _LOGGER.debug("Returned datasets: %s", datasets)
        return datasets

    def connection_lost(self, exc: Exception | None) -> None:
        """Called when the connection is lost."""
        self._transport = None
        _LOGGER.debug("Connection lost: %s", exc)
        if exc:
            self._meter.on_connection_lost(exc)

    def close(self) -> None:
        """Close the connection."""
        if self._transport:
            self._transport.close()


class LinkyMeter:
    """Linky energy meter representation, for interacting with Home Assistant."""

    _hass: HomeAssistant
    _config: ConfigEntry

    def __init__(self) -> None:
        """Instantiation of a meter, from_config must be used."""
        self._update_callbacks: dict[str, Callable[[bool], None]] = {}
        self._historic_short_frame_active: int = 0
        self._connected: asyncio.Event = asyncio.Event()

        self._serial_number: str | None = None
        self._serial_number_read: asyncio.Future[str] = asyncio.Future()

        self._values: dict[str, Dataset] = {}
        self._protocol: TICProtocol | None
        self._path = ""
        self._mode_std: bool = False

    @classmethod
    async def probe_serial_number(cls, port: str, mode: bool) -> str:
        """Probes a serial connection for a meter, and return its S/N if found.

        Raise LINKY_IO_ERROR or TimeoutError on failure.
        """

        meter = cls()
        meter._path = port
        meter._mode_std = mode

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
        meter._path = config.data[SETUP_SERIAL]
        meter._mode_std = config.data[SETUP_TICMODE] == TICMODE_STANDARD
        await meter._connect_and_wait_for_serial_number()
        return meter

    async def _connect_and_wait_for_serial_number(self) -> str:
        """Coroutine for waiting for the serial number to be read by the reader thread."""

        dataset_type = StandardDataset if self._mode_std else HistoricDataset
        baudrate = (
            MODE_STANDARD_BAUD_RATE if self._mode_std else MODE_HISTORIC_BAUD_RATE
        )

        _LOGGER.debug(
            "Opening serial connection at %s (TIC standard=%s, baudrate=%s)",
            self._path,
            self._mode_std,
            baudrate,
        )

        _, self._protocol = await serialx.create_serial_connection(  # type: ignore[assignment]
            loop=asyncio.get_running_loop(),
            protocol_factory=lambda: TICProtocol(self, dataset_type),
            url=self._path,
            baudrate=baudrate,
            byte_size=BYTESIZE,
            parity=PARITY,
            stopbits=STOPBITS,
        )
        try:
            self._serial_number = await asyncio.wait_for(
                self._serial_number_read, timeout=CONNECTION_TIMEOUT
            )
        except TimeoutError:
            await self.disconnect(Event("Error"))
            raise
        return self._serial_number

    async def disconnect(self, event: Event) -> None:
        """Disconnect the meter."""
        if self._protocol:
            self._protocol.close()

    @callback
    def get_value(self, tag: str) -> tuple[str | None, str | None]:
        """Get the value (and/or timestamp) for a given tag."""
        dataset = self._values.get(tag)
        if dataset is None:
            return None, None
        return dataset.value, dataset.timestamp

    @property
    def name(self) -> str:
        """Return the name of the reader."""
        return self._config.title

    @property
    def is_connected(self) -> bool:
        """Return whether connection is active or not."""
        return self._connected.is_set()

    @property
    def serial_number(self) -> str:
        """Return the serial number of the linky meter."""
        assert self._serial_number  # Should not be called before connection is done
        return self._serial_number

    @property
    def device_identification(self) -> dict[str, str | None]:
        """Return the device identification, derived from its serial number."""
        return self._device_identification

    @property
    def link_quality_indicator(self) -> int:
        """Return the reader LQI, in percent."""
        assert self._protocol
        return self._protocol.link_quality_indicator

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
    def on_connection_made(self) -> None:
        """Callback for the reader when connection has been established (serial number read)."""
        _LOGGER.debug("Connection made to %s", self._path)
        self._connected.set()

    @callback
    def on_connection_lost(self, e: Exception) -> None:
        """Callback for the reader when connection has been lost."""
        if self._connected.is_set():
            _LOGGER.warning("Connection to Linky meter has been lost: %s", e)
            self._hass.config_entries.async_schedule_reload(self._config.entry_id)

    @callback
    def frame_received(self, frame: list[Dataset]) -> None:
        """Callback for the reader when a frame has been read."""

        new_values = {dataset.tag: dataset for dataset in frame}
        try:
            if self._check_serial_number(new_values):
                self._handle_new_values(new_values)
                self._values = new_values
        except SerialNumberMismatch as e:
            _LOGGER.warning(
                "Received a frame with a different meter S/N (%s), dropping frame to preserve saved data",
                e.s_n,
            )

    def _check_serial_number(self, frame: dict[str, Dataset]) -> bool:
        """Check the presence of serial number dataset in frame."""

        s_n_dataset = frame.get(SN_TAG_STANDARD if self._mode_std else SN_TAG_HISTORIC)
        if s_n_dataset is None:
            return False

        if self._serial_number_read.done():
            if s_n_dataset.value == self._serial_number:
                return True
            raise SerialNumberMismatch(s_n_dataset.value)

        return self._set_serial_number(s_n_dataset.value)

    def _set_serial_number(self, s_n: str) -> bool:
        """Set the meter serial number on first read."""
        assert self._serial_number is None

        if len(s_n) != 12:
            _LOGGER.debug(
                "%s: ADS should be 12 char long, actually %d cannot parse: %s",
                self._path,
                len(s_n or ""),
                s_n,
            )
            return False

        # Save serial number
        self._serial_number = s_n
        # let's parse ADS as EURIDIS
        const_code = s_n[0:2]
        type_code = s_n[4:6]

        device_identification = {
            DID_YEAR: s_n[2:4],
            DID_REGNUMBER: s_n[6:],
            DID_CONSTRUCTOR_CODE: const_code,
            DID_CONSTRUCTOR: CONSTRUCTORS_CODES.get(const_code),
            DID_TYPE_CODE: type_code,
            DID_TYPE: DEVICE_TYPES.get(type_code),
        }
        self._device_identification = device_identification
        # Parsing done
        _LOGGER.debug("Parsed ADS: %s", repr(self.device_identification))
        # First read, sets the serial number
        self._serial_number_read.set_result(s_n)
        return True

    def _handle_new_values(self, new_values: dict[str, Dataset]) -> None:
        """Handles data updates for new values."""

        # TODO: this should be the role of a DataUpdateCoordinator
        # Prevent protocol from pushing data in probe mode
        if not self._config:
            return
        # forced ?
        realtime = self._config.options.get(OPTIONS_REALTIME, False)

        # Missing and new data to be updated
        tags_to_update = self._values.keys() | new_values.keys()

        # Check for historic short frames
        if not self._mode_std and new_values.keys() & SHORT_FRAME_DETECTION_TAGS:
            if not self._historic_short_frame_active > 0:
                _LOGGER.info("Short frame burst detected.")

            self._historic_short_frame_active = 2

            # Don't clear long frame data, and update short frame values
            self._values.update(new_values)

            for tag in new_values:
                callback = self._update_callbacks.get(tag)
                if callback:
                    callback(True)
                # Don't propagate other data
                return

        if (
            self._historic_short_frame_active > 0
            and not new_values.keys() & SHORT_FRAME_DETECTION_TAGS
        ):
            self._historic_short_frame_active -= 1

            self._values.update(new_values)

            # Only update values received, don't bother updating missing tags, the logic is complex enough
            # and short frames are uncommon and should not last very long...

            for updated_tag in new_values.keys():
                callback = self._update_callbacks.get(updated_tag)
                if callback:
                    callback(realtime)

        # OVERPOWER TAG should auto-update on callback

        self._values = new_values

        for tag in tags_to_update:
            callback = self._update_callbacks.get(tag)
            if callback:
                callback(realtime)
