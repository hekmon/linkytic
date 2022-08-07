"""Energy sensors for Linky (LiXee-TIC-DIN) integration"""
from __future__ import annotations
import asyncio
import logging

from homeassistant.const import(
    ENERGY_WATT_HOUR,
    ELECTRIC_CURRENT_AMPERE,
    POWER_VOLT_AMPERE
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass
)
from homeassistant.core import (
    HomeAssistant,
    callback
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    SERIAL_READER,
    CONF_STANDARD_MODE,
    CONF_THREE_PHASE
)


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Linky (LiXee-TIC-DIN) sensor platform."""
    serial_reader = discovery_info[SERIAL_READER]
    # Wait a bit for the controller to feed on serial frames (home assistant warns after 10s)
    _LOGGER.debug(
        "waiting at most 9s before setting up sensor plateform in order for the async serial reader to have time to parse a full frame"
    )
    for i in range(9):
        await asyncio.sleep(1)
        if serial_reader.has_read_full_frame():
            _LOGGER.debug("a full frame has been read, initializing sensors")
            break
        if i == 10:
            _LOGGER.debug("wait time is over, initializing sensors anyway")
    # Init sensors
    sensors = []
    if discovery_info[CONF_STANDARD_MODE]:
        _LOGGER.error(
            "standard mode is not supported (yet ?): no entities will be spawned")
    else:
        # historic mode
        if discovery_info[CONF_THREE_PHASE]:
            _LOGGER.error(
                "three-phase historic mode is not supported (yet ?): no entities will be spawned")
        else:
            # single phase
            sensors = [
                ADCOSensor(serial_reader),
                RegularStrSensor(serial_reader,
                                 "OPTARIF", "Option tarifaire choisie", "mdi:cash-check",
                                 category=EntityCategory.CONFIG),
                RegularIntSensor(serial_reader,
                                 "ISOUSC", "Intensité souscrite",
                                 category=EntityCategory.CONFIG,
                                 device_class=SensorDeviceClass.CURRENT,
                                 native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE),
                EnergyIndexSensor(serial_reader,
                                  "BASE", "Index option Base"),
                EnergyIndexSensor(serial_reader,
                                  "HCHC", "Index option Heures Creuses - Heures Creuses"),
                EnergyIndexSensor(serial_reader,
                                  "HCHP", "Index option Heures Creuses - Heures Pleines"),
                EnergyIndexSensor(serial_reader,
                                  "EJPHN", "Index option EJP - Heures Normales"),
                EnergyIndexSensor(serial_reader,
                                  "EJPHPM", "Index option EJP - Heures de Pointe Mobile"),
                EnergyIndexSensor(serial_reader,
                                  "BBRHCJB", "Index option Tempo - Heures Creuses Jours Bleus"),
                EnergyIndexSensor(serial_reader,
                                  "BBRHPJB", "Index option Tempo - Heures Pleines Jours Bleus"),
                EnergyIndexSensor(serial_reader,
                                  "BBRHCJW", "Index option Tempo - Heures Creuses Jours Blancs"),
                EnergyIndexSensor(serial_reader,
                                  "BBRHPJW", "Index option Tempo - Heures Pleines Jours Blancs"),
                EnergyIndexSensor(serial_reader,
                                  "BBRHCJR", "Index option Tempo - Heures Creuses Jours Rouges"),
                EnergyIndexSensor(serial_reader,
                                  "BBRHPJR", "Index option Tempo - Heures Pleines Jours Rouges"),
                PEJPSensor(serial_reader),
                RegularStrSensor(serial_reader,
                                 "PTEC", "Période Tarifaire en cours", "mdi:calendar-expand-horizontal"),
                RegularStrSensor(serial_reader,
                                 "DEMAIN", "Couleur du lendemain", "mdi:palette"),
                RegularIntSensor(serial_reader,
                                 "IINST", "Intensité Instantanée",
                                 device_class=SensorDeviceClass.CURRENT,
                                 native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                                 state_class=SensorStateClass.MEASUREMENT),
                RegularIntSensor(serial_reader,
                                 "ADPS", "Avertissement de Dépassement De Puissance Souscrite",
                                 device_class=SensorDeviceClass.CURRENT,
                                 native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                                 state_class=SensorStateClass.MEASUREMENT),
                RegularIntSensor(serial_reader,
                                 "IMAX", "Intensité maximale appelée",
                                 device_class=SensorDeviceClass.CURRENT,
                                 native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE),
                RegularIntSensor(serial_reader,
                                 "PAPP", "Puissance apparente",
                                 device_class=SensorDeviceClass.APPARENT_POWER,
                                 native_unit_of_measurement=POWER_VOLT_AMPERE,
                                 state_class=SensorStateClass.MEASUREMENT),
                RegularStrSensor(serial_reader,
                                 "HHPHC", "Horaire Heures Pleines Heures Creuses", "mdi:clock-outline",
                                 enabled_by_default=False),
                RegularStrSensor(serial_reader,
                                 "MOTDETAT", "Mot d'état du compteur", "mdi:file-word-box-outline",
                                 category=EntityCategory.DIAGNOSTIC,
                                 enabled_by_default=False),
            ]
            _LOGGER.info(
                "adding %d sensors for the single phase historic mode", len(sensors))
    if len(sensors) > 0:
        async_add_entities(sensors, False)


class ADCOSensor(SensorEntity):
    """Adresse du compteur entity"""

    _serial_controller = None
    _extra = {}

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Linky - Adresse du compteur"
    _attr_should_poll = True
    _attr_unique_id = "linky_adco"
    _attr_icon = "mdi:tag"

    def __init__(self, serial_reader):
        _LOGGER.debug("initializing ADCO sensor")
        self._serial_controller = serial_reader

    @property
    def native_value(self) -> str | None:
        """Value of the sensor"""
        value, _ = self._serial_controller.get_values("ADCO")
        _LOGGER.debug(
            "recovered ADCO value from serial controller: %s", value)
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "marking the ADCO sensor as unavailable: a full frame has been read but ADCO has not been found")
                self._attr_available = False
            return value
        # else
        # update extra info by parsing value
        self.parse_ads(value)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return self._extra

    @callback
    def update(self):
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "recovered %s value from serial controller: %s", self._tag, repr(value))
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._tag, self._tag
                )
                self._attr_available = False
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "marking the %s sensor as available now ! (was not previously)", self._tag
                )
                self._attr_available = True

    def parse_ads(self, ads):
        """Extract informations contained in the ADS as EURIDIS"""
        if len(ads) != 12:
            _LOGGER.error(
                "ADS should be 12 char long, actually %d cannot parse: %s", len(ads), ads)
            self._extra = {}
            return
        # let's parse ADS as EURIDIS
        extra = {
            'code constructeur': ads[0:2],
            'année de construction': "20{}".format(ads[2:4]),
            "matricule de l'appareil": ads[6:],
        }
        device_type_key = "type de l'appareil"
        device_type = ads[4:6]
        if device_type == "61":
            extra[
                device_type_key] = "Compteur monophasé 60 A généralisation Linky G3 - arrivée puissance haute (61)"
        elif device_type == "62":
            extra[
                device_type_key] = "Compteur monophasé 90 A généralisation Linky G1 - arrivée puissance basse (62)"
        elif device_type == "63":
            extra[
                device_type_key] = "Compteur triphasé 60 A généralisation Linky G1 - arrivée puissance basse (63)"
        elif device_type == "64":
            extra[
                device_type_key] = "Compteur monophasé 60 A généralisation Linky G3 - arrivée puissance basse (64)"
        elif device_type == "70":
            extra[device_type_key] = "Compteur monophasé Linky 60 A mise au point G3 (70)"
        elif device_type == "71":
            extra[device_type_key] = "Compteur triphasé Linky 60 A mise au point G3 (71)"
        elif device_type == "75":
            extra[
                device_type_key] = "Compteur monophasé 90 A généralisation Linky G3 - arrivée puissance basse (75)"
        elif device_type == "76":
            extra[
                device_type_key] = "Compteur triphasé 60 A généralisation Linky G3 - arrivée puissance basse (76)"
        else:
            _LOGGER.warning(
                "ADS device type is unknown: %s", device_type)
            extra[device_type_key] = device_type
        _LOGGER.debug("parsed ADS: %s", repr(extra))
        self._extra = extra


class RegularStrSensor(SensorEntity):
    """common class for text sensor"""

    _serial_controller = None

    # Generic entity properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_should_poll = True

    def __init__(self, serial_reader, tag: str, name: str, icon: str | None = None,
                 category: EntityCategory | None = None, enabled_by_default: bool = True):
        _LOGGER.debug("initializing %s sensor", tag.upper())
        self._serial_controller = serial_reader
        self._tag = tag.upper()
        # Generic entity properties
        if category:
            self._attr_entity_category = category
        self._attr_name = "Linky - {}".format(name)
        self._attr_unique_id = "linky_{}".format(tag.lower())
        if icon:
            self._attr_icon = icon
        self._attr_entity_registry_enabled_default = enabled_by_default

    @property
    def native_value(self) -> str | None:
        """Value of the sensor"""
        value, _ = self._serial_controller.get_values(self._tag)
        return value

    @callback
    def update(self):
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "recovered %s value from serial controller: %s", self._tag, repr(value))
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._tag, self._tag
                )
                self._attr_available = False
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "marking the %s sensor as available now ! (was not previously)", self._tag
                )
                self._attr_available = True


class RegularIntSensor(SensorEntity):
    """common class for energy index counters"""

    _serial_controller = None

    # Generic entity properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_should_poll = True

    def __init__(self, serial_reader, tag: str, name: str, icon: str | None = None,
                 category: EntityCategory | None = None, device_class: SensorDeviceClass | None = None,
                 native_unit_of_measurement: str | None = None, state_class: SensorStateClass | None = None):
        _LOGGER.debug("initializing %s sensor", tag.upper())
        self._serial_controller = serial_reader
        self._tag = tag.upper()
        # Generic entity properties
        if category:
            self._attr_entity_category = category
        self._attr_name = "Linky - {}".format(name)
        self._attr_unique_id = "linky_{}".format(tag.lower())
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
    def native_value(self) -> int | None:
        """Value of the sensor"""
        raw_value, _ = self._serial_controller.get_values(self._tag)
        if raw_value is not None:
            return int(raw_value)
        # else
        return None

    @callback
    def update(self):
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "recovered %s value from serial controller: %s", self._tag, repr(value))
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._tag, self._tag
                )
                self._attr_available = False
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "marking the %s sensor as available now ! (was not previously)", self._tag
                )
                self._attr_available = True


class EnergyIndexSensor(RegularIntSensor):
    """common class for energy index counters"""

    def __init__(self, serial_reader, tag, name):
        super().__init__(serial_reader, tag, name,
                         icon="mdi:counter",
                         device_class=SensorDeviceClass.ENERGY,
                         native_unit_of_measurement=ENERGY_WATT_HOUR,
                         state_class=SensorStateClass.TOTAL_INCREASING)


class PEJPSensor(SensorEntity):
    """Préavis Début EJP (30 min) sensor"""

    #
    # This sensor could be improved I think (minutes as integer), but I do not have it to check and test its values
    # Leaving it as it is to facilitate future modifications
    #

    _serial_controller = None

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_name = "Linky - Préavis Début EJP"
    _attr_should_poll = True
    _attr_unique_id = "linky_pejp"
    _attr_icon = "mdi:clock-start"

    def __init__(self, serial_reader):
        _LOGGER.debug("initializing PEJP sensor")
        self._serial_controller = serial_reader

    @property
    def native_value(self) -> str | None:
        """Value of the sensor"""
        value, _ = self._serial_controller.get_values("PEJP")
        return value

    @callback
    def update(self):
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "recovered %s value from serial controller: %s", self._tag, repr(value))
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._tag, self._tag
                )
                self._attr_available = False
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "marking the %s sensor as available now ! (was not previously)", self._tag
                )
                self._attr_available = True
