"""serial reader tests"""

import asyncio
import contextlib
import logging
import os
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from typing import IO, Any
from unittest.mock import MagicMock, patch

import pytest
import serialx
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.linkytic import const
from custom_components.linkytic.serial_reader import (
    Dataset,
    HistoricDataset,
    InvalidChecksumException,
    LinkQualityIndicator,
    LinkyMeter,
    MalformatedDatasetException,
    SerialNumberMismatch,
    StandardDataset,
    TICProtocol,
)


# Nicely borrowed from serialx
@contextlib.contextmanager
def create_socat_pair() -> Iterator[
    tuple[str, str, Callable[[], None] | None, Callable[[], None] | None]
]:
    """Create a bridged pair of virtual PTYs using two socat processes.

    Each PTY is managed by its own socat process, linked via a UNIX socket.
    Killing one socat process closes its PTY and propagates EOF to the other.
    """

    def _wait_for_ready(
        process: subprocess.Popen[Any],
        stream: IO[bytes] | None,
        marker: str,
        name: str,
    ) -> None:
        """Wait for a process to print a ready marker to stdout or stderr."""
        assert stream is not None

        marker_bytes = marker.encode()
        output = bytearray()

        while True:
            line = stream.readline()

            if not line:
                raise RuntimeError(
                    f"{name} exited before ready (code={process.returncode})"
                    f"\n{stream}: {output.decode(errors='replace')}"
                )

            output.extend(line)

            if marker_bytes in line:
                return

    with tempfile.TemporaryDirectory() as tmpdir:
        left_tty = os.path.join(tmpdir, "ttyLeft")
        right_tty = os.path.join(tmpdir, "ttyRight")
        bridge = os.path.join(tmpdir, "bridge.sock")

        # Start the right side first (UNIX-LISTEN), then the left (UNIX-CONNECT)
        right_proc = subprocess.Popen(
            [
                "socat",
                "-d",
                "-d",
                f"PTY,link={right_tty},raw,echo=0",
                f"UNIX-LISTEN:{bridge},rcvbuf=1024,sndbuf=1024",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        _wait_for_ready(
            right_proc,
            marker="listening on",
            stream=right_proc.stderr,
            name="socat(right)",
        )

        left_proc = subprocess.Popen(
            [
                "socat",
                "-d",
                "-d",
                f"PTY,link={left_tty},raw,echo=0",
                f"UNIX-CONNECT:{bridge},rcvbuf=1024,sndbuf=1024",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        _wait_for_ready(
            left_proc,
            marker="starting data transfer loop",
            stream=left_proc.stderr,
            name="socat(left)",
        )

        def _kill(proc: subprocess.Popen[Any]) -> None:
            proc.kill()
            proc.wait()

        try:
            # Killing socat tears down the PTY; the client read hangs up with
            # EIO, an inherently abrupt disconnect. There is no clean-FIN form.
            yield (
                left_tty,
                right_tty,
                None,
                lambda: _kill(left_proc),
            )
        finally:
            for proc in (left_proc, right_proc):
                if proc.returncode is None:
                    proc.terminate()
                    proc.wait()

                # The unplug callables hold references to the Popen objects
                if proc.stderr is not None:
                    proc.stderr.close()


@pytest.mark.parametrize(
    ("data", "tag", "value", "timestamp"),
    [
        (b"EAST\t003519702\t*", "EAST", "003519702", None),
        (b"ADSC\t001122334455\t+", "ADSC", "001122334455", None),
        (b"SMAXSN\tH081225223518\t01234\t>", "SMAXSN", "01234", "H081225223518"),
    ],
)
def test_standard_dataset_decode(data, tag, value, timestamp):
    """Test the decoding of a standard dataset."""

    dataset = StandardDataset.from_raw(data)

    assert dataset.tag == tag
    assert dataset.value == value
    assert dataset.timestamp == timestamp


@pytest.mark.parametrize(
    "data",
    [
        (b"EAST\t003519702\t0"),
        (b"ADSC\t001122334455\t0"),
    ],
)
def test_standard_dataset_invalid_checksum(data):
    """Test that an invalid checksum raises an exception."""

    with pytest.raises(InvalidChecksumException):
        StandardDataset.from_raw(data)


@pytest.mark.parametrize(
    "data",
    [
        (b"EAST\t003519702a0"),
        (b"ADSC\t001122334455\t\0"),
        (b"ADSC\t\t001122334455\tx0"),
    ],
)
def test_standard_dataset_malformed(data):
    """Test that a malformed dataset raises an exception."""

    with pytest.raises(MalformatedDatasetException):
        StandardDataset.from_raw(data)


@pytest.mark.parametrize(
    "data,tag,value",
    [
        (b"ADCO 012345678910 E", "ADCO", "012345678910"),
        (b"BASE 123456789 8", "BASE", "123456789"),
    ],
)
def test_historic_dataset_decode(data, tag, value):
    """Test the decoding of a historic dataset."""

    dataset = HistoricDataset.from_raw(data)

    assert dataset.tag == tag
    assert dataset.value == value
    assert dataset.timestamp is None


@pytest.mark.parametrize(
    "data",
    [
        (b"ADCO 012345678910 0"),
        (b"BASE 123456789 0"),
    ],
)
def test_historic_dataset_invalid_checksum(data):
    """Test that an invalid checksum raises an exception."""

    with pytest.raises(InvalidChecksumException):
        HistoricDataset.from_raw(data)


@pytest.mark.parametrize(
    "data",
    [
        (b"ADCOx012345678910 0"),
        (b"BASE 123456789 0a"),
        (b"BASE 123456789 \x00"),
    ],
)
def test_historic_dataset_malformed(data):
    """Test that a malformed dataset raises an exception."""

    with pytest.raises(MalformatedDatasetException):
        HistoricDataset.from_raw(data)


def test_link_quality_indicator():
    """Test the link quality indicator filter."""

    lqi = LinkQualityIndicator()

    for _ in range(100):
        lqi.update(False)

    assert lqi.get_value() == 0


async def test_standard_tic_protocol(hass: HomeAssistant, config_entry: ConfigEntry):
    """Test standard TIC protocol."""
    meter = LinkyMeter()
    meter._mode_std = True
    meter._config = config_entry
    meter._hass = MagicMock(hass)

    with create_socat_pair() as (left_tty, right_tty, _, _):
        with open(left_tty, "wb") as writer:
            transport, protocol = await serialx.create_serial_connection(
                loop=asyncio.get_running_loop(),
                protocol_factory=lambda: TICProtocol(meter, StandardDataset),
                url=right_tty,
                baudrate=9600,
            )
            writer.write(
                b"\x02\x0aADSC\t001122334455\t+\x0d\x0aEAST\t003519702\t*\x0d\x03"
            )
            writer.flush()
            await meter._serial_number_read

    assert meter._values == {
        "ADSC": Dataset("ADSC", "001122334455", None),
        "EAST": Dataset("EAST", "003519702", None),
    }


async def test_historic_tic_protocol(hass: HomeAssistant, config_entry: ConfigEntry):
    """Test standard TIC protocol."""
    meter = LinkyMeter()
    meter._mode_std = False
    meter._config = config_entry
    meter._hass = MagicMock(hass)

    with create_socat_pair() as (left_tty, right_tty, _, _):
        with open(left_tty, "wb") as writer:
            transport, protocol = await serialx.create_serial_connection(
                loop=asyncio.get_running_loop(),
                protocol_factory=lambda: TICProtocol(meter, HistoricDataset),
                url=right_tty,
                baudrate=9600,
            )
            writer.write(b"\x02\x0aADCO 012345678910 E\x0d\x0aBASE 123456789 8\x0d\x03")
            writer.flush()
            await meter._serial_number_read

    assert meter._values == {
        "ADCO": Dataset("ADCO", "012345678910", None),
        "BASE": Dataset("BASE", "123456789", None),
    }


async def test_meter_from_config_no_port(
    hass: HomeAssistant, config_entry: ConfigEntry
):
    """Test file not found error for device config."""

    with pytest.raises(FileNotFoundError):
        await LinkyMeter.connect_from_config(hass, config_entry)


async def test_meter_from_config_timeout(hass: HomeAssistant):
    """Test timeout error on connection."""

    with (
        create_socat_pair() as (tty, *_),
        patch("custom_components.linkytic.serial_reader.CONNECTION_TIMEOUT", 0.01),
    ):
        config_entry = MockConfigEntry(
            data={
                const.SETUP_SERIAL: tty,
                const.SETUP_TICMODE: const.TICMODE_STANDARD,
            }
        )
        with pytest.raises(TimeoutError):
            await LinkyMeter.connect_from_config(hass, config_entry)


@pytest.mark.parametrize(
    ("mode", "frame"),
    (
        (
            const.TICMODE_STANDARD,
            b"\x02\x0aADSC\t001122334455\t+\x0d\x0aEAST\t003519702\t*\x0d\x03",
        ),
        (
            const.TICMODE_HISTORIC,
            b"\x02\x0aADCO 001122334455 5\x0d\x0aBASE 123456789 8\x0d\x03",
        ),
    ),
)
async def test_meter_from_config(hass: HomeAssistant, mode, frame):
    """Test S/N mismatch error on connection."""

    hass = MagicMock(hass)

    with (
        create_socat_pair() as (input_tty, output_tty, _, kill_input),
        patch("custom_components.linkytic.serial_reader.CONNECTION_TIMEOUT", 0.1),
    ):
        config_entry = MockConfigEntry(
            data={
                const.SETUP_SERIAL: output_tty,
                const.SETUP_TICMODE: mode,
            }
        )
        async with serialx.async_serial_for_url(input_tty, baudrate=9600) as writer:
            async with asyncio.TaskGroup() as tg:

                async def emulate_tic() -> None:
                    while True:
                        if not writer.is_open:
                            return
                        await writer.write(frame)
                        await asyncio.sleep(0.1)

                tg.create_task(emulate_tic())

                meter = await LinkyMeter.connect_from_config(hass, config_entry)
                assert meter.serial_number == "001122334455"
                kill_input()
                await meter.disconnect(None)


@pytest.mark.parametrize("realtime", (True, False))
def test_update_callback(realtime):
    """Test registering callback, and update."""

    data = []

    def callback(realtime: bool):
        data.append(realtime)

    meter = LinkyMeter()
    meter._config = MockConfigEntry(options={const.OPTIONS_REALTIME: realtime})
    meter.register_update_callback("DEMO", callback)

    meter._handle_new_values({"DEMO": Dataset("DEMO", "test", None)})

    assert data[0] is realtime


def test_historic_short_frame_callback():
    """Test historic short frame handler."""

    frame = {
        "ADS": Dataset("", "", None),
        "ADIR1": Dataset("", "", None),
        "ADIR2": Dataset("", "", None),
        "ADIR3": Dataset("", "", None),
        "IINST1": Dataset("", "", None),
        "IINST2": Dataset("", "", None),
        "IINST3": Dataset("", "", None),
    }

    data = []

    def callback(realtime: bool):
        data.append(realtime)

    meter = LinkyMeter()
    meter._config = MockConfigEntry(options={const.OPTIONS_REALTIME: False})

    for tag in frame:
        meter.register_update_callback(tag, callback)

    meter._handle_new_values(frame)

    assert data == [True] * frame.__len__()

    data.clear()
    # Test new values not in short frame

    meter._handle_new_values({"ADS": Dataset("", "", "")})

    assert data == [False]


@pytest.mark.parametrize(
    ("s_n", "frame", "retval"),
    (
        (None, {}, False),
        ("1", {"ADCO": Dataset("ADCO", "1", None)}, True),
    )
)
def test_serial_number_check(s_n, frame, retval):
    """Test checking of serial number."""

    meter = LinkyMeter()
    meter._serial_number = s_n
    if s_n:
        meter._serial_number_read.set_result(s_n)
    assert meter._check_serial_number(frame) == retval    


@pytest.mark.parametrize(
    ("mode", "frame"),
    (
        (const.TICMODE_HISTORIC, [Dataset("ADCO", "2", None)]),
        (const.TICMODE_STANDARD, [Dataset("ADSC", "2", None)]),
    ),
)
def test_serial_number_mistmatch(mode, frame, caplog):
    """Test detection of wrong serial number."""

    meter = LinkyMeter()
    meter._mode_std = mode == const.TICMODE_STANDARD
    meter._serial_number_read.set_result("1")
    meter._serial_number = "1"

    with caplog.at_level(logging.WARNING):
        meter.frame_received(frame)
    assert "different meter S/N" in caplog.text


def test_tag_update():
    """Test return value for a tag."""

    meter = LinkyMeter()
    meter._values = {"TAG1": Dataset("TAG1", "Value", None), "TAG2": Dataset("TAG2", "Value", "H081225223518")}

    value, timestamp = meter.get_value("TAG1")
    assert value == "Value"
    assert timestamp is None

    value, timestamp = meter.get_value("TAG2")
    assert value == "Value" 
    assert timestamp == "H081225223518"

    
def test_missing_tag_update():
    """Test return value for a missing tag."""
    
    meter = LinkyMeter()

    value, timestamp = meter.get_value("TAG")
    assert value is None
    assert timestamp is None


async def test_meter_lqi():
    """Test meter LQI retrieval."""

    meter = LinkyMeter()

    with pytest.raises(AssertionError):
        meter.link_quality_indicator


@pytest.fixture(name="config_entry")
def config_entry_fixture() -> MockConfigEntry:
    """Fixture of a config entry"""
    return MockConfigEntry(
        version=2,
        minor_version=1,
        domain=const.DOMAIN,
        data={
            const.SETUP_SERIAL: "/dev/ttyUSBX",
            const.SETUP_TICMODE: const.TICMODE_STANDARD,
            const.SETUP_PRODUCER: False,
            const.SETUP_THREEPHASE: False,
        },
        options={const.OPTIONS_REALTIME: False},
    )
