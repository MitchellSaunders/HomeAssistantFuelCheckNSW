from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import main as cli_main


def _set_common_env(monkeypatch) -> None:
    monkeypatch.setenv("NSW_FUEL_API_BASE_URL", "https://api.onegov.nsw.gov.au")
    monkeypatch.setenv("NSW_FUEL_API_KEY", "test-key")
    monkeypatch.setenv("NSW_FUEL_API_SECRET", "test-secret")
    monkeypatch.setenv("NSW_FUEL_API_NAMEDLOCATION", "2287")
    monkeypatch.setenv("NSW_FUEL_API_LAT", "-32.8928")
    monkeypatch.setenv("NSW_FUEL_API_LON", "151.6620")
    monkeypatch.setenv("NSW_FUEL_API_RADIUS_KM", "10")
    monkeypatch.setenv("NSW_FUEL_API_STATION_CODE", "")
    monkeypatch.setenv("NSW_FUEL_API_RESULTS_LIMIT", "10")


def test_main_calls_nearby_once_per_preferred_fuel(monkeypatch):
    _set_common_env(monkeypatch)
    monkeypatch.setenv("NSW_FUEL_API_FUELTYPE", "U91")
    monkeypatch.setenv("NSW_FUEL_API_PREFERRED_FUELS", "E10|U91|P95")

    calls: list[str] = []

    class FakeClient:
        def __init__(self, **_kwargs) -> None:
            return

        def get_prices_nearby_v1(self, **kwargs):
            fueltype = kwargs["fueltype"]
            calls.append(fueltype)
            return {
                "stations": [
                    {
                        "code": fueltype,
                        "brand": "Test Brand",
                        "name": "Test Station",
                        "address": "123 Test Street",
                        "location": {"latitude": -32.9, "longitude": 151.7},
                    }
                ],
                "prices": [
                    {
                        "stationcode": fueltype,
                        "fueltype": fueltype,
                        "price": 170.1,
                        "lastupdated": "01/01/2026 01:00:00 PM",
                    }
                ],
            }

    monkeypatch.setattr(cli_main, "NswFuelClient", FakeClient)

    cli_main.main()

    assert calls == ["E10", "U91", "P95"]


def test_main_falls_back_to_single_fuel_when_preferred_empty(monkeypatch):
    _set_common_env(monkeypatch)
    monkeypatch.setenv("NSW_FUEL_API_FUELTYPE", "U91")
    monkeypatch.setenv("NSW_FUEL_API_PREFERRED_FUELS", "")

    calls: list[str] = []

    class FakeClient:
        def __init__(self, **_kwargs) -> None:
            return

        def get_prices_nearby_v1(self, **kwargs):
            fueltype = kwargs["fueltype"]
            calls.append(fueltype)
            return {
                "stations": [
                    {
                        "code": fueltype,
                        "brand": "Test Brand",
                        "name": "Test Station",
                        "address": "123 Test Street",
                        "location": {"latitude": -32.9, "longitude": 151.7},
                    }
                ],
                "prices": [
                    {
                        "stationcode": fueltype,
                        "fueltype": fueltype,
                        "price": 170.1,
                        "lastupdated": "01/01/2026 01:00:00 PM",
                    }
                ],
            }

    monkeypatch.setattr(cli_main, "NswFuelClient", FakeClient)

    cli_main.main()

    assert calls == ["U91"]
