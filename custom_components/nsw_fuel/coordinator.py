from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import NswFuelApi
from .const import (
    CONF_BRANDS,
    CONF_FAVORITE_STATION_CODE,
    CONF_FAVORITE_UPDATE_MINUTES,
    CONF_HOME_LAT,
    CONF_HOME_LON,
    CONF_HOME_NAMEDLOCATION,
    CONF_NEARBY_UPDATE_MINUTES,
    CONF_PERSON_ENTITIES,
    CONF_PREFERRED_FUELS,
    CONF_RADIUS_KM,
    DEFAULT_FAVORITE_UPDATE_MINUTES,
    DEFAULT_NEARBY_UPDATE_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


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
        _LOGGER.warning("Location entity missing: %s", entity_id)
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
        _LOGGER.warning("Location entity missing lat/lon: %s attrs=%s", entity_id, attrs)
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
            logger=_LOGGER,
            name="nsw_fuel_nearby",
            update_interval=timedelta(minutes=interval),
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> Dict[str, Any]:
        preferred_fuels = _split_pipe(self.entry.data[CONF_PREFERRED_FUELS])
        brands = _split_pipe(self.entry.data.get(CONF_BRANDS, ""))
        radius_raw = self.entry.data[CONF_RADIUS_KM]
        try:
            radius_km = str(int(float(radius_raw)))
        except (TypeError, ValueError):
            radius_km = str(radius_raw)
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
                try:
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
                except Exception as err:
                    _LOGGER.error("Nearby request failed for %s (%s): %s", loc_id, fuel, err)
                    raise UpdateFailed(f"Nearby request failed: {err}") from err
                joined = _join_station_prices(payload)
                cheapest = _pick_cheapest(joined)
                if cheapest and (not best or cheapest["price"] < best["price"]):
                    best = cheapest

            if not best:
                _LOGGER.warning(
                    "No prices found for %s (lat=%s lon=%s postal=%s fuels=%s)",
                    loc_id,
                    loc.get("lat"),
                    loc.get("lon"),
                    loc.get("postal"),
                    preferred_fuels,
                )
            results[loc_id] = {
                "best": best,
                "last_checked": checked_at,
            }
        return results


class FavoriteStationCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: NswFuelApi) -> None:
        interval = entry.data.get(CONF_FAVORITE_UPDATE_MINUTES, DEFAULT_FAVORITE_UPDATE_MINUTES)
        super().__init__(
            hass,
            logger=_LOGGER,
            name="nsw_fuel_favorite_station",
            update_interval=timedelta(minutes=interval),
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> Dict[str, Any]:
        station_code = self.entry.data.get(CONF_FAVORITE_STATION_CODE, "")
        if not station_code:
            _LOGGER.info("Favorite station code not configured; skipping update.")
            return {}
        preferred_fuels = set(_split_pipe(self.entry.data[CONF_PREFERRED_FUELS]))
        checked_at = dt_util.utcnow().isoformat()
        try:
            payload = await self.api.get_station_prices(station_code)
        except Exception as err:
            _LOGGER.error("Favorite station request failed (%s): %s", station_code, err)
            raise UpdateFailed(f"Favorite station request failed: {err}") from err
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
