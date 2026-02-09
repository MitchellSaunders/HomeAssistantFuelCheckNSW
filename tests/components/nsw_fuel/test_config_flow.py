from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
pytest.importorskip("homeassistant")

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.nsw_fuel.const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_BRANDS,
    CONF_FAVOURITE_STATION_CODE,
    CONF_HOME_LAT,
    CONF_HOME_LON,
    CONF_HOME_NAMEDLOCATION,
    CONF_PERSON_ENTITIES,
    CONF_PREFERRED_FUELS,
    CONF_RADIUS_KM,
    DOMAIN,
)


async def _create_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "NSW Fuel",
            CONF_API_KEY: "test-key",
            CONF_API_SECRET: "test-secret",
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOME_NAMEDLOCATION: "2287",
            CONF_HOME_LAT: "-32.8928",
            CONF_HOME_LON: "151.6620",
            CONF_RADIUS_KM: 10,
            CONF_BRANDS: "",
            CONF_PREFERRED_FUELS: ["E10", "U91"],
            CONF_PERSON_ENTITIES: ["person.alice"],
            CONF_FAVOURITE_STATION_CODE: "1234",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    return entry


@pytest.mark.asyncio
async def test_location_step_accepts_person_and_sensor_entities(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "NSW Fuel",
            CONF_API_KEY: "test-key",
            CONF_API_SECRET: "test-secret",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "location"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOME_NAMEDLOCATION: "2287",
            CONF_HOME_LAT: "-32.8928",
            CONF_HOME_LON: "151.6620",
            CONF_RADIUS_KM: 10,
            CONF_BRANDS: "",
            CONF_PREFERRED_FUELS: ["E10", "U91"],
            CONF_PERSON_ENTITIES: ["person.alice", "sensor.mobile_location"],
            CONF_FAVOURITE_STATION_CODE: "",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PERSON_ENTITIES] == "person.alice,sensor.mobile_location"


@pytest.mark.asyncio
async def test_location_step_persists_entities_as_csv(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "NSW Fuel",
            CONF_API_KEY: "test-key",
            CONF_API_SECRET: "test-secret",
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOME_NAMEDLOCATION: "2287",
            CONF_HOME_LAT: "-32.8928",
            CONF_HOME_LON: "151.6620",
            CONF_PERSON_ENTITIES: ["person.alice", "person.bob"],
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PERSON_ENTITIES] == "person.alice,person.bob"


@pytest.mark.asyncio
async def test_reconfigure_updates_values_and_preserves_name(hass, monkeypatch):
    entry = await _create_entry(hass)
    original_name = entry.data[CONF_NAME]

    monkeypatch.setattr(
        hass.config_entries,
        "async_reload",
        AsyncMock(return_value=True),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: "new-key",
            CONF_API_SECRET: "new-secret",
            CONF_HOME_NAMEDLOCATION: "2290",
            CONF_HOME_LAT: "-33.1000",
            CONF_HOME_LON: "151.8000",
            CONF_RADIUS_KM: 15,
            CONF_BRANDS: "Ampol|BP",
            CONF_PREFERRED_FUELS: ["P95", "P98"],
            CONF_PERSON_ENTITIES: ["person.alice", "sensor.phone_loc"],
            CONF_FAVOURITE_STATION_CODE: "9999",
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated_entry is not None
    assert updated_entry.data[CONF_NAME] == original_name
    assert updated_entry.data[CONF_API_KEY] == "new-key"
    assert updated_entry.data[CONF_API_SECRET] == "new-secret"
    assert updated_entry.data[CONF_PREFERRED_FUELS] == "P95|P98"
    assert updated_entry.data[CONF_PERSON_ENTITIES] == "person.alice,sensor.phone_loc"
