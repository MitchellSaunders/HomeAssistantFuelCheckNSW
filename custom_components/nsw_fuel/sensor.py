from __future__ import annotations

from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FAVOURITE_STATION_CODE, CONF_PERSON_ENTITIES, DOMAIN
from .coordinator import ApiCallCounter, FavouriteStationCoordinator, NearbyCoordinator, _split_commas


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    nearby_coordinator = coordinators["nearby"]
    favourite_coordinator = coordinators["favourite"]
    api_calls = hass.data[DOMAIN][entry.entry_id]["api_calls"]

    entities: List[SensorEntity] = []
    entities.append(NswFuelNearbySensor(nearby_coordinator, "home", "Home Cheapest Fuel"))
    for idx, entity_id in enumerate(_split_commas(entry.data.get(CONF_PERSON_ENTITIES, "")), start=1):
        state = hass.states.get(entity_id)
        label = state.name if state else f"User {idx}"
        entities.append(
            NswFuelNearbySensor(
                nearby_coordinator, entity_id, f"{label} Nearby Cheapest Fuel"
            )
        )

    if entry.data.get(CONF_FAVOURITE_STATION_CODE, ""):
        entities.append(NswFuelFavouriteStationSensor(favourite_coordinator))
    entities.append(NswFuelApiCallsSensor(api_calls))

    async_add_entities(entities)


class NswFuelNearbySensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:gas-station"
    _attr_native_unit_of_measurement = "c/L"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NearbyCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{key}_nearby"

    @property
    def native_value(self) -> Optional[float]:
        data = (self.coordinator.data or {}).get(self._key, {})
        best = data.get("best")
        price = best.get("price") if best else None
        return _to_float(price)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = (self.coordinator.data or {}).get(self._key, {})
        best = data.get("best") or {}
        attrs = {
            "fueltype": best.get("fueltype"),
            "brand": best.get("brand"),
            "stationcode": best.get("stationcode"),
            "station_name": best.get("name"),
            "address": best.get("address"),
            "distance": best.get("distance"),
            "last_checked": data.get("last_checked"),
            "last_changed": best.get("lastupdated"),
        }
        if self._key != "home":
            attrs["distance_to_home_cheapest"] = data.get("distance_to_home_cheapest")
        return attrs


class NswFuelFavouriteStationSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:gas-station"
    _attr_native_unit_of_measurement = "c/L"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: FavouriteStationCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Favourite Station Fuel"
        self._attr_unique_id = f"{DOMAIN}_favourite_station"

    @property
    def native_value(self) -> Optional[float]:
        best = (self.coordinator.data or {}).get("best") or {}
        return _to_float(best.get("price"))

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        best = data.get("best") or {}
        return {
            "station_code": data.get("station_code"),
            "fueltype": best.get("fueltype"),
            "last_checked": data.get("last_checked"),
            "last_changed": best.get("lastupdated"),
            "prices": data.get("prices", []),
        }


class NswFuelApiCallsSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = "calls"

    def __init__(self, coordinator: ApiCallCounter) -> None:
        super().__init__(coordinator)
        self._attr_name = "API Calls Used Today"
        self._attr_unique_id = f"{DOMAIN}_api_calls_today"

    @property
    def native_value(self) -> Optional[int]:
        return int((self.coordinator.data or {}).get("count", 0))

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "date": data.get("date"),
            "last_reset": data.get("last_reset"),
        }
