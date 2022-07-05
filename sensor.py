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
    async_add_entities([BASE(serial_reader)], False)


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
        if value is None:
            return None
        # else
        _LOGGER.debug(
            "recovered ADCO value from serial controller: %s", value)
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
            'code du constructeur': ads[0:2],
            'année de construction': "20{}".format(ads[2:4]),
            "matricule de l'appareil": ads[6:],
        }
        device_type_key = "type de l'appareil"
        device_type = ads[4:6]
        if device_type == "61":
            extra[device_type_key] = "61 : Compteur monophasé 60 A généralisation Linky G3 - arrivée puissance haute"
        elif device_type == "62":
            extra[device_type_key] = "62 : Compteur monophasé 90 A généralisation Linky G1 - arrivée puissance basse"
        elif device_type == "63":
            extra[device_type_key] = "63 : Compteur triphasé 60 A généralisation Linky G1 - arrivée puissance basse"
        elif device_type == "64":
            extra[device_type_key] = "64 : Compteur monophasé 60 A généralisation Linky G3 - arrivée puissance basse"
        elif device_type == "70":
            extra[device_type_key] = "70 : Compteur monophasé Linky 60 A mise au point G3"
        elif device_type == "71":
            extra[device_type_key] = "71 : Compteur triphasé Linky 60 A mise au point G3"
        elif device_type == "75":
            extra[device_type_key] = "75 : Compteur monophasé 90 A généralisation Linky G3 - arrivée puissance basse"
        elif device_type == "76":
            extra[device_type_key] = "76 : Compteur triphasé 60 A généralisation Linky G3 - arrivée puissance basse"
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
            return None
        # else
        return int(raw_value)


class BASE(SensorEntity):
    """Index option Base sensor"""

    _serial_controller = None

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_name = "Linky - Index option Base"
    _attr_should_poll = True
    _attr_unique_id = "linky_base"
    _attr_icon = "mdi:counter"

    # Sensor Entity Properties
    #   https://developers.home-assistant.io/docs/core/entity/sensor/#properties
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = ENERGY_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, serial_reader):
        _LOGGER.debug("initializing BASE sensor")
        self._serial_controller = serial_reader

    @property
    def native_value(self) -> int | None:
        """Value of the sensor"""
        raw_value, _ = self._serial_controller.get_values("BASE")
        _LOGGER.debug(
            "recovered BASE value from serial controller: %s", repr(raw_value))
        if raw_value is None:
            return None
        # else
        return int(raw_value)
