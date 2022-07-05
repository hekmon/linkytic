"""Constants for the Linky (LiXee-TIC-DIN) integration."""

import serial

DOMAIN = "lixeeticdin"

SERIAL_READER = "sr"

# Protocol configuration
#   https://www.enedis.fr/media/2035/download

BYTESIZE = serial.SEVENBITS
PARITY = serial.PARITY_EVEN
STOPBITS = serial.STOPBITS_ONE

MODE_STANDARD_BAUD_RATE = 9600
MODE_STANDARD_FIELD_SEPARATOR = b'\x09'

MODE_HISTORIC_BAUD_RATE = 1200
MODE_HISTORIC_FIELD_SEPARATOR = b'\x20'

LINE_END = b'\r\n'
FRAME_END = b'\r\x03\x02\n'


# Configuration

CONF_SERIAL_PORT = "serial_port"
CONF_STANDARD_MODE = "standard_mode"

DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"
DEFAULT_STANDARD_MODE = False
