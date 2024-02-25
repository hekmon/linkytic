"""Binary sensors for linkytic integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .serial_reader import LinkyTICReader
from .entity import LinkyTICEntity

_LOGGER = logging.getLogger(__name__)


# config flow setup
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry."""
    _LOGGER.debug("%s: setting up binary sensor plateform", config_entry.title)
    # Retrieve the serial reader object
    try:
        serial_reader = hass.data[DOMAIN][config_entry.entry_id]
    except KeyError:
        _LOGGER.error(
            "%s: can not init binaries sensors: failed to get the serial reader object",
            config_entry.title,
        )
        return
    # Init sensors
    async_add_entities(
        [SerialConnectivity(config_entry.title, config_entry.entry_id, serial_reader)],
        True,
    )


class SerialConnectivity(LinkyTICEntity, BinarySensorEntity):
    """Serial connectivity to the Linky TIC serial interface."""

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Connectivité du lien série"

    # Binary sensor properties
    #   https://developers.home-assistant.io/docs/core/entity/binary-sensor/#properties
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, title: str, uniq_id: str | None, serial_reader: LinkyTICReader) -> None:
        """Initialize the SerialConnectivity binary sensor."""
        _LOGGER.debug("%s: initializing Serial Connectivity binary sensor", title)
        super().__init__(serial_reader)
        self._title = title
        self._attr_unique_id = f"{DOMAIN}_{uniq_id}_serial_connectivity"

    @property
    def is_on(self) -> bool:
        """Value of the sensor."""
        return self._serial_controller.is_connected
