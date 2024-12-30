"""Sensors for Linky TIC integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, cast

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import (
    DID_CONSTRUCTOR,
    DID_CONSTRUCTOR_CODE,
    DID_REGNUMBER,
    DID_TYPE,
    DID_TYPE_CODE,
    DID_YEAR,
    SETUP_PRODUCER,
    SETUP_THREEPHASE,
    SETUP_TICMODE,
    TICMODE_STANDARD,
)
from .entity import LinkyTICEntity
from .serial_reader import LinkyTICReader
from .status_register import StatusRegister

_LOGGER = logging.getLogger(__name__)

REACTIVE_ENERGY = "VArh"


def _parse_timestamp(raw: str):
    """Parse the raw timestamp string into human readable form."""
    return (
        f"{raw[5:7]}/{raw[3:5]}/{raw[1:3]} "
        f"{raw[7:9]}:{raw[9:11]} "
        f"({'Eté' if raw[0] == 'E' else 'Hiver'})"
    )


@dataclass(frozen=True, kw_only=True)
class LinkyTicSensorConfig(SensorEntityDescription):
    """Sensor configuration dataclass."""

    fallback_tags: tuple[str, ...] | None = (
        None  # Multiple tags are allowed for non-standard linky tags support, see hekmon/linky#42
    )
    register_callback: bool = False
    conversion: Callable | None = None


@dataclass(frozen=True, kw_only=True)
class SerialNumberSensorConfig(LinkyTicSensorConfig):
    """Sensor configuration dataclass."""

    translation_key: str | None = "serial_number"
    entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC


@dataclass(frozen=True, kw_only=True)
class ApparentPowerSensorConfig(LinkyTicSensorConfig):
    """Configuration for apparent power sensors."""

    device_class: SensorDeviceClass | None = SensorDeviceClass.APPARENT_POWER
    native_unit_of_measurement: str | None = UnitOfApparentPower.VOLT_AMPERE


@dataclass(frozen=True, kw_only=True)
class ActivePowerSensorConfig(LinkyTicSensorConfig):
    """Configuration for active power sensors."""

    device_class: SensorDeviceClass | None = SensorDeviceClass.POWER
    native_unit_of_measurement: str | None = UnitOfPower.WATT


@dataclass(frozen=True, kw_only=True)
class VoltageSensorConfig(LinkyTicSensorConfig):
    """Configuration for voltage sensors."""

    device_class: SensorDeviceClass | None = SensorDeviceClass.VOLTAGE
    native_unit_of_measurement: str | None = UnitOfElectricPotential.VOLT


@dataclass(frozen=True, kw_only=True)
class ElectricalCurrentSensorConfig(LinkyTicSensorConfig):
    """Configuration for electrical current sensors."""

    device_class: SensorDeviceClass | None = SensorDeviceClass.CURRENT
    native_unit_of_measurement: str | None = UnitOfElectricCurrent.AMPERE


@dataclass(frozen=True, kw_only=True)
class ActiveEnergySensorConfig(LinkyTicSensorConfig):
    """Configuration for active energy sensors."""

    device_class: SensorDeviceClass | None = SensorDeviceClass.ENERGY
    native_unit_of_measurement: str | None = UnitOfEnergy.WATT_HOUR
    state_class: SensorStateClass | str | None = SensorStateClass.TOTAL_INCREASING


@dataclass(frozen=True, kw_only=True)
class ReactiveEnergySensorConfig(LinkyTicSensorConfig):
    """Configuration for reactive energy sensors."""

    device_class: SensorDeviceClass | None = SensorDeviceClass.REACTIVE_POWER
    native_unit_of_measurement: str | None = REACTIVE_ENERGY


@dataclass(frozen=True, kw_only=True)
class StatusRegisterSensorConfig(LinkyTicSensorConfig):
    """Configuration for status register sensors."""

    key: str = "STGE"
    status_field: StatusRegister


REGISTRY: dict[type[LinkyTicSensorConfig], type[LinkyTICSensor]] = {}


def match(*configs: type[LinkyTicSensorConfig]):
    """Associate one or more sensor config to a sensor class."""

    def wrap(cls):
        for config in configs:
            REGISTRY[config] = cls
        return cls

    return wrap


SENSORS_HISTORIC_COMMON: tuple[LinkyTicSensorConfig, ...] = (
    SerialNumberSensorConfig(key="ADCO"),
    LinkyTicSensorConfig(
        key="OPTARIF",
        translation_key="tarif_option",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ElectricalCurrentSensorConfig(
        key="ISOUSC",
        translation_key="subcription_current",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ActiveEnergySensorConfig(
        key="BASE",
        translation_key="index_base",
    ),
    ActiveEnergySensorConfig(
        key="HCHC",
        translation_key="index_hchc",
    ),
    ActiveEnergySensorConfig(
        key="HCHP",
        translation_key="index_hchp",
    ),
    ActiveEnergySensorConfig(
        key="EJPHN",
        translation_key="index_ejp_normal",
    ),
    ActiveEnergySensorConfig(
        key="EJPJPM",
        translation_key="index_ejp_peak",
    ),
    ActiveEnergySensorConfig(
        key="BBRHCJB",
        translation_key="index_tempo_bluehc",
    ),
    ActiveEnergySensorConfig(
        key="BBRHPJB",
        translation_key="index_tempo_bluehp",
    ),
    ActiveEnergySensorConfig(
        key="BBRHCJW",
        translation_key="index_tempo_whitehc",
    ),
    ActiveEnergySensorConfig(
        key="BBRHPJW",
        translation_key="index_tempo_whitehp",
    ),
    ActiveEnergySensorConfig(
        key="BBRHCJR",
        translation_key="index_tempo_redhc",
    ),
    ActiveEnergySensorConfig(
        key="BBRHPJR",
        translation_key="index_tempo_redhp",
    ),
    LinkyTicSensorConfig(
        key="PTEC",
        translation_key="current_tarif",
    ),
    LinkyTicSensorConfig(
        key="PEJP",
        translation_key="peak_notice",
    ),
    LinkyTicSensorConfig(
        key="DEMAIN",
        translation_key="tomorrow_color",
    ),
    ApparentPowerSensorConfig(
        key="PAPP",
        translation_key="apparent_power",
        state_class=SensorStateClass.MEASUREMENT,
        register_callback=True,
    ),
    LinkyTicSensorConfig(
        key="HHPHC",
        translation_key="peak_hour_schedule",
    ),
    LinkyTicSensorConfig(
        key="MOTDETAT",
        translation_key="meter_state",
    ),
)

SENSORS_HISTORIC_SINGLEPHASE: tuple[LinkyTicSensorConfig, ...] = (
    ElectricalCurrentSensorConfig(
        key="IINST",
        translation_key="inst_current",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ElectricalCurrentSensorConfig(
        key="ADPS",
        translation_key="overcurrent_warning",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ElectricalCurrentSensorConfig(
        key="IMAX",
        translation_key="max_current",
    ),
)

SENSORS_HISTORIC_TREEPHASE: tuple[LinkyTicSensorConfig, ...] = (
    # IINST1, IINST2, IINST3
    *(
        ElectricalCurrentSensorConfig(
            key=f"IINST{phase}",
            translation_key=f"inst_current_ph{phase}",
            state_class=SensorStateClass.MEASUREMENT,
        )
        for phase in (1, 2, 3)
    ),
    #  ADIR1, ADIR2, ADIR3
    *(
        ElectricalCurrentSensorConfig(
            key=f"ADIR{phase}",
            translation_key=f"overcurrent_warning_ph{phase}",
            state_class=SensorStateClass.MEASUREMENT,
        )
        for phase in (1, 2, 3)
    ),
    *(
        ElectricalCurrentSensorConfig(
            key=f"IMAX{phase}",
            translation_key=f"max_current_ph{phase}",
        )
        for phase in (1, 2, 3)
    ),
    ApparentPowerSensorConfig(
        key="PMAX",
        translation_key="max_power_n-1",
    ),
    LinkyTicSensorConfig(
        key="PPOT",
        translation_key="potentials_presence",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

SENSORS_STANDARD_COMMON: tuple[LinkyTicSensorConfig, ...] = (
    SerialNumberSensorConfig(key="ADSC"),
    LinkyTicSensorConfig(
        key="VTIC",
        translation_key="tic_version",
    ),
    LinkyTicSensorConfig(
        key="DATE",
        translation_key="datetime",
        conversion=_parse_timestamp,
    ),  # Useful in any way?
    LinkyTicSensorConfig(
        key="NGTF",
        translation_key="tarif_name",
    ),
    LinkyTicSensorConfig(
        key="LTARF",
        translation_key="current_tarif_label",
    ),
    ActiveEnergySensorConfig(
        key="EAST",
        translation_key="active_energy_drawn_total",
    ),
    #  EASF01, ... , EASF09
    *(
        ActiveEnergySensorConfig(
            key=f"EASF{index:02}",
            translation_key=f"active_energy_provider_{index}",
        )
        for index in range(1, 10)
    ),
    #  EASD01, ... , EASD04
    *(
        ActiveEnergySensorConfig(
            key=f"EASD{index:02}",
            translation_key=f"active_energy_distributor_{index}",
        )
        for index in range(1, 5)
    ),
    ElectricalCurrentSensorConfig(
        key="IRMS1",
        translation_key="rms_current_ph1",
        state_class=SensorStateClass.MEASUREMENT,
        register_callback=True,
    ),
    VoltageSensorConfig(
        key="URMS1",
        translation_key="rms_voltage_ph1",
        state_class=SensorStateClass.MEASUREMENT,
        register_callback=True,
    ),
    ApparentPowerSensorConfig(
        key="PREF",
        translation_key="ref_power",
        entity_category=EntityCategory.DIAGNOSTIC,
        conversion=(lambda x: x * 1000),  # kVA to VA conversion
    ),
    ApparentPowerSensorConfig(
        key="PCOUP",
        translation_key="trip_power",
        entity_category=EntityCategory.DIAGNOSTIC,
        conversion=(lambda x: x * 1000),  # kVA to VA conversion
    ),
    ApparentPowerSensorConfig(
        key="SINSTS",
        translation_key="instantaneous_apparent_power",
        fallback_tags=("SINST1",),  # See hekmon/linkytic#42
        state_class=SensorStateClass.MEASUREMENT,
        register_callback=True,
    ),
    ApparentPowerSensorConfig(
        key="SMAXSN",
        translation_key="apparent_power_max_n",
        fallback_tags=("SMAXN",),  # See hekmon/linkytic#42
        register_callback=True,
    ),
    ApparentPowerSensorConfig(
        key="SMAXSN-1",
        translation_key="apparent_power_max_n-1",
        fallback_tags=("SMAXN-1",),  # See hekmon/linkytic#42
        register_callback=True,
    ),
    ActivePowerSensorConfig(
        key="CCASN",
        translation_key="power_load_curve_n",
    ),
    ActivePowerSensorConfig(
        key="CCASN-1",
        translation_key="power_load_curve_n-1",
    ),
    VoltageSensorConfig(
        key="UMOY1",
        translation_key="mean_voltage_ph1",
        state_class=SensorStateClass.MEASUREMENT,
        register_callback=True,
    ),
    #  DPM1, DPM2, DPM3
    *(
        LinkyTicSensorConfig(
            translation_key=f"mobile_peak_start_{index}",
            key=f"DPM{index}",
        )
        for index in (1, 2, 3)
    ),
    #  FPM1, FPM2, FPM3
    *(
        LinkyTicSensorConfig(
            translation_key=f"mobile_peak_end_{index}",
            key=f"FPM{index}",
        )
        for index in (1, 2, 3)
    ),
    LinkyTicSensorConfig(
        key="MSG1",
        translation_key="short_msg",
    ),
    LinkyTicSensorConfig(
        key="MSG2",
        translation_key="ultra_short_msg",
    ),
    LinkyTicSensorConfig(
        key="PRM",
        translation_key="delivery_point",
    ),
    LinkyTicSensorConfig(
        key="RELAIS",
        translation_key="relays",
    ),
    LinkyTicSensorConfig(
        key="NTARF",
        translation_key="current_tarif_index",
    ),
    LinkyTicSensorConfig(
        key="NJOURF",
        translation_key="calendar_index_today",
    ),
    LinkyTicSensorConfig(
        key="NJOURF+1",
        translation_key="calendar_index_tomorrow",
    ),
    LinkyTicSensorConfig(
        key="PJOURF+1",
        translation_key="calendar_profile_tomorrow",
        conversion=(lambda x: str(x).replace("NONUTILE", "").strip()),
    ),
    LinkyTicSensorConfig(
        key="PPOINTE",
        translation_key="next_peak_dat_profile",
    ),
    LinkyTicSensorConfig(
        key="STGE",
        translation_key="status_register",
    ),  # Duplicate? All fields are exposed as sensors or binary sensors
    StatusRegisterSensorConfig(
        translation_key="status_trip_device",
        status_field=StatusRegister.TRIP_UNIT,
    ),
    StatusRegisterSensorConfig(
        translation_key="status_tarif_provider",
        status_field=StatusRegister.PROVIDER_INDEX,
    ),
    StatusRegisterSensorConfig(
        translation_key="status_tarif_distributor",
        status_field=StatusRegister.DISTRIBUTOR_INDEX,
    ),
    StatusRegisterSensorConfig(
        translation_key="status_euridis",
        status_field=StatusRegister.EURIDIS,
    ),
    StatusRegisterSensorConfig(
        translation_key="status_cpl",
        status_field=StatusRegister.STATUS_CPL,
    ),
    StatusRegisterSensorConfig(
        translation_key="status_tempo_color_today",
        status_field=StatusRegister.COLOR_TODAY,
    ),
    StatusRegisterSensorConfig(
        translation_key="status_tempo_color_tomorrow",
        status_field=StatusRegister.COLOR_NEXT_DAY,
    ),
    StatusRegisterSensorConfig(
        translation_key="status_mobile_peak_notice",
        status_field=StatusRegister.MOBILE_PEAK_NOTICE,
    ),
    StatusRegisterSensorConfig(
        translation_key="status_mobile_peak", status_field=StatusRegister.MOBILE_PEAK
    ),
)

SENSORS_STANDARD_THREEPHASE: tuple[LinkyTicSensorConfig, ...] = (
    #  IRMS2, IRMS3
    *(
        ElectricalCurrentSensorConfig(
            key=f"IRMS{phase}",
            translation_key=f"rms_current_ph{phase}",
            state_class=SensorStateClass.MEASUREMENT,
            register_callback=True,
        )
        for phase in (2, 3)
    ),
    #  URMS2, URMS3
    *(
        VoltageSensorConfig(
            key=f"URMS{phase}",
            translation_key=f"rms_voltage_ph{phase}",
            state_class=SensorStateClass.MEASUREMENT,
            register_callback=True,
        )
        for phase in (2, 3)
    ),
    #  SINSTS1, SINSTS2, SINSTS3
    *(
        ApparentPowerSensorConfig(
            key=f"SINSTS{phase}",
            translation_key=f"instantaneous_apparent_power_ph{phase}",
            state_class=SensorStateClass.MEASUREMENT,
            register_callback=True,
        )
        for phase in (1, 2, 3)
    ),
    #  SMAXSN1, SMAXSN2, SMAXSN3
    *(
        ApparentPowerSensorConfig(
            key=f"SMAXSN{phase}",
            translation_key=f"apparent_power_max_n_ph{phase}",
            state_class=SensorStateClass.MEASUREMENT,
            register_callback=True,
        )
        for phase in (1, 2, 3)
    ),
    #  SMAXSN1-1, SMAXSN2-1, SMAXSN3-1
    *(
        ApparentPowerSensorConfig(
            key=f"SMAXSN{phase}-1",
            translation_key=f"apparent_power_max_n-1_ph{phase}",
            state_class=SensorStateClass.MEASUREMENT,
            register_callback=True,
        )
        for phase in (1, 2, 3)
    ),
    #  UMOY2, UMOY3
    *(
        VoltageSensorConfig(
            key=f"UMOY{phase}",
            translation_key=f"mean_voltage_ph{phase}",
            state_class=SensorStateClass.MEASUREMENT,
            register_callback=True,
        )
        for phase in (2, 3)
    ),
)

SENSORS_STANDARD_PRODUCER: tuple[LinkyTicSensorConfig, ...] = (
    ActiveEnergySensorConfig(
        key="EAIT",
        translation_key="active_energy_injected_total",
    ),
    #  ERQ1, ... , ERQ4
    *(
        ReactiveEnergySensorConfig(
            key=f"ERQ{index}",
            translation_key=f"reactive_energy_q{index}",
        )
        for index in range(1, 5)
    ),
    ApparentPowerSensorConfig(
        key="SINSTI",
        translation_key="instantaneous_apparent_power_injected",
        state_class=SensorStateClass.MEASUREMENT,
        register_callback=True,
    ),
    ApparentPowerSensorConfig(
        key="SMAXIN",
        translation_key="apparent_power_injected_max_n",
        register_callback=True,
    ),
    ApparentPowerSensorConfig(
        key="SMAXIN-1",
        translation_key="apparent_power_injected_max_n-1",
        register_callback=True,
    ),
    ActivePowerSensorConfig(
        key="CCAIN",
        translation_key="power_injected_load_curve_n",
    ),
    ActivePowerSensorConfig(
        key="CCAIN-1",
        translation_key="power_injected_load_curve_n-1",
    ),
)


# config flow setup
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry[LinkyTICReader],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Modern (thru config entry) sensors setup."""
    _LOGGER.debug("%s: setting up sensor plateform", config_entry.title)
    # Retrieve the serial reader object
    reader = config_entry.runtime_data

    is_standard = bool(config_entry.data.get(SETUP_TICMODE) == TICMODE_STANDARD)
    is_threephase = bool(config_entry.data.get(SETUP_THREEPHASE))
    is_producer = bool(config_entry.data.get(SETUP_PRODUCER))

    if is_standard:
        # Standard mode
        sensor_desc = [SENSORS_STANDARD_COMMON]

        if is_threephase:
            sensor_desc.append(SENSORS_STANDARD_THREEPHASE)

        if is_producer:
            sensor_desc.append(SENSORS_STANDARD_PRODUCER)

    else:
        # Historic mode
        sensor_desc = [SENSORS_HISTORIC_COMMON]

        sensor_desc.append(
            SENSORS_HISTORIC_SINGLEPHASE
            if is_threephase
            else SENSORS_HISTORIC_SINGLEPHASE
        )

    async_add_entities(
        (
            REGISTRY[type(config)](config, config_entry, reader)
            for descriptor in sensor_desc
            for config in descriptor
        ),
        update_before_add=True,
    )


T = TypeVar("T")


class LinkyTICSensor(LinkyTICEntity, SensorEntity, Generic[T]):
    """Base class for all Linky TIC sensor entities."""

    _attr_should_poll = True
    _last_value: T | None
    entity_description: LinkyTicSensorConfig

    def __init__(
        self,
        description: LinkyTicSensorConfig,
        config_entry: ConfigEntry,
        reader: LinkyTICReader,
    ) -> None:
        """Init sensor entity."""
        super().__init__(reader)

        self.entity_description = description
        self._last_value = None
        self._tag = description.key

        self._attr_unique_id = slugify(f"{reader.serial_number}_{description.key}")

    @property
    def native_value(self) -> T | None:  # type:ignore
        """Value of the sensor."""
        return self._last_value

    def _update(self) -> tuple[Optional[str], Optional[str]]:
        """Get value and/or timestamp from cached data. Responsible for updating sensor availability."""
        value, timestamp = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: (%s, %s)",
            self._serial_controller.name,
            self._tag,
            value,
            timestamp,
        )

        if (
            not value
            and not timestamp
            and self.entity_description.fallback_tags is not None
        ):
            # Fallback to other tags, if any
            for tag in self.entity_description.fallback_tags:
                value, timestamp = self._serial_controller.get_values(tag)
                if value or timestamp:
                    break

        if not value and not timestamp:  # No data returned.
            if not self.available:
                # Sensor is already unavailable, no need to check why.
                return None, None
            if not self._serial_controller.is_connected:
                _LOGGER.debug(
                    "%s: marking the %s sensor as unavailable: serial connection lost",
                    self._serial_controller.name,
                    self._tag,
                )
                self._attr_available = False
            elif self._serial_controller.has_read_full_frame:
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._serial_controller.name,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
            else:
                # A frame has not been read yet (it should!) or is already unavailable and no new data was fetched.
                # Let sensor in current availability state.
                pass
            return None, None

        if not self.available:
            # Data is available, so is sensor
            self._attr_available = True
            _LOGGER.info(
                "%s: marking the %s sensor as available now !",
                self._serial_controller.name,
                self._tag,
            )

        return value, timestamp


@match(SerialNumberSensorConfig)
class ADSSensor(LinkyTICSensor[str]):
    """Adresse du compteur entity."""  # codespell:ignore

    entity_description: SerialNumberSensorConfig

    def __init__(
        self,
        description: SerialNumberSensorConfig,
        config_entry: ConfigEntry,
        reader: LinkyTICReader,
    ) -> None:
        """Initialize an ADCO/ADSC Sensor."""
        super().__init__(description, config_entry, reader)

        # Overwrite tag-based unique id for compatibility between tic versions
        self._attr_unique_id = slugify(f"{reader.serial_number}_adco")
        self._extra: dict[str, str] = {}

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Get HA sensor extra attributes."""
        return self._extra

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._update()

        if not value:
            return

        # Set this sensor extra attributes
        did = self._serial_controller.device_identification
        self._extra = {
            "constructeur": f"{did[DID_CONSTRUCTOR] or 'Inconnu'} ({did[DID_CONSTRUCTOR_CODE]})",
            "année de construction": f"20{did[DID_YEAR]}",
            "type de l'appareil": f"{did[DID_TYPE] or 'Inconnu'} ({did[DID_TYPE_CODE]})",
            "matricule de l'appareil": did[DID_REGNUMBER] or "Inconnu",
        }
        # Save value
        self._last_value = value


@match(LinkyTicSensorConfig)
class LinkyTICStringSensor(LinkyTICSensor[str]):
    """Common class for text sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._update()
        if not value:
            return

        conversion = self.entity_description.conversion

        if conversion is not None:
            try:
                self._last_value = conversion(value)
            except TypeError as e:
                _LOGGER.debug("Couldn't convert value %s: %s", value, e)
                self._last_value = value
        else:
            self._last_value = " ".join(value.split())


@match(
    ApparentPowerSensorConfig,
    ActiveEnergySensorConfig,
    ReactiveEnergySensorConfig,
    ElectricalCurrentSensorConfig,
    VoltageSensorConfig,
    ActivePowerSensorConfig,
)
class RegularIntSensor(LinkyTICSensor[int]):
    """Common class for int sensors."""

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        value, _ = self._update()
        if not value:
            return
        try:
            value_int = int(value)
        except ValueError:
            return

        conversion = self.entity_description.conversion

        if conversion is not None:
            try:
                self._last_value = conversion(value_int)
            except TypeError as e:
                _LOGGER.debug("Couldn't convert value %s: %s", value_int, e)
                self._last_value = value_int
        else:
            self._last_value = value_int

    def update_notification(self, realtime_option: bool) -> None:
        """Receive a notification from the serial reader when our tag has been read on the wire."""
        # Realtime off
        if not realtime_option:
            _LOGGER.debug(
                "received a push notification for new %s data but user has not activated real time: skipping",
                self._tag,
            )
            if not self._attr_should_poll:
                self._attr_should_poll = (
                    True  # realtime option disable, HA should poll us
                )
            return
        # Realtime on
        _LOGGER.debug(
            "received a push notification for new %s data and user has activated real time: scheduling ha update",
            self._tag,
        )
        if self._attr_should_poll:
            self._attr_should_poll = False  # now that user has activated realtime, we will push data, no need for HA to poll us
        self.schedule_update_ha_state(force_refresh=True)


@match(StatusRegisterSensorConfig)
class LinkyTICStatusRegisterSensor(LinkyTICStringSensor):
    """Data from status register."""

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(
        self,
        description: StatusRegisterSensorConfig,
        config_entry: ConfigEntry,
        reader: LinkyTICReader,
    ) -> None:
        """Initialize a status register data sensor."""
        super().__init__(description, config_entry, reader)
        status_field = description.status_field
        self._field = status_field

        self._attr_unique_id = slugify(
            f"{reader.serial_number}_{description.status_field.name}"
        )
        # For SensorDeviceClass.ENUM, _attr_options contains all the possible values for the sensor.
        self._attr_options = list(
            cast(dict[int, str], status_field.value.options).values()
        )

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._update()

        if not value:
            return

        try:
            self._last_value = cast(str, self._field.value.get_status(value))
        except IndexError:
            pass  # Failsafe, value is unchanged.
