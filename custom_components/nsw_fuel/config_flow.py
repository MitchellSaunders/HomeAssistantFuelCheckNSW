from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_AUTHORIZATION,
    CONF_HOME_LAT,
    CONF_HOME_LON,
    CONF_HOME_NAMEDLOCATION,
    CONF_RADIUS_KM,
    CONF_BRANDS,
    CONF_PREFERRED_FUELS,
    CONF_PERSON_ENTITIES,
    CONF_COSTCO_STATION_CODE,
    CONF_NEARBY_UPDATE_MINUTES,
    CONF_COSTCO_UPDATE_MINUTES,
    DEFAULT_RADIUS_KM,
    DEFAULT_BRANDS,
    DEFAULT_PREFERRED_FUELS,
    DEFAULT_NEARBY_UPDATE_MINUTES,
    DEFAULT_COSTCO_UPDATE_MINUTES,
    DOMAIN,
)


class NswFuelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="NSW Fuel"): str,
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_API_SECRET): str,
                vol.Optional(CONF_AUTHORIZATION): str,
                vol.Required(CONF_HOME_NAMEDLOCATION): str,
                vol.Required(CONF_HOME_LAT): str,
                vol.Required(CONF_HOME_LON): str,
                vol.Optional(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): str,
                vol.Optional(CONF_BRANDS, default=DEFAULT_BRANDS): str,
                vol.Optional(CONF_PREFERRED_FUELS, default=DEFAULT_PREFERRED_FUELS): str,
                vol.Optional(CONF_PERSON_ENTITIES, default=""): str,
                vol.Optional(CONF_COSTCO_STATION_CODE, default=""): str,
                vol.Optional(
                    CONF_NEARBY_UPDATE_MINUTES, default=DEFAULT_NEARBY_UPDATE_MINUTES
                ): int,
                vol.Optional(
                    CONF_COSTCO_UPDATE_MINUTES, default=DEFAULT_COSTCO_UPDATE_MINUTES
                ): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
