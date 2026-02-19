"""CoinGecko price provider — fetches historical token prices in USD."""

import asyncio
import logging
from decimal import Decimal

from cryptotax.infra.http.rate_limited_client import RateLimitedClient

logger = logging.getLogger(__name__)

# Common symbol → CoinGecko ID mapping
SYMBOL_TO_COINGECKO: dict[str, str] = {
    "ETH": "ethereum",
    "BTC": "bitcoin",
    "WETH": "ethereum",
    "WBTC": "bitcoin",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
    "FRAX": "frax",
    "USDS": "usds",
    "MATIC": "matic-network",
    "BNB": "binancecoin",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "AAVE": "aave",
    "CRV": "curve-dao-token",
    "MKR": "maker",
    "COMP": "compound-governance-token",
    "SNX": "havven",
    "SUSHI": "sushi",
    "1INCH": "1inch",
    "stETH": "staked-ether",
    "wstETH": "wrapped-steth",
    "rETH": "rocket-pool-eth",
    "cbETH": "coinbase-wrapped-staked-eth",
    "frxETH": "frax-ether",
    "SOL": "solana",
    "WSOL": "solana",
    "RAY": "raydium",
    "JUP": "jupiter-exchange-solana",
    "BONK": "bonk",
    "GRT": "the-graph",
    "LDO": "lido-dao",
    "RPL": "rocket-pool",
    "PENDLE": "pendle",
    "ARB": "arbitrum",
    "OP": "optimism",
}

# Stablecoins that are always $1
STABLECOINS = {"USDC", "USDT", "DAI", "FRAX", "USDS", "BUSD", "TUSD", "LUSD", "GUSD", "PYUSD"}

BASE_URL = "https://api.coingecko.com"

MAX_RETRIES = 3


class CoinGeckoProvider:
    """Fetch historical USD prices from CoinGecko API with rate-limit retry."""

    def __init__(self, http_client: RateLimitedClient, api_key: str = "") -> None:
        self._http = http_client
        self._api_key = api_key

    async def get_price(self, symbol: str, timestamp: int) -> Decimal | None:
        """Get USD price for a token at a specific Unix timestamp.

        Uses /coins/{id}/market_chart/range with a 2-hour window around the timestamp.
        Returns the closest price point, or None if not found.
        Retries with exponential backoff on 429 rate limit.
        """
        upper = symbol.upper()

        # Stablecoins: shortcut
        if upper in STABLECOINS:
            return Decimal("1.0")

        coingecko_id = SYMBOL_TO_COINGECKO.get(upper)
        if coingecko_id is None:
            logger.warning("No CoinGecko ID mapping for symbol: %s", symbol)
            return None

        # Query a 2-hour window around the target timestamp
        from_ts = timestamp - 3600
        to_ts = timestamp + 3600

        params: dict[str, str] = {
            "vs_currency": "usd",
            "from": str(from_ts),
            "to": str(to_ts),
        }
        if self._api_key:
            params["x_cg_demo_api_key"] = self._api_key

        url = f"{BASE_URL}/api/v3/coins/{coingecko_id}/market_chart/range"

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._http.get(url, params=params)

                if response.status_code == 429:
                    wait = 2 ** (attempt + 1)  # 2, 4, 8 seconds
                    logger.info("CoinGecko 429 rate limit for %s, waiting %ds...", symbol, wait)
                    await asyncio.sleep(wait)
                    continue

                if response.status_code != 200:
                    logger.warning("CoinGecko returned %d for %s", response.status_code, symbol)
                    return None

                data = response.json()
                prices = data.get("prices", [])
                if not prices:
                    return None

                # Find closest price to target timestamp
                target_ms = timestamp * 1000
                closest = min(prices, key=lambda p: abs(p[0] - target_ms))
                return Decimal(str(closest[1]))

            except Exception:
                logger.exception("CoinGecko price fetch failed for %s (attempt %d)", symbol, attempt + 1)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)

        logger.warning("CoinGecko exhausted retries for %s", symbol)
        return None
