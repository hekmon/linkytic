"""Config flow for linkytic integration."""
from __future__ import annotations

# import dataclasses
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries

# from homeassistant.components.usb import UsbServiceInfo
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    OPTIONS_REALTIME,
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
from .serial_reader import CannotConnect, CannotRead, linky_tic_tester

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
        vol.Required(SETUP_THREEPHASE, default=SETUP_THREEPHASE_DEFAULT): bool,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for linkytic."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # No input
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )
        # Validate input
        await self.async_set_unique_id(DOMAIN + "_" + user_input[SETUP_SERIAL])
        self._abort_if_unique_id_configured()
        errors = {}
        title = user_input[SETUP_SERIAL]
        try:
            linky_tic_tester(
                device=user_input[SETUP_SERIAL],
                std_mode=user_input[SETUP_TICMODE] == TICMODE_STANDARD,
            )
        except CannotConnect as cannot_connect:
            _LOGGER.error("%s: can not connect: %s", title, cannot_connect)
            errors["base"] = "cannot_connect"
        except CannotRead as cannot_read:
            _LOGGER.error(
                "%s: can not read a line after connection: %s", title, cannot_read
            )
            errors["base"] = "cannot_read"
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception: %s", exc)
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    # async def async_step_usb(self, discovery_info: UsbServiceInfo) -> FlowResult:
    #     """Handle a flow initialized by USB discovery."""
    #     return await self.async_step_discovery(dataclasses.asdict(discovery_info))

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles the options of a Linky TIC connection."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
