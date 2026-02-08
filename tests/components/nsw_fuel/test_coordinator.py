from __future__ import annotations

from types import SimpleNamespace

import pytest
pytest.importorskip("homeassistant")

from custom_components.nsw_fuel.const import (
    CONF_HOME_LAT,
    CONF_HOME_LON,
    CONF_HOME_NAMEDLOCATION,
    CONF_PERSON_ENTITIES,
    CONF_PREFERRED_FUELS,
)
from custom_components.nsw_fuel.coordinator import NearbyCoordinator


class _FakeApi:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.calls: list[dict[str, str | list[str]]] = []

    async def get_prices_nearby(self, **kwargs):
        self.calls.append(kwargs)
        fueltype = kwargs["fueltype"]
        return {
            "stations": self._payload["stations"],
            "prices": [
                {
                    "stationcode": "100",
                    "fueltype": fueltype,
                    "price": 170.1 if fueltype == "E10" else 180.2,
                    "lastupdated": "01/01/2026 01:00:00 PM",
                }
            ],
        }


@pytest.mark.asyncio
async def test_nearby_coordinator_deduplicates_identical_location_queries(
    hass, nsw_entry_data, sample_nearby_payload
):
    data = dict(nsw_entry_data)
    data[CONF_PREFERRED_FUELS] = "E10|U91"
    data[CONF_PERSON_ENTITIES] = "person.alice,person.bob"
    data[CONF_HOME_NAMEDLOCATION] = "2287"
    data[CONF_HOME_LAT] = "-32.8928"
    data[CONF_HOME_LON] = "151.6620"
    entry = SimpleNamespace(data=data)

    hass.states.async_set(
        "person.alice",
        "home",
        {"latitude": "-32.8928", "longitude": "151.6620", "postal_code": "2287"},
    )
    hass.states.async_set(
        "person.bob",
        "home",
        {"latitude": "-32.8928", "longitude": "151.6620", "postal_code": "2287"},
    )

    api = _FakeApi(sample_nearby_payload)
    coordinator = NearbyCoordinator(hass, entry, api)

    data = await coordinator._async_update_data()

    assert len(api.calls) == 2
    assert set(data.keys()) == {"home", "person.alice", "person.bob"}


@pytest.mark.asyncio
async def test_nearby_interval_is_disabled_for_daily_schedule(
    hass, nsw_entry_data, sample_nearby_payload
):
    entry = SimpleNamespace(data=dict(nsw_entry_data))
    api = _FakeApi(sample_nearby_payload)
    coordinator = NearbyCoordinator(hass, entry, api)
    assert coordinator.update_interval is None
