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
    URL_HELP,
    URL_ISSUES,
)
from .serial_reader import CannotConnect, CannotRead, linky_tic_tester

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(SETUP_SERIAL, default=SETUP_SERIAL_DEFAULT): str,  # type: ignore
        vol.Required(SETUP_TICMODE, default=TICMODE_HISTORIC): selector.SelectSelector(  # type: ignore
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
        vol.Required(SETUP_PRODUCER, default=SETUP_PRODUCER_DEFAULT): bool,  # type: ignore
        vol.Required(SETUP_THREEPHASE, default=SETUP_THREEPHASE_DEFAULT): bool,  # type: ignore
    }
)


class LinkyTICConfigFlow(ConfigFlow, domain=DOMAIN):  # type:ignore
    """Handle a config flow for linkytic."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""

        errors = {}
        if user_input is not None:
            # Validate input
            await self.async_set_unique_id(DOMAIN + "_" + user_input[SETUP_SERIAL])
            self._abort_if_unique_id_configured()

            # Search for serial/by-id, which SHOULD be a persistent name to serial interface.
            _port = await self.hass.async_add_executor_job(
                usb.get_serial_by_id, user_input[SETUP_SERIAL]
            )

            title = user_input[SETUP_SERIAL]
            try:
                # Encapsulate the tester function, pyserial rfc2217 implementation have blocking calls.
                await asyncio.to_thread(
                    linky_tic_tester,
                    device=_port,
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
                user_input[SETUP_SERIAL] = _port
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"url_help": URL_HELP},
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
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """Handles the options of a Linky TIC connection."""

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
                        default=self.config_entry.options.get(OPTIONS_REALTIME),  # type: ignore
                    ): bool
                }
            ),
        )
