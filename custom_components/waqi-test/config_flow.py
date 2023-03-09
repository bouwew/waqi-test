from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

import waqi_client_async as waqi

from .const import (
    CONF_API_TOKEN,
    CONF_KEYWORD,
    CONF_STATION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LOGGER,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    _api_token: str
    _stations: dict[str, str]
    _update_interval: int

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:

            try:
                client = waqi.WAQIClient(
                    user_input[CONF_API_TOKEN], async_get_clientsession(self.hass)
                )
                found = await client.search(user_input[CONF_KEYWORD])
                if not found:
                    errors[CONF_KEYWORD] = "no_matching_stations_found"
            except waqi.OverQuota:
                errors[CONF_API_TOKEN] = "api_over_quota"
            except waqi.InvalidToken:
                errors[CONF_API_TOKEN] = "api_token_invalid"
            except:
                return self.async_abort(reason="unknown")
            else:
                if found:
                    self._stations = {}
                    for station in found:
                        unique_id = station["uid"]
                        self._stations[unique_id] = station["station"]["name"]

                    self._api_token = user_input[CONF_API_TOKEN]
                    self._update_interval = user_input[CONF_UPDATE_INTERVAL]

                    return await self.async_step_pick_station()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_TOKEN): str,
                    vol.Required(CONF_KEYWORD): str,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=DEFAULT_UPDATE_INTERVAL,
                    ): int,
                }
            ),
            errors=errors,
        )

    async def async_step_pick_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the station selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = user_input[CONF_STATION]

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self._stations[unique_id],
                data={},
                options={
                    CONF_API_TOKEN: self._api_token,
                    CONF_UPDATE_INTERVAL: self._update_interval,
                },
            )

        return self.async_show_form(
            step_id="pick_station",
            data_schema=vol.Schema(
                {vol.Required(CONF_STATION): vol.In(self._stations)}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlow:
        """Get the options flow."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the options configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._config_entry.options
        options_schema = vol.Schema(
            {
                vol.Required(CONF_API_TOKEN): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self._config_entry.options.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                ): int,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
