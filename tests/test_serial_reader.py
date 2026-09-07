"""serial reader tests"""

import asyncio
import contextlib
import os
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from typing import IO, Any

import pytest
import serialx
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.linkytic.const import DOMAIN
from custom_components.linkytic.serial_reader import (
    Dataset,
    HistoricDataset,
    InvalidChecksumException,
    LinkQualityIndicator,
    LinkyMeter,
    MalformatedDatasetException,
    StandardDataset,
    TICProtocol,
)


def patch_config_entry() -> ConfigEntry:
    """Path a HA config entry."""
    return ConfigEntry(
        discovery_keys=None, #type: ignore[assignment]
        data={},
        domain=DOMAIN,
        version=1,
        minor_version=1,
        options={},
        source="",
        subentries_data=[],
        title="MockEntry",
        unique_id="1"
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


@pytest.mark.parametrize("data,tag,value", 
    [
        (b"EAST\t003519702\t*", "EAST", "003519702"),
        (b"ADSC\t001122334455\t+", "ADSC", "001122334455"),
    ]
)
def test_standard_dataset_decode(data, tag, value):
    """Test the decoding of a standard dataset."""

    dataset = StandardDataset.from_raw(data)

    assert dataset.tag == tag
    assert dataset.value == value


@pytest.mark.parametrize("data",
    [
        (b"EAST\t003519702\t0"),
        (b"ADSC\t001122334455\t0"),
    ]
)
def test_standard_dataset_invalid_checksum(data):
    """Test that an invalid checksum raises an exception."""

    with pytest.raises(InvalidChecksumException):
        StandardDataset.from_raw(data)

@pytest.mark.parametrize("data",
    [
        (b"EAST\t003519702\t0"),
        (b"ADSC\t001122334455\t0"),
    ]
)
def test_standard_dataset_malformed(data):
    """Test that a malformed dataset raises an exception."""

    data = b"EAST003519702*"
    with pytest.raises(MalformatedDatasetException):
        StandardDataset.from_raw(data)

@pytest.mark.parametrize("data,tag,value",
    [
        (b"ADCO 012345678910 E", "ADCO", "012345678910"),
        (b"BASE 123456789 8", "BASE", "123456789"),
    ]
)
def test_historic_dataset_decode(data, tag, value):
    """Test the decoding of a historic dataset."""

    dataset = HistoricDataset.from_raw(data)

    assert dataset.tag == tag
    assert dataset.value == value
    assert dataset.timestamp is None

@pytest.mark.parametrize("data",
    [
        (b"ADCO 012345678910 0"),
        (b"BASE 123456789 0"),
    ]
)
def test_historic_dataset_invalid_checksum(data):
    """Test that an invalid checksum raises an exception."""

    with pytest.raises(InvalidChecksumException):
        HistoricDataset.from_raw(data)

@pytest.mark.parametrize("data",
    [
        (b"ADCOx012345678910 0"),
        (b"BASE 123456789 0a"),
    ]
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


async def test_standard_tic_protocol():
    """Test standard TIC protocol."""
    meter = LinkyMeter()
    meter._mode_std = True
    meter._config = patch_config_entry()

    with create_socat_pair() as (left_tty, right_tty, _, _):
        with open(left_tty, "wb") as writer:
            
            transport, protocol = await serialx.create_serial_connection(
                loop=asyncio.get_running_loop(),
                protocol_factory=lambda: TICProtocol(meter, StandardDataset),
                url=right_tty,
                baudrate=9600
            )
            writer.write(b"\x02\x0AADSC\t001122334455\t+\x0D\x0AEAST\t003519702\t*\x0D\x03")
            writer.flush()
            await meter._serial_number_read

    assert meter._values == {"ADSC": Dataset("ADSC", "001122334455", None), "EAST": Dataset("EAST", "003519702", None)}


async def test_historic_tic_protocol():
    """Test standard TIC protocol."""
    meter = LinkyMeter()
    meter._mode_std = False
    meter._config = patch_config_entry()

    with create_socat_pair() as (left_tty, right_tty, _, _):
        with open(left_tty, "wb") as writer:
            
            transport, protocol = await serialx.create_serial_connection(
                loop=asyncio.get_running_loop(),
                protocol_factory=lambda: TICProtocol(meter, HistoricDataset),
                url=right_tty,
                baudrate=9600
            )
            writer.write(b"\x02\x0AADCO 012345678910 E\x0D\x0ABASE 123456789 8\x0D\x03")
            writer.flush()
            await meter._serial_number_read

    assert meter._values == {"ADCO": Dataset("ADCO", "012345678910", None), "BASE": Dataset("BASE", "123456789", None)}