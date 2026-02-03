from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from datetime import time as dt_time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er

from .api import NswFuelApi
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_FAVOURITE_STATION_CODE,
    CONF_PERSON_ENTITIES,
    DOMAIN,
    SERVICE_REFRESH,
)
from .coordinator import ApiCallCounter, FavouriteStationCoordinator, NearbyCoordinator

PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    _migrate_entity_ids(hass, entry)

    api_calls = ApiCallCounter(hass, entry)
    hass.data[DOMAIN][entry.entry_id]["api_calls"] = api_calls

    session = async_get_clientsession(hass)
    api = NswFuelApi(
        session=session,
        base_url="https://api.onegov.nsw.gov.au",
        api_key=entry.data[CONF_API_KEY],
        api_secret=entry.data[CONF_API_SECRET],
        on_api_call=api_calls.async_increment,
    )

    nearby_coordinator = NearbyCoordinator(hass, entry, api)
    favourite_coordinator = FavouriteStationCoordinator(hass, entry, api)

    hass.data[DOMAIN][entry.entry_id]["coordinators"] = {
        "nearby": nearby_coordinator,
        "favourite": favourite_coordinator,
    }
    hass.data[DOMAIN][entry.entry_id]["unsub"] = []

    await nearby_coordinator.async_config_entry_first_refresh()
    if entry.data.get(CONF_FAVOURITE_STATION_CODE, ""):
        await favourite_coordinator.async_config_entry_first_refresh()

    def _reset_api_calls(_now) -> None:
        hass.async_create_task(api_calls.async_reset_if_new_day(force=True))

    reset_unsub = async_track_time_change(hass, _reset_api_calls, hour=0, minute=0, second=0)
    hass.data[DOMAIN][entry.entry_id]["unsub"].append(reset_unsub)

    async def _handle_refresh(call) -> None:
        coordinators = hass.data[DOMAIN][entry.entry_id].get("coordinators", {})
        for coordinator in coordinators.values():
            await coordinator.async_request_refresh()

    if SERVICE_REFRESH not in hass.services.async_services().get(DOMAIN, {}):
        hass.services.async_register(DOMAIN, SERVICE_REFRESH, _handle_refresh)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        for unsub in hass.data[DOMAIN][entry.entry_id].get("unsub", []):
            unsub()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


def _migrate_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)

    desired: dict[str, str] = {
        f"{DOMAIN}_home_nearby": "sensor.home_cheapest_fuel",
        f"{DOMAIN}_favourite_station": "sensor.favourite_station_fuel",
    }
    for idx, entity_id in enumerate(entry.data.get(CONF_PERSON_ENTITIES, "").split(","), start=1):
        entity_id = entity_id.strip()
        if not entity_id:
            continue
        desired[f"{DOMAIN}_{entity_id}_nearby"] = f"sensor.user_{idx}_nearby_cheapest_fuel"

    existing_ids = {e.entity_id for e in entries}
    for e in entries:
        target = desired.get(e.unique_id)
        if not target or e.entity_id == target or target in existing_ids:
            continue
        registry.async_update_entity(e.entity_id, new_entity_id=target)
