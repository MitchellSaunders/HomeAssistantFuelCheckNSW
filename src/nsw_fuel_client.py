from __future__ import annotations

import base64
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import requests


@dataclass
class NswFuelClient:
    base_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    authorization: Optional[str] = None
    _token: Optional[str] = None
    _token_expiry: Optional[float] = None

    def _basic_auth_header(self) -> str:
        if self.authorization:
            return self.authorization
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing api_key/api_secret for token request.")
        raw = f"{self.api_key}:{self.api_secret}".encode("utf-8")
        encoded = base64.b64encode(raw).decode("ascii")
        return f"Basic {encoded}"

    def _fetch_access_token(self) -> Tuple[str, Optional[float]]:
        url = f"{self.base_url.rstrip('/')}/oauth/client_credential/accesstoken"
        headers = {"Authorization": self._basic_auth_header(), "Accept": "application/json"}
        params = {"grant_type": "client_credentials"}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not token:
            raise ValueError("Access token missing from response.")
        expiry = time.time() + int(expires_in) - 30 if expires_in else None
        return token, expiry

    def _get_access_token(self) -> str:
        if self._token and self._token_expiry:
            if time.time() < self._token_expiry:
                return self._token
        token, expiry = self._fetch_access_token()
        self._token = token
        self._token_expiry = expiry
        return token

    @staticmethod
    def _utc_timestamp() -> str:
        # Format required by API: dd/MM/yyyy hh:mm:ss AM/PM in UTC.
        return datetime.now(timezone.utc).strftime("%d/%m/%Y %I:%M:%S %p")

    def _headers(self) -> Dict[str, str]:
        token = self._get_access_token()
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "apikey": self.api_key or "",
            "transactionid": str(uuid.uuid4()),
            "requesttimestamp": self._utc_timestamp(),
        }

    def get_prices(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Default to v1 all-current prices endpoint (NSW only).
        url = f"{self.base_url.rstrip('/')}/FuelPriceCheck/v1/fuel/prices"
        response = requests.get(url, headers=self._headers(), params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_prices_v2(self, states: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/FuelPriceCheck/v2/fuel/prices"
        params = {"states": states} if states else None
        response = requests.get(url, headers=self._headers(), params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_reference_data_v1(self) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/FuelCheckRefData/v1/fuel/lovs"
        response = requests.get(url, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def get_reference_data_v2(self, states: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/FuelCheckRefData/v2/fuel/lovs"
        params = {"states": states} if states else None
        response = requests.get(url, headers=self._headers(), params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_prices_nearby_v1(
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
        url = f"{self.base_url.rstrip('/')}/FuelPriceCheck/v1/fuel/prices/nearby"
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
        response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_prices_nearby_v2(
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
        url = f"{self.base_url.rstrip('/')}/FuelPriceCheck/v2/fuel/prices/nearby"
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
        response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_station_prices_v1(self, station_code: str) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/FuelPriceCheck/v1/fuel/prices/station/{station_code}"
        response = requests.get(url, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()
