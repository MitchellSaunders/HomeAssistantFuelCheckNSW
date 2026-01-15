from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def parse_prices(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract raw price records from API payload."""
    items = payload.get("prices") or []
    return list(items)


def join_station_prices(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Join prices with station metadata for easier display."""
    stations = {str(s.get("code")): s for s in payload.get("stations", [])}
    joined: List[Dict[str, Any]] = []
    for price in payload.get("prices", []):
        code = str(price.get("stationcode"))
        station = stations.get(code, {})
        joined.append(
            {
                "stationcode": code,
                "fueltype": price.get("fueltype"),
                "price": price.get("price"),
                "lastupdated": price.get("lastupdated"),
                "brand": station.get("brand"),
                "name": station.get("name"),
                "address": station.get("address"),
                "location": station.get("location"),
                "isAdBlueAvailable": station.get("isAdBlueAvailable"),
            }
        )
    return joined


def filter_cheapest_fuels(
    records: Iterable[Dict[str, Any]],
    fueltypes: Iterable[str],
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    wanted = {f.strip() for f in fueltypes if f.strip()}
    filtered = [r for r in records if r.get("fueltype") in wanted]
    filtered.sort(key=lambda r: (r.get("price") is None, r.get("price")))
    if limit is not None:
        return filtered[: max(limit, 0)]
    return filtered
