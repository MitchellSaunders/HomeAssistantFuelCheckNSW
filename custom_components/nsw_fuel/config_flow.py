from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_HOME_LAT,
    CONF_HOME_LON,
    CONF_HOME_NAMEDLOCATION,
    CONF_RADIUS_KM,
    CONF_BRANDS,
    CONF_PREFERRED_FUELS,
    CONF_PERSON_ENTITIES,
    CONF_FAVOURITE_STATION_CODE,
    DEFAULT_RADIUS_KM,
    DEFAULT_BRANDS,
    DEFAULT_PREFERRED_FUELS,
    DOMAIN,
)


class NswFuelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._data = dict(user_input)
            return await self.async_step_location()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="NSW Fuel"): selector.TextSelector(
                    selector.TextSelectorConfig()
                ),
                vol.Required(CONF_API_KEY): selector.TextSelector(
                    selector.TextSelectorConfig()
                ),
                vol.Required(CONF_API_SECRET): selector.TextSelector(
                    selector.TextSelectorConfig(type="password")
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_location(self, user_input=None):
        if user_input is not None:
            data = dict(self._data)
            preferred = user_input.get(CONF_PREFERRED_FUELS)
            if isinstance(preferred, list):
                user_input[CONF_PREFERRED_FUELS] = "|".join(preferred)
            person_entities = user_input.get(CONF_PERSON_ENTITIES)
            if isinstance(person_entities, list):
                user_input[CONF_PERSON_ENTITIES] = ",".join(person_entities)
            data.update(user_input)
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOME_NAMEDLOCATION): selector.TextSelector(
                    selector.TextSelectorConfig()
                ),
                vol.Required(CONF_HOME_LAT): selector.TextSelector(
                    selector.TextSelectorConfig()
                ),
                vol.Required(CONF_HOME_LON): selector.TextSelector(
                    selector.TextSelectorConfig()
                ),
                vol.Optional(
                    CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=50, step=1, mode="box")
                ),
                vol.Optional(CONF_BRANDS, default=DEFAULT_BRANDS): selector.TextSelector(
                    selector.TextSelectorConfig()
                ),
                vol.Optional(
                    CONF_PREFERRED_FUELS,
                    default=DEFAULT_PREFERRED_FUELS.split("|"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["E10", "U91", "P95", "P98"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_PERSON_ENTITIES, default=[]): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["person", "device_tracker", "sensor"],
                        multiple=True,
                    )
                ),
                vol.Optional(CONF_FAVOURITE_STATION_CODE, default=""): selector.TextSelector(
                    selector.TextSelectorConfig()
                ),
            }
        )
        return self.async_show_form(step_id="location", data_schema=schema)
