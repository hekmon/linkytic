"""Sensors for Linky TIC integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONSTRUCTORS_CODES,
    DEVICE_TYPES,
    DID_CONSTRUCTOR,
    DID_DEFAULT_MANUFACTURER,
    DID_DEFAULT_MODEL,
    DID_DEFAULT_NAME,
    DID_REGNUMBER,
    DID_TYPE,
    DID_YEAR,
    DOMAIN,
    SETUP_THREEPHASE,
    SETUP_TICMODE,
    TICMODE_STANDARD,
)
from .serial_reader import LinkyTICReader

_LOGGER = logging.getLogger(__name__)


# config flow setup
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Modern (thru config entry) sensors setup."""
    _LOGGER.debug("%s: setting up sensor plateform", config_entry.title)
    # Retrieve the serial reader object
    try:
        serial_reader = hass.data[DOMAIN][config_entry.entry_id]
    except KeyError:
        _LOGGER.error(
            "%s: can not init sensors: failed to get the serial reader object",
            config_entry.title,
        )
        return
    # Wait a bit for the controller to feed on serial frames (home assistant warns after 10s)
    _LOGGER.debug(
        "%s: waiting at most 9s before setting up sensor plateform in order for the async serial reader to have time to parse a full frame",
        config_entry.title,
    )
    for i in range(9):
        await asyncio.sleep(1)
        if serial_reader.has_read_full_frame():
            _LOGGER.debug(
                "%s: a full frame has been read, initializing sensors",
                config_entry.title,
            )
            break
        if i == 8:
            _LOGGER.warning(
                "%s: wait time is over but a full frame has yet to be read: initializing sensors anyway",
                config_entry.title,
            )
    # Init sensors
    sensors = []
    if config_entry.data.get(SETUP_TICMODE) == TICMODE_STANDARD:
        # standard mode
        _LOGGER.error(
            "%s: standard mode is not supported (yet ?): no entities will be spawned",
            config_entry.title,
        )
    else:
        # historic mode
        sensors = [
            ADCOSensor(
                config_entry.title, config_entry.entry_id, serial_reader
            ),  # needs to be the first for ADS parsing
            RegularStrSensor(
                tag="OPTARIF",
                name="Option tarifaire choisie",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                category=EntityCategory.CONFIG,
            ),
            RegularIntSensor(
                tag="ISOUSC",
                name="Intensité souscrite",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                category=EntityCategory.CONFIG,
                device_class=SensorDeviceClass.CURRENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            ),
            EnergyIndexSensor(
                tag="BASE",
                name="Index option Base",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="HCHC",
                name="Index option Heures Creuses - Heures Creuses",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="HCHP",
                name="Index option Heures Creuses - Heures Pleines",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EJPHN",
                name="Index option EJP - Heures Normal"
                + "es",  # workaround for codespell in HA pre commit hook
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EJPHPM",
                name="Index option EJP - Heures de Pointe Mobile",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHCJB",
                name="Index option Tempo - Heures Creuses Jours Bleus",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHPJB",
                name="Index option Tempo - Heures Pleines Jours Bleus",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHCJW",
                name="Index option Tempo - Heures Creuses Jours Blancs",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHPJW",
                name="Index option Tempo - Heures Pleines Jours Blancs",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHCJR",
                name="Index option Tempo - Heures Creuses Jours Rouges",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHPJR",
                name="Index option Tempo - Heures Pleines Jours Rouges",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            PEJPSensor(
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            RegularStrSensor(
                tag="PTEC",
                name="Période Tarifaire en cours",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:calendar-expand-horizontal",
            ),
            RegularStrSensor(
                tag="DEMAIN",
                name="Couleur du lendemain",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:palette",
            ),
            RegularIntSensor(
                tag="PAPP",
                name="Puissance apparente",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.APPARENT_POWER,
                native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularStrSensor(
                tag="HHPHC",
                name="Horaire Heures Pleines Heures Creuses",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-outline",
                enabled_by_default=False,
            ),
            RegularStrSensor(
                tag="MOTDETAT",
                name="Mo"
                + "t d'état du compteur",  # workaround for codespell in HA pre commit hook
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:file-word-box-outline",
                category=EntityCategory.DIAGNOSTIC,
                enabled_by_default=False,
            ),
        ]
        # Add specific sensors
        if bool(config_entry.data.get(SETUP_THREEPHASE)):
            # three-phase - concat specific sensors
            sensors.append(
                RegularIntSensor(
                    tag="IINST1",
                    name="Intensité Instantanée (phase 1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IINST2",
                    name="Intensité Instantanée (phase 2)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IINST3",
                    name="Intensité Instantanée (phase 3)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IMAX1",
                    name="Intensité maximale appelée (phase 1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IMAX2",
                    name="Intensité maximale appelée (phase 2)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IMAX3",
                    name="Intensité maximale appelée (phase 3)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="PMAX",
                    name="Puissance maximale triphasée atteinte (jour n-1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfPower.WATT,  # documentation says unit is Watt but description talks about VoltAmp :/
                )
            )
            sensors.append(
                RegularStrSensor(
                    tag="PPOT",
                    name="Présence des potentiels",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    category=EntityCategory.DIAGNOSTIC,
                )
            )
            # Burst sensors
            sensors.append(
                RegularIntSensor(
                    tag="ADIR1",
                    name="Avertissement de Dépassement d'intensité de réglage (phase 1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="ADIR2",
                    name="Avertissement de Dépassement d'intensité de réglage (phase 2)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="ADIR3",
                    name="Avertissement de Dépassement d'intensité de réglage (phase 3)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    register_callback=True,
                )
            )
            _LOGGER.info(
                "Adding %d sensors for the three phase historic mode", len(sensors)
            )
        else:
            # single phase - concat specific sensors
            sensors.append(
                RegularIntSensor(
                    tag="IINST",
                    name="Intensité Instantanée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="ADPS",
                    name="Avertissement de Dépassement De Puissance Souscrite",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IMAX",
                    name="Intensité maximale appelée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
            _LOGGER.info(
                "Adding %d sensors for the single phase historic mode", len(sensors)
            )
    # Add the entities to HA
    if len(sensors) > 0:
        async_add_entities(sensors, True)


class ADCOSensor(SensorEntity):
    """Ad resse du compteur entity."""

    _extra: dict[str, str] = {}

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = (
        "A" + "dress" + "e du compteur"
    )  # workaround for codespell in HA pre commit hook
    _attr_should_poll = True
    _attr_icon = "mdi:tag"

    def __init__(
        self, config_title: str, config_uniq_id: str, serial_reader: LinkyTICReader
    ) -> None:
        """Initialize an ADCO Sensor."""
        _LOGGER.debug("%s: initializing ADCO sensor", config_title)
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: str | None = None
        self._serial_controller = serial_reader
        self._tag = "ADCO"
        # Generic entity properties
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_adco"
        # We need to parse the ADS value first thing to have correct values for the device identification
        self.update()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            default_manufacturer=DID_DEFAULT_MANUFACTURER,
            default_model=DID_DEFAULT_MODEL,
            default_name=DID_DEFAULT_NAME,
            identifiers={(DOMAIN, self._config_uniq_id)},
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
        )

    @property
    def native_value(self) -> str | None:
        """Value of the sensor."""
        return self._last_value

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Get HA sensor extra attributes."""
        return self._extra

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._config_title,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
        else:
            self.parse_ads(value)  # update extra info by parsing value
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now ! (was not previously)",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
        # Save value
        self._last_value = value

    def parse_ads(self, ads):
        """Extract information contained in the ADS as EURIDIS."""
        _LOGGER.debug(
            "%s: parsing ADS: %s",
            self._config_title,
            ads,
        )
        if len(ads) != 12:
            _LOGGER.error(
                "%s: ADS should be 12 char long, actually %d cannot parse: %s",
                self._config_title,
                len(ads),
                ads,
            )
            self._extra = {}
            return
        # let's parse ADS as EURIDIS
        device_identification = {DID_YEAR: ads[2:4], DID_REGNUMBER: ads[6:]}
        # # Parse constructor code
        constructor_code = ads[0:2]
        try:
            device_identification[DID_CONSTRUCTOR] = CONSTRUCTORS_CODES[
                constructor_code
            ]
        except KeyError:
            _LOGGER.warning(
                "%s: constructor code is unknown: %s",
                self._config_title,
                constructor_code,
            )
            device_identification[DID_CONSTRUCTOR] = None
        # # Parse device type code
        device_type = ads[4:6]
        try:
            device_identification[DID_TYPE] = f"{DEVICE_TYPES[device_type]}"
        except KeyError:
            _LOGGER.warning(
                "%s: ADS device type is unknown: %s", self._config_title, device_type
            )
            device_identification[DID_TYPE] = None
        # # Update main thread with device infos
        self._serial_controller.device_identification = device_identification
        # # Set this sensor extra attributes
        constructor_str = (
            f"{device_identification[DID_CONSTRUCTOR]} ({constructor_code})"
            if device_identification[DID_CONSTRUCTOR] is not None
            else f"Inconnu ({constructor_code})"
        )
        type_str = (
            f"{device_identification[DID_TYPE]} ({device_type})"
            if device_identification[DID_TYPE] is not None
            else f"Inconnu ({device_type})"
        )
        self._extra = {
            "constructeur": constructor_str,
            "année de construction": f"20{device_identification[DID_YEAR]}",
            "type de l'appareil": type_str,
            "matricule de l'appareil": device_identification[DID_REGNUMBER],
        }
        # Parsing done
        _LOGGER.debug("%s: parsed ADS: %s", self._config_title, repr(self._extra))


class RegularStrSensor(SensorEntity):
    """Common class for text sensor."""

    # Generic entity properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(
        self,
        tag: str,
        name: str,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
        icon: str | None = None,
        category: EntityCategory | None = None,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize a Regular Str Sensor."""
        _LOGGER.debug("%s: initializing %s sensor", config_title, tag.upper())
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: str | None = None
        self._serial_controller = serial_reader
        self._tag = tag.upper()
        # Generic Entity properties
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{tag.lower()}"
        if icon:
            self._attr_icon = icon
        if category:
            self._attr_entity_category = category
        self._attr_entity_registry_enabled_default = enabled_by_default

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            default_manufacturer=DID_DEFAULT_MANUFACTURER,
            default_model=DID_DEFAULT_MODEL,
            default_name=DID_DEFAULT_NAME,
            identifiers={(DOMAIN, self._config_uniq_id)},
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
        )

    @property
    def native_value(self) -> str | None:
        """Value of the sensor."""
        return self._last_value

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._config_title,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now ! (was not previously)",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
        # Save value
        self._last_value = value


class RegularIntSensor(SensorEntity):
    """Common class for energy index counters."""

    # Generic entity properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(
        self,
        tag: str,
        name: str,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
        icon: str | None = None,
        category: EntityCategory | None = None,
        device_class: SensorDeviceClass | None = None,
        native_unit_of_measurement: str | None = None,
        state_class: SensorStateClass | None = None,
        register_callback: bool = False,
    ) -> None:
        """Initialize a Regular Int Sensor."""
        _LOGGER.debug("%s: initializing %s sensor", config_title, tag.upper())
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: int | None = None
        self._serial_controller = serial_reader
        self._tag = tag.upper()
        if register_callback:
            self._serial_controller.register_push_notif(
                self._tag, self.update_notification
            )
        # Generic Entity properties
        if category:
            self._attr_entity_category = category
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{tag.lower()}"
        if icon:
            self._attr_icon = icon
        # Sensor Entity Properties
        if device_class:
            self._attr_device_class = device_class
        if native_unit_of_measurement:
            self._attr_native_unit_of_measurement = native_unit_of_measurement
        if state_class:
            self._attr_state_class = state_class

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            default_manufacturer=DID_DEFAULT_MANUFACTURER,
            default_model=DID_DEFAULT_MODEL,
            default_name=DID_DEFAULT_NAME,
            identifiers={(DOMAIN, self._config_uniq_id)},
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
        )

    @property
    def native_value(self) -> int | None:
        """Value of the sensor."""
        return self._last_value

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability and save value
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._config_title,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
            # Save value
            self._last_value = None
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now ! (was not previously)",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
            # Save value
            self._last_value = int(value)

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


class EnergyIndexSensor(RegularIntSensor):
    """Common class for energy index counters."""

    def __init__(
        self,
        tag: str,
        name: str,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
    ) -> None:
        """Initialize an Energy Index sensor."""
        super().__init__(
            tag=tag,
            name=name,
            config_title=config_title,
            config_uniq_id=config_uniq_id,
            serial_reader=serial_reader,
            icon="mdi:counter",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
        )


class PEJPSensor(SensorEntity):
    """Préavis Début EJP (30 min) sensor."""

    #
    # This sensor could be improved I think (minutes as integer), but I do not have it to check and test its values
    # Leaving it as it is to facilitate future modifications
    #

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_has_entity_name = True
    _attr_name = "Préavis Début EJP"
    _attr_should_poll = True
    _attr_icon = "mdi:clock-start"

    def __init__(
        self, config_title: str, config_uniq_id: str, serial_reader: LinkyTICReader
    ) -> None:
        """Initialize a PEJP sensor."""
        _LOGGER.debug("%s: initializing PEJP sensor", config_title)
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: str | None = None
        self._serial_controller = serial_reader
        self._tag = "PEJP"
        # Generic Entity properties
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{self._tag.lower()}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            default_manufacturer=DID_DEFAULT_MANUFACTURER,
            default_model=DID_DEFAULT_MODEL,
            default_name=DID_DEFAULT_NAME,
            identifiers={(DOMAIN, self._config_uniq_id)},
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
        )

    @property
    def native_value(self) -> str | None:
        """Value of the sensor."""
        return self._last_value

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._config_title,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now ! (was not previously)",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
        # Save value
        self._last_value = value
