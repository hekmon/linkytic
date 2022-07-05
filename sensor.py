"""Energy sensors for Linky (LiXee-TIC-DIN) integration"""
from __future__ import annotations
import asyncio
import logging

from homeassistant.const import(
    ENERGY_WATT_HOUR,
    ELECTRIC_CURRENT_AMPERE
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import SERIAL_READER


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Linky (LiXee-TIC-DIN) sensor platform."""
    _LOGGER.debug(
        "waiting at most 9s before setting up sensor plateform in order for the async serial reader to parse a full frame")
    serial_reader = discovery_info[SERIAL_READER]
    # Wait a bit for the controller to feed on serial frames
    for i in range(10):
        if serial_reader.has_read_full_frame():
            _LOGGER.debug("a full frame has been read, initializing sensors")
            break
        if i == 10:
            _LOGGER.debug("wait time is over, initializing sensors anyway")
            break
        await asyncio.sleep(1)
    # Init sensors
    async_add_entities([ADCO(serial_reader)], False)
    async_add_entities([OPTARIF(serial_reader)], False)
    async_add_entities([ISOUSC(serial_reader)], False)
    async_add_entities([EnergyIndex(serial_reader, "BASE",
                       "Index option Base")], False)
    async_add_entities([EnergyIndex(serial_reader, "HCHC",
                       "Index option Heures Creuses - Heures Creuses")], False)
    async_add_entities([EnergyIndex(serial_reader, "HCHP",
                       "Index option Heures Creuses - Heures Pleines")], False)
    async_add_entities([EnergyIndex(serial_reader, "EJPHN",
                       "Index option EJP - Heures Normales")], False)
    async_add_entities([EnergyIndex(serial_reader, "EJPHPM",
                       "Index option EJP - Heures de Pointe Mobile")], False)
    async_add_entities([EnergyIndex(serial_reader, "BBRHCJB",
                       "Index option Tempo - Heures Creuses Jours Bleus")], False)
    async_add_entities([EnergyIndex(serial_reader, "BBRHPJB",
                       "Index option Tempo - Heures Pleines Jours Bleus")], False)
    async_add_entities([EnergyIndex(serial_reader, "BBRHCJW",
                       "Index option Tempo - Heures Creuses Jours Blancs")], False)
    async_add_entities([EnergyIndex(serial_reader, "BBRHPJW",
                       "Index option Tempo - Heures Pleines Jours Blancs")], False)
    async_add_entities([EnergyIndex(serial_reader, "BBRHCJR",
                       "Index option Tempo - Heures Creuses Jours Rouges")], False)
    async_add_entities([EnergyIndex(serial_reader, "BBRHPJR",
                       "Index option Tempo - Heures Pleines Jours Rouges")], False)


class ADCO(SensorEntity):
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
    def native_value(self) -> int | None:
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
                "ADS can not be parsed as EURIDIS, device type is unknown: %s", device_type)
            extra[device_type_key] = device_type
        _LOGGER.debug("parsed ADS: %s", repr(extra))
        self._extra = extra


class OPTARIF(SensorEntity):
    """Option tarifaire choisie sensor"""

    _serial_controller = None

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Linky - Option tarifaire choisie"
    _attr_should_poll = True
    _attr_unique_id = "linky_optarif"
    _attr_icon = "mdi:cash-check"

    def __init__(self, serial_reader):
        _LOGGER.debug("initializing OPTARIF sensor")
        self._serial_controller = serial_reader

    @property
    def native_value(self) -> int | None:
        """Value of the sensor"""
        value, _ = self._serial_controller.get_values("OPTARIF")
        _LOGGER.debug(
            "recovered OPTARIF value from serial controller: %s", value)
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "marking the OPTARIF sensor as unavailable: a full frame has been read but OPTARIF has not been found")
                self._attr_available = False
        return value


class ISOUSC(SensorEntity):
    """Intensité souscrite sensor"""

    _serial_controller = None

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Linky - Intensité souscrite"
    _attr_should_poll = True
    _attr_unique_id = "linky_isousc"

    # Sensor Entity Properties
    #   https://developers.home-assistant.io/docs/core/entity/sensor/#properties
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = ELECTRIC_CURRENT_AMPERE

    def __init__(self, serial_reader):
        _LOGGER.debug("initializing ISOUSC sensor")
        self._serial_controller = serial_reader

    @property
    def native_value(self) -> int | None:
        """Value of the sensor"""
        raw_value, _ = self._serial_controller.get_values("ISOUSC")
        _LOGGER.debug(
            "recovered ISOUSC value from serial controller: %s", repr(raw_value))
        if raw_value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "marking the ISOUSC sensor as unavailable: a full frame has been read but ISOUSC has not been found")
                self._attr_available = False
            return raw_value
        # else
        return int(raw_value)


class EnergyIndex(SensorEntity):
    """common class for energy index counters"""

    _serial_controller = None

    # Generic entity properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_should_poll = True
    _attr_icon = "mdi:counter"

    # Sensor Entity Properties
    #   https://developers.home-assistant.io/docs/core/entity/sensor/#properties
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = ENERGY_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, serial_reader, tag, name):
        _LOGGER.debug("initializing BBRHCJB sensor")
        self._serial_controller = serial_reader
        self._tag = tag.upper()
        # Generic properties
        self._attr_name = "Linky - {}".format(name)
        self._attr_unique_id = "linky_{}".format(tag.lower())

    @property
    def native_value(self) -> int | None:
        """Value of the sensor"""
        raw_value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "recovered %s value from serial controller: %s", self._tag, repr(raw_value))
        if raw_value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._tag, self._tag
                )
                self._attr_available = False
            return raw_value
        # else
        return int(raw_value)
