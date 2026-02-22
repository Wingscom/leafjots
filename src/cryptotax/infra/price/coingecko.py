"""CoinGecko price provider — fetches historical token prices in USD."""

import asyncio
import logging
from decimal import Decimal

from cryptotax.infra.http.rate_limited_client import RateLimitedClient

logger = logging.getLogger(__name__)

# Common symbol → CoinGecko ID mapping
SYMBOL_TO_COINGECKO: dict[str, str] = {
    # Major tokens
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
    "DOGE": "dogecoin",
    "SHIB": "shiba-inu",
    "PEPE": "pepe",
    "WLD": "worldcoin-wld",
    "FET": "fetch-ai",
    "ENA": "ethena",
    "GHO": "gho",
    "RAIL": "railgun",
    "EIGEN": "eigenlayer",
    "LIT": "litentry",
    "SPK": "sparkdex",
    "STSPK": "sparkdex",
    "ATH": "aethir",
    "ANKR": "ankr",
    "BCH": "bitcoin-cash",
    "FLOW": "flow",
    "SOLV": "solv-protocol",
    "WBETH": "wrapped-beacon-ether",
    "XRP": "ripple",
    "BTTC": "bittorrent-2",
    "WAXP": "wax",
    "ZBT": "zerobridge-bitcoin",
    # Staked / wrapped variants
    "STEAKETH": "ethereum",
    "STEAKUSDC": "usd-coin",
    "GTWETH": "ethereum",
    "GTUSDC": "usd-coin",
    # Aave v3 receipt tokens (≈ 1:1 underlying)
    "AETHWETH": "ethereum",
    "AETHWBTC": "bitcoin",
    "AETHUSDC": "usd-coin",
    "AETHUSDT": "tether",
    "AETHDAI": "dai",
    "AETHLIDOWETH": "ethereum",
    # Spark protocol receipt tokens
    "SPWETH": "ethereum",
    "SPDAI": "dai",
    # Compound v3 receipt tokens
    "CWETHV3": "ethereum",
    "CUSDCV3": "usd-coin",
}


def _resolve_coingecko_id(symbol: str) -> str | None:
    """Resolve a token symbol to a CoinGecko ID, with auto-detection for protocol receipt tokens."""
    upper = symbol.upper()

    # 1. Direct static mapping (covers most tokens)
    if upper in SYMBOL_TO_COINGECKO:
        return SYMBOL_TO_COINGECKO[upper]

    # 2. Aave v3 receipt tokens: aEth{TOKEN} → underlying
    if upper.startswith("AETH"):
        underlying = upper[4:]
        return SYMBOL_TO_COINGECKO.get(underlying) or SYMBOL_TO_COINGECKO.get("W" + underlying)

    # 3. Compound v3: c{TOKEN}v3 → underlying
    if upper.startswith("C") and upper.endswith("V3"):
        underlying = upper[1:-2]
        return SYMBOL_TO_COINGECKO.get(underlying) or SYMBOL_TO_COINGECKO.get("W" + underlying)

    # 4. Spark: sp{TOKEN} → underlying
    if upper.startswith("SP") and len(upper) > 2:
        underlying = upper[2:]
        return SYMBOL_TO_COINGECKO.get(underlying) or SYMBOL_TO_COINGECKO.get("W" + underlying)

    # 5. Staked tokens: st{TOKEN} → underlying (e.g. stSPK → sparkdex)
    if upper.startswith("ST") and len(upper) > 2 and upper not in ("STETH",):
        underlying = upper[2:]
        result = SYMBOL_TO_COINGECKO.get(underlying) or SYMBOL_TO_COINGECKO.get("W" + underlying)
        if result:
            return result

    # 6. Aave debt tokens: variableDebt*, stableDebt* — skip pricing
    if "DEBT" in upper:
        return None

    logger.warning("No CoinGecko ID mapping for symbol: %s", symbol)
    return None

# Stablecoins that are always $1
STABLECOINS = {"USDC", "USDT", "DAI", "FRAX", "USDS", "BUSD", "TUSD", "LUSD", "GUSD", "PYUSD", "USD1", "BFUSD", "RWUSD"}

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

        coingecko_id = _resolve_coingecko_id(symbol)
        if coingecko_id is None:
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
