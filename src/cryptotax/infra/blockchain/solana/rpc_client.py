"""Solana JSON-RPC client — fetches transactions via getSignaturesForAddress + getTransaction."""

import logging

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from cryptotax.exceptions import ExternalServiceError
from cryptotax.infra.http.rate_limited_client import RateLimitedClient

logger = logging.getLogger(__name__)


class SolanaRPCClient:
    """Minimal Solana JSON-RPC client for transaction loading."""

    def __init__(self, rpc_url: str, http_client: RateLimitedClient) -> None:
        self._rpc_url = rpc_url
        self._http = http_client

    @retry(
        retry=retry_if_exception_type(ExternalServiceError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=3, max=30),
    )
    async def _call(self, method: str, params: list) -> dict | list | int | str | None:
        """Execute a JSON-RPC call and return the result field."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        resp = await self._http.post(self._rpc_url, json=payload)
        data = resp.json()

        if "error" in data:
            error = data["error"]
            msg = error.get("message", str(error))
            raise ExternalServiceError(f"Solana RPC error ({method}): {msg}")

        return data.get("result")

    async def get_signatures(
        self,
        address: str,
        before: str | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Fetch transaction signatures for an address.

        Returns list of {signature, slot, blockTime, err, ...} ordered newest-first.
        Uses `before` cursor for pagination.
        """
        opts: dict = {"limit": limit}
        if before is not None:
            opts["before"] = before

        result = await self._call("getSignaturesForAddress", [address, opts])
        if result is None:
            return []
        return result  # type: ignore[return-value]

    async def get_transaction(self, signature: str) -> dict | None:
        """Fetch a parsed transaction by signature.

        Uses jsonParsed encoding for human-readable token info.
        """
        opts = {
            "encoding": "jsonParsed",
            "maxSupportedTransactionVersion": 0,
        }
        result = await self._call("getTransaction", [signature, opts])
        return result  # type: ignore[return-value]

    async def get_slot(self) -> int:
        """Get current slot number."""
        result = await self._call("getSlot", [])
        return int(result)  # type: ignore[arg-type]
