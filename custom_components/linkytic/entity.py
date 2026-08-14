"""Entity for linkytic integration."""

from __future__ import annotations

import logging
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
from .serial_reader import LinkyMeter

_LOGGER = logging.getLogger(__name__)


class LinkyTICEntity(Entity):
    """Base class for all linkytic entities."""

    _meter: LinkyMeter
    _attr_should_poll = True
    _attr_has_entity_name = True
    _tag: str

    def __init__(self, reader: LinkyMeter):
        """Init Linkytic entity."""
        self._meter = reader

    @property
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        did = self._meter.device_identification

        return DeviceInfo(
            identifiers={(DOMAIN, cast(str, did.get(DID_REGNUMBER)))},
            manufacturer=did.get(DID_CONSTRUCTOR, DID_DEFAULT_MANUFACTURER),
            model=did.get(DID_TYPE, DID_DEFAULT_MODEL),
            name=DID_DEFAULT_NAME,
            serial_number=self._meter.serial_number,
            sw_version="TIC "
            + ("Standard" if self._meter.is_tic_mode_standard else "Historique"),
        )

    def _update(self, tag: str = "") -> tuple[str | None, str | None]:
        """Get value and/or timestamp from cached data. Responsible for updating sensor availability."""
        value, timestamp = self._meter.get_value(tag or self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: (%s, %s)",
            self._meter.name,
            tag,
            value,
            timestamp,
        )
        self._attr_available = bool(value or timestamp)
        return value, timestamp
