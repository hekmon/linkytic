"""TIC Emulator using socat utility (posix)."""

import argparse
import asyncio
import contextlib
import logging
import pathlib
import subprocess
import tempfile
import time
from collections.abc import AsyncGenerator, Callable, Generator, Iterable

import serialx

SOCAT_LISTENING = b"starting data transfer loop"

SOF = b"\x02"
EOF = b"\x03"
SOD = b"\x0A"
EOD = b"\x0D"

DATASET_HISTORIC_COMMON = (
    ("ADCO", ""),
)

DATASETS_HISTORIC_MONO_BASE = (
    ("OPTARIF", "BASE"),
    ("ISOUSC", "90"),
    ("BASE", "%09d"),
    ("IINST", "%03d"),
    ("IMAX", "90"),
    ("PAPP", "%03d"),
    ("PHHPHC", "A"),
    ("MOTDETAT", "000000")
)

DATASETS_HISTORIC_THREE_BASE = (
    ("OPTARIF", "BASE"), # "Selon contrat"?
    ("ISOUSC", "60"),
    ("BASE", "%09d"),
    ("HCHC", "%09d"),
    ("HCHP", "%09d"),
    ("EJPHN", "%09d"),
    ("EJPHPM", "%09d"),
    ("BBRHCJB", "%09d"),
    ("BBRHPJB", "%09d"),
    ("BBRHCJW", "%09d"),
    ("BBRHPJW", "%09d"),
    ("BBRHCJR", "%09d"),
    ("BBRHPJR", "%09d"),
    ("PEJP", "30"),
    ("PTEC", "TH.."),
    ("DEMAIN", "ROUG"),
    ("IINST1", "%03d"),
    ("IINST2", "%03d"),
    ("IINST3", "%03d"),
    ("IMAX1", "%03d"),
    ("IMAX2", "%03d"),
    ("IMAX3", "%03d"),
    ("PMAX", "%05d"),
    ("PAPP", "%05d"),
    ("HHPHC", "A"),
    ("MOTDETAT", "000000"),
    ("PPOT", "00")
)

DATASET_HISTORIC_SHORT_FRAME = (
    ("ADIR1", "%03d"),
    ("ADIR2", "%03d"),
    ("ADIR3", "%03d"),
    ("IINST1", "%03d"),
    ("IINST2", "%03d"),
    ("IINST3", "%03d"),
)

# @ notes a timestamp
DATASET_STANDARD_COMMON = (
    ("ADSC", ""),
    ("VTIC", "02"),
    ("DATE", "@"),
    ("NGTF", "BASE"),
    ("LTARF", "BASE"),
    ("EAST", "%09d"),
    *(("EASF%02d" % i, "%09d") for i in range(1, 11)),
    *(("EASD%02d" % i, "%09d") for i in range(1, 5)),
    ("IRMS1", "%03d"),
    ("URMS1", "%03d"),
    ("PREF", "%02d"),
    ("PCOUP", "%02d"),
    ("SINSTS", "%02d"),
    ("SINSTS", "%02d"),
    ("SMAXSN", "@%05d"),
    ("SMAXSN-1", "@%05d"),
    ("CCASN", "@%05d"),
    ("CCASN-1", "@%05d"),
    ("UMOY1", "@%03d"),
    ("STGE", "%08d"),
    ("DPM1", "@%02d"),
    ("FPM1", "@%02d"),
    ("DPM2", "@%02d"),
    ("FPM2", "@%02d"),
    ("DPM3", "@%02d"),
    ("FPM3", "@%02d"),
    ("MSG1", "% 32s"),
    ("MSG2", "% 16s"),
    ("PRM", "% 14s"),
    ("RELAIS", "%03d"),
    ("NTARF", "%02d"),
    ("NJOURF", "%02d"),
    ("NJOURF+1", "%02d"),
    ("PJOUR+1", "% 98s"),
    ("PPOINTE", "% 98s"),
)

DATASET_STANDARD_THREEPHASE = (
    ("IRMS2", "%03d"),
    ("IRMS3", "%03d"),
    ("URMS2", "%03d"),
    ("URMS3", "%03d"),
    *(("SINSTS%d" % i, "%05d") for i in range(1, 4)),
    *(("SMAXSN%d" % i, "%05d") for i in range(1, 4)),
    *(("SMAXSN%d-1" % i, "%05d") for i in range(1, 4)),
    ("UMOY2", "%03d"),
    ("UMOY3", "%03d"),
)

DATASET_STANDARD_PRODUCER = (
    ("EAIT", "%09d"),
    *(("ERQ%d" % i, "%09d") for i in range(1, 5)),
    ("SINSTI", "%05d"),
    ("SMAXIN", "%05d"),
    ("SMAXIN-1", "%05d"),
    ("CCAIN", "%05d"),
    ("CCAIN-1", "%05d"),
)


@contextlib.asynccontextmanager
async def create_socat(output:pathlib.Path, input: pathlib.Path) -> AsyncGenerator[Callable]:
    """Open a socat process. Return a callable that kills the process."""
    
    socat_process = subprocess.Popen(
        [
            "socat",
            "-dd",
            f"PTY,link={input},raw,echo=0",
            f"PTY,link={output},raw,echo=0"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE
    )
    assert socat_process.stderr
    socat_output = bytearray()

    async with asyncio.timeout(5):
        while True:
            line = socat_process.stderr.readline()
            if not line:
                raise RuntimeError(
                    f"No stream from socat. code={socat_process.returncode}"
                    f"\nstream: {socat_process.stderr}: {socat_output}"
                    )
            socat_output.extend(line)

            if SOCAT_LISTENING in line:
                break

    def kill(proc: subprocess.Popen) -> None:
        proc.kill()
        proc.wait()
    
    try:
        yield lambda: kill(socat_process)
    finally:
        if socat_process.returncode is None:
            socat_process.terminate()
            socat_process.wait()


async def write_loop(input: pathlib.Path, stream):
    """Write in loop from the given stream."""

    async with serialx.async_serial_for_url(str(input), baudrate=9600) as writer:
        while True:
            await writer.write(next(stream))
            await asyncio.sleep(0.1)


def get_stream(file) -> Generator:
    """Get data from a file indefinitely."""

    while True:
        with open(file, "rb") as stream:
            while data := stream.readline():
                yield data


def encode_historic_dataset(tag:str, value:str) -> bytes:
    """Encode a historic dataset."""
    tag_b = tag.encode("ascii")
    value_b = value.encode("ascii")
    checksum = (((sum(tag_b + value_b) + 0x20) & 0x3F) + 0x20).to_bytes()
    return SOD + b" ".join((tag_b, value_b, checksum)) + EOD


def encode_standard_dataset(tag:str, value:str) -> bytes:
    """Encode a historic dataset."""
    tag_b = tag.encode("ascii")
    value_b = value.lstrip("@").encode("ascii")
    timestamp_b = b"H250911232818"
    data = tag_b + b"\t" + ((timestamp_b + b"\t") if value.startswith("@") else b"") + value_b + b"\t"
    checksum = ((sum(data) & 0x3F) + 0x20).to_bytes()
    return SOD + data + checksum + EOD


def generate_stream(serial_number: str, mode_std: bool, pool: Generator[Iterable]) -> Generator:
    """Generate random data in historic mode."""
    encode = encode_standard_dataset if mode_std else encode_historic_dataset
    while True:
        yield SOF
        for (tag, value) in next(pool):
            if tag in ("ADCO", "ADSC"):
                value = serial_number

            if "%" in value:
                ndigit = value.rstrip("ds").lstrip("@%0 ")
                value = value % (int(time.time()) % 10**int(ndigit))

            yield encode(tag, value)
        yield EOF


async def main():
    """Entry point, handles argument and controls data flow."""
    
    argparser = argparse.ArgumentParser()
    argparser.add_argument("mode", choices=("hist", "std"))
    argparser.add_argument("-t", "--tty", type=pathlib.Path, help="Path of the tty to open", default=None)
    argparser.add_argument("-c", "--capture", type=pathlib.Path, help="Capture file in hex format")
    argparser.add_argument("-s", "--serial-number", type=str, help="Custom serial number")
    argparser.add_argument("-d", "--debug", action="store_true")
    argparser.add_argument("--threephase", action="store_true")
    argparser.add_argument("--producer", action="store_true")
    argparser.add_argument("--short-frame", action="store_true")
    args = argparser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    if args.capture:
        if (args.threephase or args.producer):
            logging.warning("Can't control threephase/producer on given capture")
    else:
        if args.mode == "hist" and args.producer:
            argparser.exit(-1, "Producer mode is not available in historic mode")
        if args.mode == "std" and args.short_frame:
            argparser.exit(-1, "Short frames are not available in standard mode")

    if args.short_frame:
        args.threephase = True

    serial_number = args.serial_number or "001122334455"

    with tempfile.TemporaryDirectory() as tempdir:
        input = pathlib.Path(tempdir, "input")
        tty = args.tty or pathlib.Path(f"./tty{args.mode.upper()}")

        async with create_socat(tty, input) as kill:

            if args.capture:
                stream = get_stream(args.capture)
            else:
                if args.mode == "std":
                    pool = [*DATASET_STANDARD_COMMON]
                    if args.producer:
                        pool.extend(DATASET_STANDARD_PRODUCER)
                    if args.threephase:
                        pool.extend(DATASET_STANDARD_THREEPHASE)
                elif args.mode == "hist":
                    pool = [*DATASET_HISTORIC_COMMON, *(DATASETS_HISTORIC_THREE_BASE if args.threephase else DATASETS_HISTORIC_MONO_BASE)]

                def pool_generator():
                    while True:
                        yield pool
                        # Send 20 burst frame every minute
                        if args.short_frame and time.monotonic() % 60 < 1:
                            logging.info("Burst frame")
                            for _ in range(20):
                                yield (*DATASET_HISTORIC_COMMON, *DATASET_HISTORIC_SHORT_FRAME)

                stream = generate_stream(serial_number, args.mode == "std", pool_generator())

            print(f"Emulating TIC in {args.mode} mode")
            print(f"Serial port available at {tty}")

            try:
                await write_loop(input, stream)
            except asyncio.CancelledError:
                print("\nExciting.")
                kill()

if __name__ == "__main__":
    asyncio.run(main())