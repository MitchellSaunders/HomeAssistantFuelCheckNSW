from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NswFuelApi
from .const import CONF_API_KEY, CONF_API_SECRET, CONF_FAVORITE_STATION_CODE, DOMAIN, SERVICE_REFRESH
from .coordinator import FavoriteStationCoordinator, NearbyCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

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
