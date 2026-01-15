from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er

from .api import NswFuelApi
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_FAVORITE_STATION_CODE,
    CONF_PERSON_ENTITIES,
    DOMAIN,
    SERVICE_REFRESH,
)
from .coordinator import FavoriteStationCoordinator, NearbyCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    _migrate_entity_ids(hass, entry)

    session = async_get_clientsession(hass)
    api = NswFuelApi(
        session=session,
        base_url="https://api.onegov.nsw.gov.au",
        api_key=entry.data[CONF_API_KEY],
        api_secret=entry.data[CONF_API_SECRET],
    )

    nearby_coordinator = NearbyCoordinator(hass, entry, api)
    favorite_coordinator = FavoriteStationCoordinator(hass, entry, api)

    try:
        await nearby_coordinator.async_config_entry_first_refresh()
        if entry.data.get(CONF_FAVORITE_STATION_CODE, ""):
            await favorite_coordinator.async_config_entry_first_refresh()
    except Exception as exc:
        raise ConfigEntryNotReady from exc

    hass.data[DOMAIN][entry.entry_id]["coordinators"] = {
        "nearby": nearby_coordinator,
        "favorite": favorite_coordinator,
    }

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
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


def _migrate_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)

    desired: dict[str, str] = {
        f"{DOMAIN}_home_nearby": "sensor.home_cheapest_fuel",
        f"{DOMAIN}_favorite_station": "sensor.favorite_station_fuel",
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
