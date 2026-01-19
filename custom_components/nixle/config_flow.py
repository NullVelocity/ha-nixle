"""Config flow for Nixle integration."""
import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import CONF_AGENCY_URL, CONF_ALERT_TYPES, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Simple alert type options for the form
ALERT_TYPE_OPTIONS = {
    "alert": "Alert",
    "advisory": "Advisory", 
    "community": "Community",
}


class NixleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nixle."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            agency_url = user_input[CONF_AGENCY_URL].strip()
            
            # Validate URL format
            if not re.match(r"https://local\.nixle\.com/[\w\-]+/?", agency_url):
                errors[CONF_AGENCY_URL] = "invalid_url"
            else:
                # Extract agency name from URL for unique ID
                agency_id = agency_url.split("/")[-2] if agency_url.endswith("/") else agency_url.split("/")[-1]
                
                await self.async_set_unique_id(agency_id)
                self._abort_if_unique_id_configured()
                
                # Get selected alert types or default to all
                selected_types = user_input.get(CONF_ALERT_TYPES, list(ALERT_TYPE_OPTIONS.keys()))
                
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, f"Nixle - {agency_id}"),
                    data={
                        CONF_AGENCY_URL: agency_url,
                        CONF_ALERT_TYPES: selected_types,
                    },
                )

        # Create the form schema
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_NAME, default="Nixle Alerts"): cv.string,
                vol.Required(CONF_AGENCY_URL, default="https://local.nixle.com/"): cv.string,
                vol.Optional(
                    CONF_ALERT_TYPES, 
                    default=list(ALERT_TYPE_OPTIONS.keys())
                ): cv.multi_select(ALERT_TYPE_OPTIONS),
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NixleOptionsFlowHandler(config_entry)


class NixleOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Nixle options."""

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
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_ALERT_TYPES,
                    default=self.config_entry.data.get(CONF_ALERT_TYPES, list(ALERT_TYPE_OPTIONS.keys())),
                ): cv.multi_select(ALERT_TYPE_OPTIONS),
            }),
        )
