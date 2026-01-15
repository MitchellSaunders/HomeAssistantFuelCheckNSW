from __future__ import annotations

import os

from dotenv import load_dotenv

from nsw_fuel_client import NswFuelClient
from parser import filter_cheapest_fuels, join_station_prices


def main() -> None:
    load_dotenv()
    base_url = os.environ.get("NSW_FUEL_API_BASE_URL", "")
    if not base_url:
        raise SystemExit("Missing NSW_FUEL_API_BASE_URL in environment.")

    client = NswFuelClient(
        base_url=base_url,
        api_key=os.environ.get("NSW_FUEL_API_KEY"),
        api_secret=os.environ.get("NSW_FUEL_API_SECRET"),
        authorisation=os.environ.get("NSW_FUEL_API_AUTHORISATION"),
    )
    fueltype = os.environ.get("NSW_FUEL_API_FUELTYPE", "U91")
    brands_raw = os.environ.get("NSW_FUEL_API_BRANDS", "")
    brands = [b for b in brands_raw.split("|") if b]
    radius_km = os.environ.get("NSW_FUEL_API_RADIUS_KM", "5")
    namedlocation = os.environ.get("NSW_FUEL_API_NAMEDLOCATION", "")
    latitude = os.environ.get("NSW_FUEL_API_LAT", "")
    longitude = os.environ.get("NSW_FUEL_API_LON", "")
    sortby = os.environ.get("NSW_FUEL_API_SORTBY", "price")
    sortascending = os.environ.get("NSW_FUEL_API_SORTASCENDING", "true")
    station_code = os.environ.get("NSW_FUEL_API_STATION_CODE", "")

    if station_code:
        payload = client.get_station_prices_v1(station_code)
        joined = join_station_prices({"stations": [], "prices": payload.get("prices", [])})
        print(f"Station {station_code} prices: {len(joined)}")
        for item in joined:
            print(
                f"{item.get('price')} {item.get('fueltype')} | {item.get('lastupdated')}"
            )
        return

    if not namedlocation or not latitude or not longitude:
        raise SystemExit("Missing NSW_FUEL_API_NAMEDLOCATION or NSW_FUEL_API_LAT/LON.")

    payload = client.get_prices_nearby_v1(
        fueltype=fueltype,
        brands=brands,
        namedlocation=namedlocation,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        sortby=sortby,
        sortascending=sortascending,
    )
    preferred = os.environ.get("NSW_FUEL_API_PREFERRED_FUELS", "E10|U91|P95|P98")
    preferred_list = [f for f in preferred.split("|") if f]
    limit = int(os.environ.get("NSW_FUEL_API_RESULTS_LIMIT", "10"))

    joined = join_station_prices(payload)
    cheapest = filter_cheapest_fuels(joined, preferred_list, limit=limit)
    print(f"Retrieved {len(joined)} prices; showing {len(cheapest)} cheapest.")
    for item in cheapest:
        print(
            f"{item.get('price')} {item.get('fueltype')} | {item.get('brand')} | "
            f"{item.get('name')} | {item.get('address')} | {item.get('lastupdated')}"
        )


if __name__ == "__main__":
    main()
