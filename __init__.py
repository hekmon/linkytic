"""The Linky (LiXee-TIC-DIN) integration."""
from __future__ import annotations

# from homeassistant.config_entries import ConfigEntry
# from homeassistant.const import Platform
# from homeassistant.core import HomeAssistant

# from .const import DOMAIN

# # TODO List the platforms that you want to support.
# # For your initial PR, limit it to 1 platform.
# PLATFORMS: list[Platform] = [Platform.SENSOR]


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Set up Linky (LiXee-TIC-DIN) from a config entry."""
#     # TODO Store an API object for your platforms to access
#     # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

#     hass.config_entries.async_setup_platforms(entry, PLATFORMS)

#     return True


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Unload a config entry."""
#     if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
#         hass.data[DOMAIN].pop(entry.entry_id)

#     return unload_ok


import asyncio
import logging

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType

import serial_asyncio
import voluptuous as vol

from .const import (
    DOMAIN,

    BYTESIZE,
    PARITY,
    STOPBITS,
    MODE_STANDARD_BAUD_RATE,
    MODE_STANDARD_FIELD_SEPARATOR,
    MODE_HISTORIC_BAUD_RATE,
    MODE_HISTORIC_FIELD_SEPARATOR,
    LINE_END,
    FRAME_END,

    CONF_SERIAL_PORT,
    CONF_STANDARD_MODE,
    DEFAULT_SERIAL_PORT,
    DEFAULT_STANDARD_MODE
)


_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_SERIAL_PORT, default=DEFAULT_SERIAL_PORT): cv.string,
                vol.Required(CONF_STANDARD_MODE, default=DEFAULT_STANDARD_MODE): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Linky LiXee-TIC-DIN component."""

    _LOGGER.debug("init lixee component", config)

    conf = config.get(DOMAIN)
    _LOGGER.debug("Serial port: %s", conf[CONF_SERIAL_PORT])
    _LOGGER.debug("Standard mode: %s", conf[CONF_STANDARD_MODE])

    # hass.async_create_task(
    #     serial_asyncio.create_serial_connection(
    #         asyncio.get_event_loop(), AsyncSerialReader,
    #         conf[CONF_SERIAL_PORT],
    #         baudrate=MODE_STANDARD_BAUD_RATE if conf[CONF_STANDARD_MODE] else MODE_HISTORIC_BAUD_RATE,
    #         bytesize=BYTESIZE,
    #         parity=PARITY,
    #         stopbits=STOPBITS,
    #         timeout=0.5
    #     )
    # )

    hass.async_create_task(
        async_load_platform(
            hass,
            SENSOR_DOMAIN,
            DOMAIN,
            {},
            config,
        )
    )
    return True


class AsyncSerialReader(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        _LOGGER.info("lixee serial connection open")
        _LOGGER.debug("lixee transport received: %s", repr(transport))

    def data_received(self, data):
        _LOGGER.debug("lixee data received: %s", repr(data))

    def eof_received(self):
        _LOGGER.warning("lixee serial connection received EOF")
        return False

    def connection_lost(self, exc):
        _LOGGER.error("lixee serial connection lost")
        # self.transport.loop.stop()
