from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import NswFuelApi
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_HOME_NAMEDLOCATION,
    CONF_HOME_LAT,
    CONF_HOME_LON,
    CONF_RADIUS_KM,
    CONF_BRANDS,
    CONF_PREFERRED_FUELS,
    CONF_PERSON_ENTITIES,
    CONF_COSTCO_STATION_CODE,
    CONF_FAVORITE_STATION_CODE,
    CONF_NEARBY_UPDATE_MINUTES,
    CONF_COSTCO_UPDATE_MINUTES,
    CONF_FAVORITE_UPDATE_MINUTES,
    DEFAULT_NEARBY_UPDATE_MINUTES,
    DEFAULT_COSTCO_UPDATE_MINUTES,
    DOMAIN,
)


def _split_pipe(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split("|") if v.strip()]


def _split_commas(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _get_entity_location(hass: HomeAssistant, entity_id: str) -> Optional[Dict[str, str]]:
    state = hass.states.get(entity_id)
    if not state:
        return None
    attrs = state.attributes

    location = attrs.get("Location") or attrs.get("location")
    if isinstance(location, str) and "," in location:
        lat_str, lon_str = [v.strip() for v in location.split(",", 1)]
    else:
        lat_str = attrs.get("latitude") or attrs.get("Latitude")
        lon_str = attrs.get("longitude") or attrs.get("Longitude")

    postal = (
        attrs.get("Postal Code")
        or attrs.get("postal_code")
        or attrs.get("postcode")
        or attrs.get("Postcode")
    )

    if not lat_str or not lon_str:
        return None
    return {"lat": str(lat_str), "lon": str(lon_str), "postal": str(postal or "")}


def _join_station_prices(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    stations = {str(s.get("code")): s for s in payload.get("stations", [])}
    joined: List[Dict[str, Any]] = []
    for price in payload.get("prices", []):
        code = str(price.get("stationcode"))
        station = stations.get(code, {})
        location = station.get("location") or {}
        joined.append(
            {
                "stationcode": code,
                "fueltype": price.get("fueltype"),
                "price": price.get("price"),
                "lastupdated": price.get("lastupdated"),
                "brand": station.get("brand"),
                "name": station.get("name"),
                "address": station.get("address"),
                "distance": location.get("distance"),
            }
        )
    return joined


def _pick_cheapest(records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    records = [r for r in records if r.get("price") is not None]
    if not records:
        return None
    records.sort(key=lambda r: r.get("price"))
    return records[0]


class NearbyCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: NswFuelApi) -> None:
        interval = entry.data.get(CONF_NEARBY_UPDATE_MINUTES, DEFAULT_NEARBY_UPDATE_MINUTES)
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="nsw_fuel_nearby",
            update_interval=timedelta(minutes=interval),
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> Dict[str, Any]:
        preferred_fuels = _split_pipe(self.entry.data[CONF_PREFERRED_FUELS])
        brands = _split_pipe(self.entry.data.get(CONF_BRANDS, ""))
        radius_km = self.entry.data[CONF_RADIUS_KM]
        namedlocation = self.entry.data[CONF_HOME_NAMEDLOCATION]
        home_lat = self.entry.data[CONF_HOME_LAT]
        home_lon = self.entry.data[CONF_HOME_LON]

        locations: Dict[str, Dict[str, str]] = {
            "home": {"lat": home_lat, "lon": home_lon, "postal": namedlocation}
        }
        for entity_id in _split_commas(self.entry.data.get(CONF_PERSON_ENTITIES, "")):
            loc = _get_entity_location(self.hass, entity_id)
            if loc:
                locations[entity_id] = loc

        results: Dict[str, Any] = {}
        checked_at = dt_util.utcnow().isoformat()

        for loc_id, loc in locations.items():
            best: Optional[Dict[str, Any]] = None
            for fuel in preferred_fuels:
                payload = await self.api.get_prices_nearby(
                    fueltype=fuel,
                    brands=brands,
                    namedlocation=loc.get("postal") or namedlocation,
                    latitude=loc["lat"],
                    longitude=loc["lon"],
                    radius_km=radius_km,
                    sortby="price",
                    sortascending="true",
                )
                joined = _join_station_prices(payload)
                cheapest = _pick_cheapest(joined)
                if cheapest and (not best or cheapest["price"] < best["price"]):
                    best = cheapest

            results[loc_id] = {
                "best": best,
                "last_checked": checked_at,
            }
        return results


class FavoriteStationCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: NswFuelApi) -> None:
        interval = entry.data.get(CONF_FAVORITE_UPDATE_MINUTES) or entry.data.get(
            CONF_COSTCO_UPDATE_MINUTES, DEFAULT_COSTCO_UPDATE_MINUTES
        )
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="nsw_fuel_favorite_station",
            update_interval=timedelta(minutes=interval),
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> Dict[str, Any]:
        station_code = self.entry.data.get(CONF_FAVORITE_STATION_CODE) or self.entry.data.get(
            CONF_COSTCO_STATION_CODE, ""
        )
        if not station_code:
            return {}
        preferred_fuels = set(_split_pipe(self.entry.data[CONF_PREFERRED_FUELS]))
        checked_at = dt_util.utcnow().isoformat()
        payload = await self.api.get_station_prices(station_code)
        prices = [
            p for p in payload.get("prices", []) if p.get("fueltype") in preferred_fuels
        ]
        prices.sort(key=lambda p: p.get("price"))
        best = prices[0] if prices else None
        return {
            "station_code": station_code,
            "prices": prices,
            "best": best,
            "last_checked": checked_at,
        }


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    session = async_get_clientsession(hass)
    api = NswFuelApi(
        session=session,
        base_url="https://api.onegov.nsw.gov.au",
        api_key=entry.data[CONF_API_KEY],
        api_secret=entry.data[CONF_API_SECRET],
    )

    nearby_coordinator = NearbyCoordinator(hass, entry, api)
    favorite_coordinator = FavoriteStationCoordinator(hass, entry, api)

    await nearby_coordinator.async_config_entry_first_refresh()
    favorite_station = entry.data.get(CONF_FAVORITE_STATION_CODE) or entry.data.get(
        CONF_COSTCO_STATION_CODE, ""
    )
    if favorite_station:
        await favorite_coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id]["coordinators"] = [
        nearby_coordinator,
        favorite_coordinator,
    ]

    entities: List[SensorEntity] = []
    entities.append(NswFuelNearbySensor(nearby_coordinator, "home", "Home Cheapest"))
    for entity_id in _split_commas(entry.data.get(CONF_PERSON_ENTITIES, "")):
        entities.append(NswFuelNearbySensor(nearby_coordinator, entity_id, entity_id))

    if favorite_station:
        entities.append(NswFuelFavoriteStationSensor(favorite_coordinator))

    async_add_entities(entities)


class NswFuelNearbySensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: NearbyCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{key}_nearby"

    @property
    def native_value(self) -> Optional[float]:
        data = self.coordinator.data.get(self._key, {})
        best = data.get("best")
        return best.get("price") if best else None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data.get(self._key, {})
        best = data.get("best") or {}
        return {
            "fueltype": best.get("fueltype"),
            "brand": best.get("brand"),
            "stationcode": best.get("stationcode"),
            "station_name": best.get("name"),
            "address": best.get("address"),
            "distance": best.get("distance"),
            "last_checked": data.get("last_checked"),
            "last_changed": best.get("lastupdated"),
        }


class NswFuelFavoriteStationSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: FavoriteStationCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Favorite Station Fuel"
        self._attr_unique_id = f"{DOMAIN}_favorite_station"

    @property
    def native_value(self) -> Optional[float]:
        best = self.coordinator.data.get("best") or {}
        return best.get("price")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data
        best = data.get("best") or {}
        return {
            "station_code": data.get("station_code"),
            "fueltype": best.get("fueltype"),
            "last_checked": data.get("last_checked"),
            "last_changed": best.get("lastupdated"),
            "prices": data.get("prices", []),
        }
