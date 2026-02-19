import asyncio
import time

import httpx


class RateLimitedClient:
    """Async HTTP client with simple interval-based rate limiting."""

    def __init__(self, rate_per_second: float = 5.0, timeout: float = 30.0) -> None:
        self._min_interval = 1.0 / rate_per_second
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _wait_for_slot(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()

    async def get(self, url: str, params: dict | None = None) -> httpx.Response:
        await self._wait_for_slot()
        return await self._client.get(url, params=params)

    async def post(self, url: str, json: dict | list | None = None) -> httpx.Response:
        await self._wait_for_slot()
        return await self._client.post(url, json=json)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "RateLimitedClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
