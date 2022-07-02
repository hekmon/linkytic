#!/usr/bin/env python3

import serial

# Protocol configuration
#   https://www.enedis.fr/media/2035/download

BYTESIZE = serial.SEVENBITS
PARITY = serial.PARITY_EVEN
STOPBITS = serial.STOPBITS_ONE

MODE_STANDARD_BAUD_RATE = 9600
MODE_STANDARD_FIELD_SEPARATOR = b'\x09'

MODE_HISTORIQUE_BAUD_RATE = 1200
MODE_HISTORIQUE_FIELD_SEPARATOR = b'\x20'

LINE_END = b'\r\n'
FRAME_END = b'\r\x03\x02\n'


class InvalidChecksum(Exception):
    def __init__(self, tag: bytes, timestamp: bytes, value: bytes, s1: bytes, s1_truncated: bytes, computed: bytes, expected: bytes):
        self.tag = tag.decode("ascii")
        self.timestamp = timestamp.decode("ascii")
        self.value = value.decode("ascii")
        self.s1 = s1
        self.s1_truncated = s1_truncated
        self.computed = computed
        self.expected = expected
        super().__init__(self.msg())

    def msg(self):
        return "{} -> {} ({}) | s1 {} {} | truncated {} {} {} | computed {} {} {} | expected {} {} {}".format(
            self.tag, self.value, self.timestamp, self.s1, bin(self.s1),
            self.s1_truncated, bin(self.s1_truncated), chr(self.s1_truncated),
            self.computed, bin(self.computed), chr(self.computed), int.from_bytes(
                self.expected, byteorder='big'),
            bin(int.from_bytes(self.expected, byteorder='big')), chr(ord(self.expected)))


class TICReader:
    """
    SerialReader act as a python controller to read from the Lixee TIC DIN module for the French Linky electric meter
    """

    def __init__(self, device='/dev/ttyUSB0', mode_standard=False):
        baud_rate = MODE_STANDARD_BAUD_RATE if mode_standard else MODE_HISTORIQUE_BAUD_RATE
        self._con = serial.Serial(
            device, baudrate=baud_rate, bytesize=BYTESIZE, parity=PARITY, stopbits=STOPBITS, timeout=1)
        self.std_mode = mode_standard

    def get_full_frame_data(self):
        # Open serial if not already open
        if not self._con.is_open:
            self._con.open()
        # Wait for the current frame to end
        line = self._con.readline()
        while FRAME_END not in line:
            print("waiting for new frame")
            line = self._con.readline()
        # Next line will be the first of the new set
        line = b''
        infos = {}
        while FRAME_END not in line:
            print("new line")
            line = self._con.readline()
            try:
                tag, value = self.parse_line(line)
                infos[tag] = value
            except InvalidChecksum as e:
                print("invalid checksum detected for {}: {}".format(e.tag, e.msg()))
        # Now that we have all our values, let's convert their values
        return infos

    def parse_line(self, line: bytes):
        # cleanup the line
        line = line.rstrip(LINE_END).rstrip(FRAME_END)
        # extract the fields by parsing the line given the mode
        timestamp = None
        if self.std_mode:
            fields = line.split(MODE_STANDARD_FIELD_SEPARATOR)
            if len(fields) == 4:
                tag = fields[0]
                timestamp = fields[1]
                field_value = fields[2]
                checksum = fields[3]
            elif len(fields) == 3:
                tag = fields[0]
                field_value = fields[1]
                checksum = fields[2]
            else:
                raise Exception(
                    "parse line standard mode failed: invalid number of fields after split")
        else:
            fields = line.split(MODE_HISTORIQUE_FIELD_SEPARATOR)
            if len(fields) == 3:
                tag = fields[0]
                field_value = fields[1]
                checksum = fields[2]
            elif len(fields) == 2:
                # checksum has the same value as field separator
                tag = fields[0]
                field_value = fields[1]
                checksum = MODE_HISTORIQUE_FIELD_SEPARATOR
            else:
                raise Exception(
                    "parse line historique mode failed: invalid number of fields after split")
        # validate the checksum
        self.validate_checksum(tag, timestamp, field_value, checksum)
        # prepare and format the returned values
        ret_value = {"value": field_value.decode("ascii")}
        if timestamp is not None:
            ret_value["timestamp"] = timestamp.decode("ascii")
        return tag.decode("ascii"), ret_value

    def validate_checksum(self, tag: bytes, timestamp: bytes, value: bytes, checksum: bytes):
        # rebuild the frame
        if self.std_mode:
            sep = MODE_STANDARD_FIELD_SEPARATOR
            if timestamp is None:
                frame = tag + sep + value + sep
            else:
                frame = tag + sep + timestamp + sep + value + sep
        else:
            frame = tag + MODE_HISTORIQUE_FIELD_SEPARATOR + value
        # compute the sum of the frame
        s1 = 0
        for b in frame:
            s1 += b
        # compute checksum for s1
        truncated = s1 & 0x3F
        computed_checksum = truncated + 0x20
        # validate
        if computed_checksum != ord(checksum):
            raise InvalidChecksum(tag, timestamp, value, s1, truncated,
                                  computed_checksum, checksum)


if __name__ == "__main__":
    linky = TICReader()
    print(linky.get_full_frame_data())
