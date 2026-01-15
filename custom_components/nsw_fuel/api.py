from __future__ import annotations

import base64
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from aiohttp import ClientSession


class NswFuelApi:
    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        api_key: str,
        api_secret: str,
        authorization: Optional[str] = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._api_secret = api_secret
        self._authorization = authorization
        self._token: Optional[str] = None
        self._token_expiry: Optional[float] = None

    def _basic_auth_header(self) -> str:
        if self._authorization:
            return self._authorization
        raw = f"{self._api_key}:{self._api_secret}".encode("utf-8")
        encoded = base64.b64encode(raw).decode("ascii")
        return f"Basic {encoded}"

    async def _fetch_access_token(self) -> str:
        url = f"{self._base_url}/oauth/client_credential/accesstoken"
        headers = {"Authorization": self._basic_auth_header(), "Accept": "application/json"}
        params = {"grant_type": "client_credentials"}
        async with self._session.get(url, headers=headers, params=params) as resp:
            resp.raise_for_status()
            payload = await resp.json()
        token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not token:
            raise ValueError("Access token missing from response.")
        if expires_in:
            self._token_expiry = time.time() + int(expires_in) - 30
        else:
            self._token_expiry = None
        return token

    async def _get_access_token(self) -> str:
        if self._token and self._token_expiry:
            if time.time() < self._token_expiry:
                return self._token
        self._token = await self._fetch_access_token()
        return self._token

    @staticmethod
    def _utc_timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%d/%m/%Y %I:%M:%S %p")

    async def _headers(self) -> Dict[str, str]:
        token = await self._get_access_token()
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "apikey": self._api_key,
            "transactionid": str(uuid.uuid4()),
            "requesttimestamp": self._utc_timestamp(),
        }

    async def get_prices_nearby(
        self,
        *,
        fueltype: str,
        brands: list[str],
        namedlocation: str,
        latitude: str,
        longitude: str,
        radius_km: str,
        sortby: str = "price",
        sortascending: str = "true",
    ) -> Dict[str, Any]:
        url = f"{self._base_url}/FuelPriceCheck/v1/fuel/prices/nearby"
        payload = {
            "fueltype": fueltype,
            "brand": brands,
            "namedlocation": namedlocation,
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius_km,
            "sortby": sortby,
            "sortascending": sortascending,
        }
        headers = await self._headers()
        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.content_length == 0:
                return {"stations": [], "prices": []}
            resp.raise_for_status()
            return await resp.json()

    async def get_station_prices(self, station_code: str) -> Dict[str, Any]:
        url = f"{self._base_url}/FuelPriceCheck/v1/fuel/prices/station/{station_code}"
        headers = await self._headers()
        async with self._session.get(url, headers=headers) as resp:
            if resp.content_length == 0:
                return {"prices": []}
            resp.raise_for_status()
            return await resp.json()
