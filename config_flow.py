"""Config flow for Keemple integration."""
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import KeempleHome
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_COUNTRY_CODE,
    DEFAULT_COUNTRY_CODE,
    ERROR_AUTH,
    ERROR_CANNOT_CONNECT,
    ERROR_UNKNOWN,
)

class KeempleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Keemple."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                api = KeempleHome(
                    hass=self.hass,  # Pass hass instance
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    country_code=user_input.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE),
                )

                if await api.async_login():
                    return self.async_create_entry(
                        title=user_input[CONF_USERNAME],
                        data=user_input,
                    )
                else:
                    errors["base"] = ERROR_AUTH
                    
            except ConnectionError:
                errors["base"] = ERROR_CANNOT_CONNECT
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = ERROR_UNKNOWN

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_COUNTRY_CODE, default=DEFAULT_COUNTRY_CODE): str,
            }),
            errors=errors,
        )
