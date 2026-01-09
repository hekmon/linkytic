"""Test the status register decoding."""

from custom_components.linkytic.status_register import (
    StatusRegister,
    cpl_status,
    current_index,
    euridis_status,
    mobile_peak,
    tempo_color,
    trip_unit,
)


def test_parse():
    STGE = "013AC501"

    EXPECTED = {
        StatusRegister.DRY_CONTACT: 1,
        StatusRegister.TRIP_UNIT: trip_unit[0],
        StatusRegister.TERMINAL_COVER: 0,
        StatusRegister.OVERVOLTAGE: 0,
        StatusRegister.POWER_OVER_REF: 0,
        StatusRegister.PRODUCER: 1,
        StatusRegister.INJECTING: 0,
        StatusRegister.PROVIDER_INDEX: current_index[1],
        StatusRegister.DISTRIBUTOR_INDEX: current_index[3],
        StatusRegister.RTC_DEGRADED: 0,
        StatusRegister.TIC_STD: 1,
        StatusRegister.EURIDIS: euridis_status[3],
        StatusRegister.CPL_STATUS: cpl_status[1],
        StatusRegister.CPL_SYNC: 0,
        StatusRegister.COLOR_TODAY: tempo_color[1],
        StatusRegister.COLOR_NEXT_DAY: tempo_color[0],
        StatusRegister.MOBILE_PEAK_NOTICE: mobile_peak[0],
        StatusRegister.MOBILE_PEAK: mobile_peak[0],
    }

    for element in StatusRegister:
        assert EXPECTED[element] == element.value.get_status(STGE)

    STGE = "003AC000"

    EXPECTED = {
        StatusRegister.DRY_CONTACT: 0,
        StatusRegister.TRIP_UNIT: trip_unit[0],
        StatusRegister.TERMINAL_COVER: 0,
        StatusRegister.OVERVOLTAGE: 0,
        StatusRegister.POWER_OVER_REF: 0,
        StatusRegister.PRODUCER: 0,
        StatusRegister.INJECTING: 0,
        StatusRegister.PROVIDER_INDEX: current_index[0],
        StatusRegister.DISTRIBUTOR_INDEX: current_index[3],
        StatusRegister.RTC_DEGRADED: 0,
        StatusRegister.TIC_STD: 1,
        StatusRegister.EURIDIS: euridis_status[3],
        StatusRegister.CPL_STATUS: cpl_status[1],
        StatusRegister.CPL_SYNC: 0,
        StatusRegister.COLOR_TODAY: tempo_color[0],
        StatusRegister.COLOR_NEXT_DAY: tempo_color[0],
        StatusRegister.MOBILE_PEAK_NOTICE: mobile_peak[0],
        StatusRegister.MOBILE_PEAK: mobile_peak[0],
    }

    for element in StatusRegister:
        assert EXPECTED[element] == element.value.get_status(STGE)
    
    STGE = "FFDFE7FD"

    EXPECTED = {
        StatusRegister.DRY_CONTACT: 1,
        StatusRegister.TRIP_UNIT: trip_unit[6],
        StatusRegister.TERMINAL_COVER: 1,
        StatusRegister.OVERVOLTAGE: 1,
        StatusRegister.POWER_OVER_REF: 1,
        StatusRegister.PRODUCER: 1,
        StatusRegister.INJECTING: 1,
        StatusRegister.PROVIDER_INDEX: current_index[9],
        StatusRegister.DISTRIBUTOR_INDEX: current_index[3],
        StatusRegister.RTC_DEGRADED: 1,
        StatusRegister.TIC_STD: 1,
        StatusRegister.EURIDIS: euridis_status[3],
        StatusRegister.CPL_STATUS: cpl_status[2],
        StatusRegister.CPL_SYNC: 1,
        StatusRegister.COLOR_TODAY: tempo_color[3],
        StatusRegister.COLOR_NEXT_DAY: tempo_color[3],
        StatusRegister.MOBILE_PEAK_NOTICE: mobile_peak[3],
        StatusRegister.MOBILE_PEAK: mobile_peak[3],
    }

    for element in StatusRegister:
        assert EXPECTED[element] == element.value.get_status(STGE)

def parse_stge(stge: str):
    for element in StatusRegister:
        print(element.name, element.value.get_status(stge))

if __name__ == "__main__":
    # Parse STGE, call this file as a module (python -m tests.test_status_register <STGE>)
    import sys
    if len(sys.argv) <= 1:
        print("No stge to parse.")
        sys.exit(1)
    parse_stge(sys.argv[1])