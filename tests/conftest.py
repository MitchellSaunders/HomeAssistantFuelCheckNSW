from __future__ import annotations

import importlib.util

import pytest

CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_HOME_NAMEDLOCATION = "home_namedlocation"
CONF_HOME_LAT = "home_lat"
CONF_HOME_LON = "home_lon"
CONF_RADIUS_KM = "radius_km"
CONF_BRANDS = "brands"
CONF_PREFERRED_FUELS = "preferred_fuels"
CONF_PERSON_ENTITIES = "person_entities"
CONF_FAVOURITE_STATION_CODE = "favourite_station_code"
CONF_NEARBY_UPDATE_MINUTES = "nearby_update_minutes"
CONF_FAVOURITE_UPDATE_MINUTES = "favourite_update_minutes"

DEFAULT_RADIUS_KM = "10"
DEFAULT_PREFERRED_FUELS = "E10|U91|P95|P98"
DEFAULT_NEARBY_UPDATE_MINUTES = 360
DEFAULT_FAVOURITE_UPDATE_MINUTES = 360


_HAS_HOMEASSISTANT = importlib.util.find_spec("homeassistant") is not None

if _HAS_HOMEASSISTANT:

    @pytest.fixture(autouse=True)
    def auto_enable_custom_integrations(enable_custom_integrations):
        """Enable loading custom integrations from this repository in tests."""
        yield


@pytest.fixture
def nsw_entry_data() -> dict[str, object]:
    return {
        "name": "NSW Fuel",
        CONF_API_KEY: "test-key",
        CONF_API_SECRET: "test-secret",
        CONF_HOME_NAMEDLOCATION: "2287",
        CONF_HOME_LAT: "-32.89288905201317",
        CONF_HOME_LON: "151.66201724233989",
        CONF_RADIUS_KM: DEFAULT_RADIUS_KM,
        CONF_BRANDS: "",
        CONF_PREFERRED_FUELS: DEFAULT_PREFERRED_FUELS,
        CONF_PERSON_ENTITIES: "",
        CONF_FAVOURITE_STATION_CODE: "",
        CONF_NEARBY_UPDATE_MINUTES: DEFAULT_NEARBY_UPDATE_MINUTES,
        CONF_FAVOURITE_UPDATE_MINUTES: DEFAULT_FAVOURITE_UPDATE_MINUTES,
    }


@pytest.fixture
def sample_nearby_payload() -> dict[str, object]:
    return {
        "stations": [
            {
                "code": "100",
                "brand": "Test Brand",
                "name": "Test Station",
                "address": "123 Test Street",
                "location": {
                    "distance": 1.2,
                    "latitude": -32.9,
                    "longitude": 151.7,
                },
            }
        ],
        "prices": [
            {
                "stationcode": "100",
                "fueltype": "E10",
                "price": 170.1,
                "lastupdated": "01/01/2026 01:00:00 PM",
            }
        ],
    }
