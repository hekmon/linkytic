"""Serial connection binary sensor for Linky (LiXee-TIC-DIN) integration"""
from __future__ import annotations
import asyncio
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    """Set up the Linky (LiXee-TIC-DIN) binary sensor platform."""
    _LOGGER.debug(
        "setting up binary sensor plateform")
    # Init sensors
    async_add_entities(
        [SerialConnectivity(discovery_info[SERIAL_READER])], True)


class SerialConnectivity(BinarySensorEntity):
    """Serial connectivity to the Linky TIC serial interface"""

    _serial_controller = None

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Linky - Connectivité du lien serie"
    _attr_should_poll = True
    _attr_unique_id = "linky_serial_connectivity"

    # Binary sensor properties
    #   https://developers.home-assistant.io/docs/core/entity/binary-sensor/#properties
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, serial_reader):
        _LOGGER.debug("initializing SerialConnectivity binary sensor")
        self._serial_controller = serial_reader

    @property
    def is_on(self) -> bool:
        """Value of the sensor"""
        return self._serial_controller.is_connected()
