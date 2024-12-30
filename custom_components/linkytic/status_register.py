"""Definition of status register fields and handlers."""

from enum import Enum
from typing import NamedTuple


class StatusRegisterField(NamedTuple):
    """Represent a field in the status register.
    lsb is the position of the least significant bit of the field in the status register.
    len if the length in bit of the field (default 1 bit).
    options is a dictionary mapping field int value to string. If no options, the value is treated as a boolean.
    """

    lsb: int
    len: int = 1
    options: dict[int, str] | None = None

    def get_status(self, register: str) -> str | bool:
        try:
            int_register = int(register, base=16)
        except TypeError:
            return False
        val = (int_register >> self.lsb) & ((1 << self.len) - 1)

        if self.options is None:
            return bool(val)

        return self.options[val]  # Let IndexError propagate if val is unknown.


trip_unit = {
    0: "close",
    1: "overpower",
    2: "overvoltage",
    3: "shedding",
    4: "cpl",
    5: "overheat_over_imax",
    6: "overheat_below_imax",
}

current_index = {i: f"index_{i+1}" for i in range(0, 10)}

euridis_status = {
    0: "deactivated",
    1: "activated_not_securized",
    2: "unknown",
    3: "activated_securized",
}

cpl_status = {
    0: "new_unlock",
    1: "new_lock",
    2: "registered",
    3: "unknown",
}

tempo_color = {
    0: "no_data",
    1: "blue",
    2: "white",
    3: "red",
}

mobile_peak = {
    0: "no_data",
    1: "pm1",
    2: "pm2",
    3: "pm3",
}


class StatusRegister(Enum):
    """Field provided by status register.
    The value corresponds to the (position, bits).
    """

    DRY_CONTACT = StatusRegisterField(0)
    TRIP_UNIT = StatusRegisterField(1, 3, trip_unit)
    TERMINAL_COVER_OFF = StatusRegisterField(4)
    # bit 5 is reserved
    OVERVOLTAGE = StatusRegisterField(6)
    POWER_OVER_REF = StatusRegisterField(7)
    IS_PRODUCER = StatusRegisterField(8)
    IS_INJECTING = StatusRegisterField(9)
    PROVIDER_INDEX = StatusRegisterField(10, 4, current_index)
    DISTRIBUTOR_INDEX = StatusRegisterField(14, 2, current_index)
    RTC_DEGRADED = StatusRegisterField(16)
    TIC_STD = StatusRegisterField(17)
    # bit 18 is reserved
    EURIDIS = StatusRegisterField(19, 2, euridis_status)
    STATUS_CPL = StatusRegisterField(21, 2, cpl_status)
    CPL_SYNC = StatusRegisterField(23)
    COLOR_TODAY = StatusRegisterField(24, 2, tempo_color)
    COLOR_NEXT_DAY = StatusRegisterField(26, 2, tempo_color)
    MOBILE_PEAK_NOTICE = StatusRegisterField(28, 2, mobile_peak)
    MOBILE_PEAK = StatusRegisterField(30, 2, mobile_peak)
