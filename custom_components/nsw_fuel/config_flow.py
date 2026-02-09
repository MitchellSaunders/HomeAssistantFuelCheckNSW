from __future__ import annotations

from typing import Any

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


def _pipe_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value or "").split("|") if v.strip()]


def _comma_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value or "").split(",") if v.strip()]


def _normalise_form_data(user_input: dict[str, Any]) -> dict[str, Any]:
    data = dict(user_input)
    preferred = data.get(CONF_PREFERRED_FUELS)
    if isinstance(preferred, list):
        data[CONF_PREFERRED_FUELS] = "|".join(preferred)
    person_entities = data.get(CONF_PERSON_ENTITIES)
    if isinstance(person_entities, list):
        data[CONF_PERSON_ENTITIES] = ",".join(person_entities)
    return data


class NswFuelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def _build_location_schema(defaults: dict[str, Any]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_HOME_NAMEDLOCATION,
                    default=str(defaults.get(CONF_HOME_NAMEDLOCATION, "")),
                ): selector.TextSelector(selector.TextSelectorConfig()),
                vol.Required(
                    CONF_HOME_LAT,
                    default=str(defaults.get(CONF_HOME_LAT, "")),
                ): selector.TextSelector(selector.TextSelectorConfig()),
                vol.Required(
                    CONF_HOME_LON,
                    default=str(defaults.get(CONF_HOME_LON, "")),
                ): selector.TextSelector(selector.TextSelectorConfig()),
                vol.Optional(
                    CONF_RADIUS_KM,
                    default=defaults.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=50, step=1, mode="box")
                ),
                vol.Optional(
                    CONF_BRANDS,
                    default=str(defaults.get(CONF_BRANDS, DEFAULT_BRANDS)),
                ): selector.TextSelector(selector.TextSelectorConfig()),
                vol.Optional(
                    CONF_PREFERRED_FUELS,
                    default=_pipe_list(defaults.get(CONF_PREFERRED_FUELS, DEFAULT_PREFERRED_FUELS)),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["E10", "U91", "P95", "P98"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_PERSON_ENTITIES,
                    default=_comma_list(defaults.get(CONF_PERSON_ENTITIES, "")),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["person", "device_tracker", "sensor"],
                        multiple=True,
                    )
                ),
                vol.Optional(
                    CONF_FAVOURITE_STATION_CODE,
                    default=str(defaults.get(CONF_FAVOURITE_STATION_CODE, "")),
                ): selector.TextSelector(selector.TextSelectorConfig()),
            }
        )

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
            data.update(_normalise_form_data(user_input))
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        schema = self._build_location_schema(
            {
                CONF_HOME_NAMEDLOCATION: "",
                CONF_HOME_LAT: "",
                CONF_HOME_LON: "",
                CONF_RADIUS_KM: DEFAULT_RADIUS_KM,
                CONF_BRANDS: DEFAULT_BRANDS,
                CONF_PREFERRED_FUELS: DEFAULT_PREFERRED_FUELS,
                CONF_PERSON_ENTITIES: "",
                CONF_FAVOURITE_STATION_CODE: "",
            }
        )
        return self.async_show_form(step_id="location", data_schema=schema)

    async def async_step_reconfigure(self, user_input=None):
        entry_id = self.context.get("entry_id")
        if not entry_id:
            return self.async_abort(reason="reconfigure_failed")

        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            return self.async_abort(reason="reconfigure_failed")

        if user_input is not None:
            updated_data = dict(entry.data)
            updated_data.update(_normalise_form_data(user_input))
            self.hass.config_entries.async_update_entry(entry, data=updated_data)
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reconfigure_successful")

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_KEY,
                    default=str(entry.data.get(CONF_API_KEY, "")),
                ): selector.TextSelector(selector.TextSelectorConfig()),
                vol.Required(
                    CONF_API_SECRET,
                    default=str(entry.data.get(CONF_API_SECRET, "")),
                ): selector.TextSelector(selector.TextSelectorConfig(type="password")),
                **self._build_location_schema(entry.data).schema,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)
