"""Binary sensors for linkytic integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DID_CONSTRUCTOR,
    DID_DEFAULT_MANUFACTURER,
    DID_DEFAULT_MODEL,
    DID_DEFAULT_NAME,
    DID_TYPE,
    DOMAIN,
)
from .serial_reader import LinkyTICReader

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
    # Wait a bit for the controller to feed on serial frames (home assistant warns after 10s)
    _LOGGER.debug(
        "%s: waiting at most 9s before setting up binary sensor plateform in order for the async serial reader to have time to parse a full frame",
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
    async_add_entities(
        [SerialConnectivity(config_entry.title, config_entry.entry_id, serial_reader)],
        True,
    )


class SerialConnectivity(BinarySensorEntity):
    """Serial connectivity to the Linky TIC serial interface."""

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Connectivité du lien série"
    _attr_should_poll = True

    # Binary sensor properties
    #   https://developers.home-assistant.io/docs/core/entity/binary-sensor/#properties
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self, title: str, uniq_id: str | None, serial_reader: LinkyTICReader
    ) -> None:
        """Initialize the SerialConnectivity binary sensor."""
        _LOGGER.debug("%s: initializing Serial Connectivity binary sensor", title)
        self._title = title
        self._attr_unique_id = f"{DOMAIN}_{uniq_id}_serial_connectivity"
        self._serial_controller = serial_reader
        self._device_uniq_id = uniq_id if uniq_id is not None else "yaml_legacy"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            default_manufacturer=DID_DEFAULT_MANUFACTURER,
            default_model=DID_DEFAULT_MODEL,
            default_name=DID_DEFAULT_NAME,
            identifiers={(DOMAIN, self._device_uniq_id)},
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
        )

    @property
    def is_on(self) -> bool:
        """Value of the sensor."""
        return self._serial_controller.is_connected()
