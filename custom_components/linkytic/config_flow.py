"""Config flow for linkytic integration."""

from __future__ import annotations

# import dataclasses
import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import usb
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)

# from homeassistant.components.usb import UsbServiceInfo
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    LINKY_IO_ERRORS,
    OPTIONS_REALTIME,
    SETUP_PRODUCER,
    SETUP_PRODUCER_DEFAULT,
    SETUP_SERIAL,
    SETUP_SERIAL_DEFAULT,
    SETUP_THREEPHASE,
    SETUP_THREEPHASE_DEFAULT,
    SETUP_TICMODE,
    TICMODE_HISTORIC,
    TICMODE_HISTORIC_LABEL,
    TICMODE_STANDARD,
    TICMODE_STANDARD_LABEL,
)
from .serial_reader import LinkyTICReader

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(SETUP_SERIAL, default=SETUP_SERIAL_DEFAULT): str,
        vol.Required(SETUP_TICMODE, default=TICMODE_HISTORIC): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(
                        value=TICMODE_HISTORIC, label=TICMODE_HISTORIC_LABEL
                    ),
                    selector.SelectOptionDict(
                        value=TICMODE_STANDARD, label=TICMODE_STANDARD_LABEL
                    ),
                ]
            ),
        ),
        vol.Required(SETUP_PRODUCER, default=SETUP_PRODUCER_DEFAULT): bool,
        vol.Required(SETUP_THREEPHASE, default=SETUP_THREEPHASE_DEFAULT): bool,
    }
)


class LinkyTICConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for linkytic."""

    VERSION = 2
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # No input
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        # Search for serial/by-id, which SHOULD be a persistent name to serial interface.
        _port = await self.hass.async_add_executor_job(
            usb.get_serial_by_id, user_input[SETUP_SERIAL]
        )

        user_input[SETUP_SERIAL] = _port

        errors = {}

        try:
            serial_reader = LinkyTICReader(
                title="Probe",
                port=_port,
                std_mode=user_input.get(SETUP_TICMODE) == TICMODE_STANDARD,
                producer_mode=user_input[SETUP_PRODUCER],
                three_phase=user_input[SETUP_THREEPHASE],
                real_time=False,
            )
            serial_reader.start()

            async def read_serial_number(serial: LinkyTICReader) -> str:
                while serial.serial_number is None:
                    await asyncio.sleep(1)
                    # Check for any serial error that occurred in the serial thread context
                    if serial.setup_error:
                        raise serial.setup_error
                return serial.serial_number

            s_n = await asyncio.wait_for(read_serial_number(serial_reader), timeout=5)

        # Error when opening serial port.
        except LINKY_IO_ERRORS as cannot_connect:
            _LOGGER.error("Could not connect to %s (%s)", _port, cannot_connect)
            errors["base"] = "cannot_connect"

        # Timeout waiting for S/N to be read.
        except TimeoutError:
            _LOGGER.error("Could not read serial number at %s", _port)
            errors["base"] = "cannot_read"

        else:
            _LOGGER.info("Found a device with serial number: %s", s_n)

            await self.async_set_unique_id(s_n)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[SETUP_SERIAL], data=user_input
            )

        finally:
            serial_reader.signalstop("end_probe")

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    # async def async_step_usb(self, discovery_info: UsbServiceInfo) -> FlowResult:
    #     """Handle a flow initialized by USB discovery."""
    #     return await self.async_step_discovery(dataclasses.asdict(discovery_info))

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    """Handles the options of a Linky TIC connection."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        OPTIONS_REALTIME,
                        default=self.config_entry.options.get(OPTIONS_REALTIME),
                    ): bool
                }
            ),
        )
