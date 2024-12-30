"""Entity for linkytic integration."""

from __future__ import annotations

from typing import cast

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import (
    DID_CONSTRUCTOR,
    DID_DEFAULT_MANUFACTURER,
    DID_DEFAULT_MODEL,
    DID_DEFAULT_NAME,
    DID_REGNUMBER,
    DID_TYPE,
    DOMAIN,
)
from .serial_reader import LinkyTICReader


class LinkyTICEntity(Entity):
    """Base class for all linkytic entities."""

    _serial_controller: LinkyTICReader
    _attr_should_poll = True
    _attr_has_entity_name = True

    def __init__(self, reader: LinkyTICReader):
        """Init Linkytic entity."""
        self._serial_controller = reader

    @property
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        did = self._serial_controller.device_identification

        return DeviceInfo(
            identifiers={(DOMAIN, cast(str, did.get(DID_REGNUMBER)))},
            manufacturer=did.get(DID_CONSTRUCTOR, DID_DEFAULT_MANUFACTURER),
            model=did.get(DID_TYPE, DID_DEFAULT_MODEL),
            name=DID_DEFAULT_NAME,
            serial_number=self._serial_controller.serial_number,
            sw_version="TIC "
            + ("Standard" if self._serial_controller._std_mode else "Historique"),
        )
