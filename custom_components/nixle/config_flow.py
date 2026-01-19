"""Config flow for Nixle integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

DOMAIN = "nixle"

_LOGGER = logging.getLogger(__name__)


class NixleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nixle."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Nixle Alerts",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                {
                    "agency_url": selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        ),
                    ),
                },
                {"agency_url": "https://local.nixle.com/"},
            ),
        )
