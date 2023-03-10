from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
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

FLOW_FEED = "Enter the station ID"
FLOW_SEARCH = "Find stations from an area/city name"
FLOW_TYPE = "flow_type"

CONFIG_SCHEMA = vol.Schema(
    {vol.Required(FLOW_TYPE, default=FLOW_SEARCH): vol.In([FLOW_SEARCH, FLOW_FEED])}
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
        """Handle the initial step for selecting the configuration method."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[FLOW_TYPE] == FLOW_SEARCH:
                return await self.async_step_user_search()

            if user_input[FLOW_TYPE] == FLOW_FEED:
                return await self.async_step_user_feed()

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
        )

    async def async_step_user_search(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the search step."""
        errors: dict[str, str] = {}

        if not user_input:
            return self.async_show_form(
                step_id="user_search",
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

        try:
            client = waqi.WAQIClient(
                user_input[CONF_API_TOKEN], async_get_clientsession(self.hass)
            )
            found = await client.search(user_input[CONF_KEYWORD])
            LOGGER.debug("Found: %s", found)
            if not found:
                errors[CONF_KEYWORD] = "no_matching_stations_found"
        except waqi.OverQuota:
            errors[CONF_API_TOKEN] = "api_over_quota"
        except waqi.InvalidToken:
            errors[CONF_API_TOKEN] = "api_token_invalid"
        except Exception:
            errors[CONF_BASE] = "unknown"

        if errors:
            LOGGER.debug("Errors: %s", errors)
            return self.async_show_form(
                step_id="user_search",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_API_TOKEN,
                            default=user_input[CONF_API_TOKEN]
                        ): str,
                        vol.Required(
                            CONF_KEYWORD),
                            default=user_input[CONF_KEYWORD]
                        ): str,
                        vol.Optional(
                            CONF_UPDATE_INTERVAL,
                            default=user_input[CONF_UPDATE_INTERVAL]),
                        ): int,
                    }
                ),
                errors=errors,
            )

        self._stations = {}
        for station in found:
            LOGGER.debug("Station found: %s", station)
            station_id = station["uid"]
            self._stations[station_id] = station["station"]["name"]

        self._api_token = user_input[CONF_API_TOKEN]
        self._update_interval = user_input[CONF_UPDATE_INTERVAL]

        return await self.async_step_pick_station()

    async def async_step_pick_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the station selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = user_input[CONF_STATION]

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            LOGGER.debug("Station data: %s", self._stations[unique_id])
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

    async def async_step_user_feed(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the feed step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                client = waqi.WAQIClient(
                    user_input[CONF_API_TOKEN], async_get_clientsession(self.hass)
                )
                station = await client.feed(user_input[CONF_STATION])
                LOGGER.debug("Station: %s", station)
                if not station:
                    errors[CONF_STATION] = "no_station_feed_found"
            except waqi.OverQuota:
                errors[CONF_API_TOKEN] = "api_over_quota"
            except waqi.InvalidToken:
                errors[CONF_API_TOKEN] = "api_token_invalid"
            except:
                return self.async_abort(reason="unknown")
            else:
                LOGGER.debug("Station data: %s", station)
                unique_id = user_input[CONF_STATION]
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=station["uid"],
                data={},
                options={
                    CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                    CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
                },
            )

        return self.async_show_form(
            step_id="user_feed",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_TOKEN): str,
                    vol.Required(CONF_STATION): str,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=DEFAULT_UPDATE_INTERVAL,
                    ): int,
                },
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
