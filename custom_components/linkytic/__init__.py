"""The linkytic integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    OPTIONS_REALTIME,
    SETUP_SERIAL,
    SETUP_THREEPHASE,
    TICMODE_HISTORIC,
)
from .serial_reader import LinkyTICReader

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up linkytic from a config entry."""
    # Create the serial reader thread and start it
    serial_reader = LinkyTICReader(
        title=entry.title,
        port=entry.data.get(SETUP_SERIAL),
        std_mode=entry.data.get(TICMODE_HISTORIC),
        three_phase=entry.data.get(SETUP_THREEPHASE),
        real_time=entry.options.get(OPTIONS_REALTIME),
    )
    serial_reader.start()
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, serial_reader.signalstop)
    # Add options callback
    entry.async_on_unload(entry.add_update_listener(update_listener))
    entry.async_on_unload(lambda: serial_reader.signalstop("config_entry_unload"))
    # Add the serial reader to HA and initialize sensors
    try:
        hass.data[DOMAIN][entry.entry_id] = serial_reader
    except KeyError:
        hass.data[DOMAIN] = {}
        hass.data[DOMAIN][entry.entry_id] = serial_reader
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Remove the related entry
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    # Retrieved the serial reader for this config entry
    try:
        serial_reader = hass.data[DOMAIN][entry.entry_id]
    except KeyError:
        _LOGGER.error(
            "Can not update options for %s: failed to get the serial reader object",
            entry.title,
        )
        return
    # Update its options
    serial_reader.update_options(entry.options.get(OPTIONS_REALTIME))
