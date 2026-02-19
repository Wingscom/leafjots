"""Etherscan v2 unified API client for all EVM chains."""

import logging
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from cryptotax.exceptions import ExternalServiceError
from cryptotax.infra.http.rate_limited_client import RateLimitedClient

logger = logging.getLogger(__name__)

# Etherscan v2 uses a single base URL + chainid param
BASE_URL = "https://api.etherscan.io/v2/api"

CHAIN_IDS: dict[str, int] = {
    "ethereum": 1,
    "arbitrum": 42161,
    "optimism": 10,
    "polygon": 137,
    "base": 8453,
    "bsc": 56,
    "avalanche": 43114,
}

MAX_RESULTS = 10_000  # Etherscan max results per call


class EtherscanClient:
    def __init__(self, api_key: str, chain: str, http_client: RateLimitedClient) -> None:
        if chain not in CHAIN_IDS:
            raise ValueError(f"Unsupported chain: {chain}")
        self._api_key = api_key
        self._chain = chain
        self._chain_id = CHAIN_IDS[chain]
        self._http = http_client

    @retry(
        retry=retry_if_exception_type(ExternalServiceError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _call(self, params: dict[str, Any]) -> list[dict]:
        params = {**params, "apikey": self._api_key, "chainid": self._chain_id}
        resp = await self._http.get(BASE_URL, params=params)
        data = resp.json()

        status = data.get("status")
        message = data.get("message", "")
        result = data.get("result")

        # "No transactions found" is valid empty result
        if message == "No transactions found" or (status == "0" and result == []):
            return []

        # Rate limit or server error → retriable
        if message == "NOTOK" or status is None:
            raise ExternalServiceError(f"Etherscan error: {data.get('result', message)}")

        if status == "0":
            error_msg = result if isinstance(result, str) else message
            raise ExternalServiceError(f"Etherscan API error: {error_msg}")

        if not isinstance(result, list):
            return []

        return result

    async def get_transactions(
        self, address: str, from_block: int = 0, to_block: int = 99999999
    ) -> list[dict]:
        """Fetch normal transactions with recursive 10K splitting."""
        return await self._fetch_with_split(
            module="account",
            action="txlist",
            address=address,
            from_block=from_block,
            to_block=to_block,
        )

    async def get_internal_transactions(
        self, address: str, from_block: int = 0, to_block: int = 99999999
    ) -> list[dict]:
        return await self._fetch_with_split(
            module="account",
            action="txlistinternal",
            address=address,
            from_block=from_block,
            to_block=to_block,
        )

    async def get_erc20_transfers(
        self, address: str, from_block: int = 0, to_block: int = 99999999
    ) -> list[dict]:
        return await self._fetch_with_split(
            module="account",
            action="tokentx",
            address=address,
            from_block=from_block,
            to_block=to_block,
        )

    async def get_latest_block(self) -> int:
        """Get latest block number. Uses proxy endpoint which returns hex, not the standard list format."""
        params = {
            "module": "proxy",
            "action": "eth_blockNumber",
            "apikey": self._api_key,
            "chainid": self._chain_id,
        }
        resp = await self._http.get(BASE_URL, params=params)
        data = resp.json()
        result = data.get("result", "0x0")
        if isinstance(result, str) and result.startswith("0x"):
            return int(result, 16)
        return int(result)

    async def _fetch_with_split(
        self,
        module: str,
        action: str,
        address: str,
        from_block: int,
        to_block: int,
    ) -> list[dict]:
        """Recursive fetch with 10K result splitting."""
        params = {
            "module": module,
            "action": action,
            "address": address,
            "startblock": from_block,
            "endblock": to_block,
            "sort": "asc",
        }
        results = await self._call(params)

        if len(results) < MAX_RESULTS:
            return results

        # Hit the 10K limit — split block range in half and recurse
        mid_block = (from_block + to_block) // 2
        if mid_block == from_block:
            logger.warning(
                "Cannot split further at block %d for %s/%s — returning partial results",
                from_block, action, address,
            )
            return results

        logger.info(
            "Splitting %s range [%d, %d] at %d for address %s",
            action, from_block, to_block, mid_block, address,
        )
        first_half = await self._fetch_with_split(module, action, address, from_block, mid_block)
        second_half = await self._fetch_with_split(module, action, address, mid_block + 1, to_block)
        return first_half + second_half
