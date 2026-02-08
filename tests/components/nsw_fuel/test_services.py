from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("homeassistant")

from custom_components.nsw_fuel import __init__ as nsw_init
from custom_components.nsw_fuel.const import (
    CONF_FAVOURITE_STATION_CODE,
    DOMAIN,
    SERVICE_REFRESH,
)
from homeassistant.exceptions import HomeAssistantError


class _FakeCoordinator:
    def __init__(self) -> None:
        self.async_config_entry_first_refresh = AsyncMock()
        self.async_request_refresh = AsyncMock()


class _FakeApiCallCounter:
    def __init__(self, *_args, **_kwargs) -> None:
        self.async_increment = AsyncMock()
        self.async_reset_if_new_day = AsyncMock()
        self.data = {"date": "2026-02-08", "count": 0, "last_reset": "2026-02-08T00:00:00+00:00"}


class _FakeApi:
    def __init__(self, *_args, **_kwargs) -> None:
        return


def _entry(entry_id: str, data: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(entry_id=entry_id, data=dict(data))


def _setup_patches(hass, monkeypatch):
    monkeypatch.setattr(nsw_init, "_migrate_entity_ids", lambda _hass, _entry: None)
    monkeypatch.setattr(nsw_init, "async_get_clientsession", lambda _hass: object())
    monkeypatch.setattr(nsw_init, "NswFuelApi", _FakeApi)
    monkeypatch.setattr(nsw_init, "ApiCallCounter", _FakeApiCallCounter)
    monkeypatch.setattr(
        hass.config_entries,
        "async_forward_entry_setups",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        hass.config_entries,
        "async_unload_platforms",
        AsyncMock(return_value=True),
    )

    nearby_by_entry: dict[str, _FakeCoordinator] = {}
    favourite_by_entry: dict[str, _FakeCoordinator] = {}

    def _fake_nearby(_hass, entry, _api):
        coord = _FakeCoordinator()
        nearby_by_entry[entry.entry_id] = coord
        return coord

    def _fake_favourite(_hass, entry, _api):
        coord = _FakeCoordinator()
        favourite_by_entry[entry.entry_id] = coord
        return coord

    monkeypatch.setattr(nsw_init, "NearbyCoordinator", _fake_nearby)
    monkeypatch.setattr(nsw_init, "FavouriteStationCoordinator", _fake_favourite)
    return nearby_by_entry, favourite_by_entry


@pytest.mark.asyncio
async def test_refresh_service_refreshes_all_entries(hass, monkeypatch, nsw_entry_data):
    nearby_by_entry, favourite_by_entry = _setup_patches(hass, monkeypatch)

    data_a = dict(nsw_entry_data)
    data_a[CONF_FAVOURITE_STATION_CODE] = "1000"
    data_b = dict(nsw_entry_data)
    data_b[CONF_FAVOURITE_STATION_CODE] = "2000"

    entry_a = _entry("entry-a", data_a)
    entry_b = _entry("entry-b", data_b)

    assert await nsw_init.async_setup_entry(hass, entry_a)
    assert await nsw_init.async_setup_entry(hass, entry_b)

    await hass.services.async_call(DOMAIN, SERVICE_REFRESH, blocking=True)

    assert nearby_by_entry["entry-a"].async_request_refresh.await_count == 1
    assert favourite_by_entry["entry-a"].async_request_refresh.await_count == 1
    assert nearby_by_entry["entry-b"].async_request_refresh.await_count == 1
    assert favourite_by_entry["entry-b"].async_request_refresh.await_count == 1


@pytest.mark.asyncio
async def test_refresh_service_removed_after_last_unload(hass, monkeypatch, nsw_entry_data):
    _setup_patches(hass, monkeypatch)
    entry = _entry("entry-a", nsw_entry_data)

    assert await nsw_init.async_setup_entry(hass, entry)
    assert hass.services.has_service(DOMAIN, SERVICE_REFRESH)

    assert await nsw_init.async_unload_entry(hass, entry)
    assert not hass.services.has_service(DOMAIN, SERVICE_REFRESH)


@pytest.mark.asyncio
async def test_refresh_service_persists_when_one_entry_unloads(hass, monkeypatch, nsw_entry_data):
    nearby_by_entry, favourite_by_entry = _setup_patches(hass, monkeypatch)

    data_a = dict(nsw_entry_data)
    data_b = dict(nsw_entry_data)
    entry_a = _entry("entry-a", data_a)
    entry_b = _entry("entry-b", data_b)

    assert await nsw_init.async_setup_entry(hass, entry_a)
    assert await nsw_init.async_setup_entry(hass, entry_b)
    assert await nsw_init.async_unload_entry(hass, entry_a)

    assert hass.services.has_service(DOMAIN, SERVICE_REFRESH)

    await hass.services.async_call(DOMAIN, SERVICE_REFRESH, blocking=True)

    assert nearby_by_entry["entry-a"].async_request_refresh.await_count == 0
    assert favourite_by_entry["entry-a"].async_request_refresh.await_count == 0
    assert nearby_by_entry["entry-b"].async_request_refresh.await_count == 1
    assert favourite_by_entry["entry-b"].async_request_refresh.await_count == 1


@pytest.mark.asyncio
async def test_no_automatic_first_refresh_on_setup(hass, monkeypatch, nsw_entry_data):
    nearby_by_entry, favourite_by_entry = _setup_patches(hass, monkeypatch)

    entry = _entry("entry-a", nsw_entry_data)
    assert await nsw_init.async_setup_entry(hass, entry)

    assert nearby_by_entry["entry-a"].async_config_entry_first_refresh.await_count == 0
    assert favourite_by_entry["entry-a"].async_config_entry_first_refresh.await_count == 0


@pytest.mark.asyncio
async def test_refresh_service_logs_and_raises_on_failures(
    hass, monkeypatch, nsw_entry_data, caplog
):
    nearby_by_entry, _favourite_by_entry = _setup_patches(hass, monkeypatch)

    data = dict(nsw_entry_data)
    entry = _entry("entry-a", data)
    assert await nsw_init.async_setup_entry(hass, entry)

    nearby_by_entry["entry-a"].async_request_refresh.side_effect = RuntimeError("boom")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(DOMAIN, SERVICE_REFRESH, blocking=True)

    assert "Manual refresh failed for entry_id=entry-a coordinator=nearby" in caplog.text
    assert "boom" in caplog.text
