from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er

from .api import NswFuelApi
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_PERSON_ENTITIES,
    DOMAIN,
    SERVICE_REFRESH,
)
from .coordinator import ApiCallCounter, FavouriteStationCoordinator, NearbyCoordinator

PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)


async def _async_handle_refresh(hass: HomeAssistant, call: ServiceCall) -> None:
    """Refresh all NSW fuel coordinators across all config entries."""
    del call
    entry_map = hass.data.get(DOMAIN, {})
    contexts: list[tuple[str, str, str]] = []
    coros = []
    for entry_id, entry_data in entry_map.items():
        for coordinator_name, coordinator in entry_data.get("coordinators", {}).items():
            coros.append(coordinator.async_request_refresh())
            contexts.append((entry_id, coordinator_name, coordinator.name))
    if not coros:
        _LOGGER.debug("Manual refresh requested with no active coordinators.")
        return
    results = await asyncio.gather(*coros, return_exceptions=True)
    failures: list[tuple[str, str, str, Exception]] = []
    for (entry_id, coordinator_name, coordinator_label), result in zip(contexts, results):
        if not isinstance(result, Exception):
            continue
        failures.append((entry_id, coordinator_name, coordinator_label, result))
        _LOGGER.error(
            "Manual refresh failed for entry_id=%s coordinator=%s label=%s error=%s",
            entry_id,
            coordinator_name,
            coordinator_label,
            result,
            exc_info=(type(result), result, result.__traceback__),
        )
    if failures:
        summary = ", ".join(
            f"{entry_id}:{coordinator_name}:{type(err).__name__}"
            for entry_id, coordinator_name, _coordinator_label, err in failures
        )
        raise HomeAssistantError(
            f"NSW fuel refresh completed with {len(failures)} failure(s): {summary}"
        )


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

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        async def _handle_refresh(call: ServiceCall) -> None:
            await _async_handle_refresh(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH,
            _handle_refresh,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        for unsub in hass.data[DOMAIN].get(entry.entry_id, {}).get("unsub", []):
            unsub()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, SERVICE_REFRESH):
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
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
