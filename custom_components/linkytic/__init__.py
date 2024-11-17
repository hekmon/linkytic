"""The linkytic integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components import usb
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    LINKY_IO_ERRORS,
    OPTIONS_REALTIME,
    SETUP_PRODUCER,
    SETUP_SERIAL,
    SETUP_THREEPHASE,
    SETUP_TICMODE,
    TICMODE_STANDARD,
)
from .serial_reader import LinkyTICReader

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up linkytic from a config entry."""
    # Create the serial reader thread and start it
    port = entry.data.get(SETUP_SERIAL)
    try:
        serial_reader = LinkyTICReader(
            title=entry.title,
            port=port,
            std_mode=entry.data.get(SETUP_TICMODE) == TICMODE_STANDARD,
            producer_mode=entry.data.get(SETUP_PRODUCER),
            three_phase=entry.data.get(SETUP_THREEPHASE),
            real_time=entry.options.get(OPTIONS_REALTIME),
        )
        serial_reader.start()

        async def read_serial_number(serial: LinkyTICReader):
            while serial.serial_number is None:
                await asyncio.sleep(1)
            return serial.serial_number

        s_n = await asyncio.wait_for(read_serial_number(serial_reader), timeout=5)
        # TODO: check if S/N is the one saved in config entry, if not this is a different meter!

    # Error when opening serial port.
    except LINKY_IO_ERRORS as e:
        raise ConfigEntryNotReady(f"Couldn't open serial port {port}: {e}") from e

    # Timeout waiting for S/N to be read.
    except TimeoutError as e:
        serial_reader.signalstop("linkytic_timeout")
        raise ConfigEntryNotReady(
            "Connected to serial port but coulnd't read serial number before timeout: check if TIC is connected and active."
        ) from e

    _LOGGER.info(f"Device connected with serial number: {s_n}")

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


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.info(
        "Migrating from version %d.%d", config_entry.version, config_entry.minor_version
    )

    if config_entry.version == 1:
        new = {**config_entry.data}

        if config_entry.minor_version < 2:
            # Migrate to serial by-id.
            serial_by_id = await hass.async_add_executor_job(
                usb.get_serial_by_id, new[SETUP_SERIAL]
            )
            if serial_by_id == new[SETUP_SERIAL]:
                _LOGGER.warning(
                    f"Couldn't find a persistent /dev/serial/by-id alias for {serial_by_id}. "
                    "Problems might occur at startup if device names are not persistent."
                )
            else:
                new[SETUP_SERIAL] = serial_by_id

        # config_entry.minor_version = 2
        hass.config_entries.async_update_entry(
            config_entry, data=new, minor_version=2, version=1
        )  # type: ignore

    _LOGGER.info(
        "Migration to version %d.%d successful",
        config_entry.version,
        config_entry.minor_version,
    )
    return True
