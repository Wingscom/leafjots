"""Binance REST API client with HMAC-SHA256 authentication."""

import hashlib
import hmac
import time
from urllib.parse import urlencode

from tenacity import retry, stop_after_attempt, wait_exponential

from cryptotax.exceptions import ExternalServiceError
from cryptotax.infra.http.rate_limited_client import RateLimitedClient

BASE_URL = "https://api.binance.com"


class BinanceClient:
    """Authenticated Binance REST API client."""

    def __init__(self, api_key: str, api_secret: str, http_client: RateLimitedClient) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._http = http_client

    def _sign(self, params: dict) -> dict:
        """Add timestamp and HMAC-SHA256 signature to request params."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode(), query_string.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
    async def _request(self, method: str, path: str, params: dict | None = None, signed: bool = True) -> list | dict:
        """Make an authenticated API request."""
        params = dict(params or {})
        if signed:
            params = self._sign(params)

        url = f"{BASE_URL}{path}"
        if method == "GET":
            resp = await self._http.get(url, params=params)
        else:
            resp = await self._http.post(url, json=params)

        data = resp.json()
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise ExternalServiceError(f"Binance API error {data.get('code')}: {data.get('msg', '')}")

        return data

    async def get_spot_trades(self, symbol: str, start_time: int | None = None, limit: int = 1000) -> list[dict]:
        """GET /api/v3/myTrades — fetch trades for a single symbol."""
        params: dict = {"symbol": symbol, "limit": limit}
        if start_time is not None:
            params["startTime"] = start_time
        result = await self._request("GET", "/api/v3/myTrades", params)
        return result if isinstance(result, list) else []

    async def get_exchange_info(self) -> dict:
        """GET /api/v3/exchangeInfo — public endpoint (no auth)."""
        resp = await self._http.get(f"{BASE_URL}/api/v3/exchangeInfo")
        return resp.json()

    async def get_active_symbols(self) -> list[str]:
        """Return list of TRADING symbol names."""
        info = await self.get_exchange_info()
        return [
            s["symbol"]
            for s in info.get("symbols", [])
            if s.get("status") == "TRADING"
        ]

    async def get_all_spot_trades(self, start_time: int | None = None) -> list[dict]:
        """Fetch trades across all active trading pairs."""
        symbols = await self.get_active_symbols()
        all_trades: list[dict] = []
        for symbol in symbols:
            trades = await self.get_spot_trades(symbol, start_time=start_time)
            all_trades.extend(trades)
        return all_trades

    async def get_deposits(self, start_time: int | None = None) -> list[dict]:
        """GET /sapi/v1/capital/deposit/hisrec — deposit history."""
        params: dict = {}
        if start_time is not None:
            params["startTime"] = start_time
        result = await self._request("GET", "/sapi/v1/capital/deposit/hisrec", params)
        return result if isinstance(result, list) else []

    async def get_withdrawals(self, start_time: int | None = None) -> list[dict]:
        """GET /sapi/v1/capital/withdraw/history — withdrawal history."""
        params: dict = {}
        if start_time is not None:
            params["startTime"] = start_time
        result = await self._request("GET", "/sapi/v1/capital/withdraw/history", params)
        return result if isinstance(result, list) else []
