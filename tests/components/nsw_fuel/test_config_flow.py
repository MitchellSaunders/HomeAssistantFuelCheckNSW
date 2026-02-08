from __future__ import annotations

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
