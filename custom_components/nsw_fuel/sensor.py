from __future__ import annotations

from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FAVORITE_STATION_CODE, CONF_PERSON_ENTITIES, DOMAIN
from .coordinator import FavoriteStationCoordinator, NearbyCoordinator, _split_commas


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    nearby_coordinator = coordinators["nearby"]
    favorite_coordinator = coordinators["favorite"]

    entities: List[SensorEntity] = []
    entities.append(NswFuelNearbySensor(nearby_coordinator, "home", "Home Cheapest"))
    for entity_id in _split_commas(entry.data.get(CONF_PERSON_ENTITIES, "")):
        entities.append(NswFuelNearbySensor(nearby_coordinator, entity_id, entity_id))

    if entry.data.get(CONF_FAVORITE_STATION_CODE, ""):
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
