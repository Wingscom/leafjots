"""CryptoCompare price provider — fallback for historical token prices."""

import asyncio
import logging
from decimal import Decimal

from cryptotax.infra.http.rate_limited_client import RateLimitedClient

logger = logging.getLogger(__name__)

BASE_URL = "https://min-api.cryptocompare.com"

# CryptoCompare uses standard symbols (ETH, BTC, etc.)
# Map protocol receipt tokens to their underlying symbol.
SYMBOL_OVERRIDES: dict[str, str] = {
    "WETH": "ETH",
    "WBTC": "BTC",
    "WSOL": "SOL",
    "WBETH": "ETH",
    "STETH": "ETH",
    "WSTETH": "ETH",
    "RETH": "ETH",
    "CBETH": "ETH",
    "FRXETH": "ETH",
}

MAX_RETRIES = 3


def _resolve_cc_symbol(symbol: str) -> str | None:
    """Resolve a token symbol to CryptoCompare's expected symbol."""
    upper = symbol.upper()

    # Direct overrides
    if upper in SYMBOL_OVERRIDES:
        return SYMBOL_OVERRIDES[upper]

    # Aave v3 receipt tokens: aEth{TOKEN} → underlying
    if upper.startswith("AETH"):
        underlying = upper[4:]
        if underlying.startswith("W"):
            underlying = underlying[1:]
        if underlying.startswith("LIDO"):
            return "ETH"
        return underlying or None

    # Compound v3: c{TOKEN}v3 → underlying
    if upper.startswith("C") and upper.endswith("V3"):
        underlying = upper[1:-2]
        if underlying.startswith("W"):
            underlying = underlying[1:]
        return underlying or None

    # Spark: sp{TOKEN} → underlying
    if upper.startswith("SP") and len(upper) > 2:
        underlying = upper[2:]
        if underlying.startswith("W"):
            underlying = underlying[1:]
        return underlying or None

    # Staked tokens: st{TOKEN} → underlying
    if upper.startswith("ST") and len(upper) > 2:
        underlying = upper[2:]
        if underlying.startswith("W"):
            underlying = underlying[1:]
        return underlying or None

    # Debt tokens — skip
    if "DEBT" in upper:
        return None

    # Use symbol as-is (CryptoCompare knows most major tokens)
    return upper


class CryptoCompareProvider:
    """Fetch historical USD prices from CryptoCompare free API."""

    def __init__(self, http_client: RateLimitedClient, api_key: str = "") -> None:
        self._http = http_client
        self._api_key = api_key

    async def get_price(self, symbol: str, timestamp: int) -> Decimal | None:
        """Get USD price for a token at a specific Unix timestamp.

        Uses /data/v2/histohour to get the hourly close price nearest to the timestamp.
        """
        cc_symbol = _resolve_cc_symbol(symbol)
        if cc_symbol is None:
            return None

        params: dict[str, str] = {
            "fsym": cc_symbol,
            "tsym": "USD",
            "limit": "1",
            "toTs": str(timestamp),
        }
        if self._api_key:
            params["api_key"] = self._api_key

        url = f"{BASE_URL}/data/v2/histohour"

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._http.get(url, params=params)

                if response.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    logger.info("CryptoCompare 429 rate limit for %s, waiting %ds...", symbol, wait)
                    await asyncio.sleep(wait)
                    continue

                if response.status_code != 200:
                    logger.warning("CryptoCompare returned %d for %s", response.status_code, symbol)
                    return None

                data = response.json()
                points = data.get("Data", {}).get("Data", [])
                if not points:
                    return None

                # Use the last data point (closest to toTs)
                closest = points[-1]
                close_price = closest.get("close", 0)
                if close_price <= 0:
                    return None

                return Decimal(str(close_price))

            except Exception:
                logger.exception("CryptoCompare price fetch failed for %s (attempt %d)", symbol, attempt + 1)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)

        logger.warning("CryptoCompare exhausted retries for %s", symbol)
        return None
