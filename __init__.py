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
from serial import SerialException
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
    # Debug conf
    conf = config.get(DOMAIN)
    _LOGGER.debug("Serial port: %s", conf[CONF_SERIAL_PORT])
    _LOGGER.debug("Standard mode: %s", conf[CONF_STANDARD_MODE])
    # create the serial controller and schedule it
    sr = AsyncSerialReader(
        port=conf[CONF_SERIAL_PORT],
        baudrate=MODE_STANDARD_BAUD_RATE if conf[CONF_STANDARD_MODE] else MODE_HISTORIC_BAUD_RATE,
        bytesize=BYTESIZE,
        parity=PARITY,
        stopbits=STOPBITS,
        fields_sep=MODE_STANDARD_FIELD_SEPARATOR if conf[
            CONF_STANDARD_MODE] else MODE_HISTORIC_FIELD_SEPARATOR
    )
    # hass.async_create_task(sr.read_serial())
    # Create the sensors
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


class AsyncSerialReader():
    def __init__(self, port, baudrate, bytesize, parity, stopbits, fields_sep):
        # Build
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._fields_sep = fields_sep
        # Run
        self._reader = None
        self._values = {}

    async def read_serial(self, **kwargs):
        while True:
            # Try to open a connection
            if self._reader is None:
                await self.open_serial(**kwargs)
                continue
            # Now that we have a connection, read its output
            try:
                line = await self._reader.readline()
            except SerialException as exc:
                _LOGGER.exception(
                    "Error while reading serial device %s: %s", self._port, exc
                )
                await asyncio.sleep(5)
            else:
                self.parse_line(line)

    async def open_serial(self, **kwargs):
        try:
            self._reader, _ = await serial_asyncio.open_serial_connection(
                url=self._port,
                baudrate=self._baudrate,
                bytesize=self._bytesize,
                parity=self._parity,
                stopbits=self._stopbits,
                **kwargs,
            )
        except SerialException as exc:
            _LOGGER.exception(
                "Unable to connect to the serial device %s: %s. Will retry in 5s",
                self._port,
                exc,
            )
            self._reader = None
            await asyncio.sleep(5)

    def parse_line(self, line):
        _LOGGER.debug("line to parse: %s", repr(line))
