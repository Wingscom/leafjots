"""PriceService — orchestrates price lookups with DB caching."""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.config import settings
from cryptotax.db.models.price_cache import PriceCache
from cryptotax.infra.price.coingecko import CoinGeckoProvider

logger = logging.getLogger(__name__)


def _round_to_hour(timestamp: int) -> int:
    """Round Unix timestamp down to the nearest hour."""
    return (timestamp // 3600) * 3600


class PriceService:
    """Price orchestrator: cache lookup → provider fetch → cache store."""

    def __init__(self, session: AsyncSession, coingecko: CoinGeckoProvider | None = None) -> None:
        self._session = session
        self._coingecko = coingecko

    async def get_price_usd(self, symbol: str, timestamp: int) -> Decimal | None:
        """Get USD price for a token at a Unix timestamp. Checks cache first."""
        hour_ts = _round_to_hour(timestamp)

        # 1. Check DB cache
        cached = await self._cache_lookup(symbol.upper(), hour_ts)
        if cached is not None:
            return cached

        # 2. Fetch from provider
        if self._coingecko is None:
            return None

        price = await self._coingecko.get_price(symbol, hour_ts)
        if price is None:
            return None

        # 3. Store in cache
        await self._cache_store(symbol.upper(), hour_ts, price, "coingecko")
        return price

    def get_usd_vnd_rate(self) -> Decimal:
        """Get USD/VND exchange rate. Uses config setting (simple approach for Phase 6)."""
        return Decimal(str(settings.usd_vnd_rate))

    async def price_split(
        self, symbol: str, quantity: Decimal, timestamp: int
    ) -> tuple[Decimal | None, Decimal | None]:
        """Calculate (value_usd, value_vnd) for a journal split."""
        price_usd = await self.get_price_usd(symbol, timestamp)
        if price_usd is None:
            return None, None

        value_usd = abs(quantity) * price_usd
        vnd_rate = self.get_usd_vnd_rate()
        value_vnd = value_usd * vnd_rate

        # Preserve sign: if quantity is negative, value is negative
        if quantity < 0:
            value_usd = -value_usd
            value_vnd = -value_vnd

        return value_usd, value_vnd

    async def _cache_lookup(self, symbol: str, hour_ts: int) -> Decimal | None:
        result = await self._session.execute(
            select(PriceCache.price_usd).where(
                PriceCache.symbol == symbol,
                PriceCache.timestamp == hour_ts,
            )
        )
        row = result.scalar_one_or_none()
        return row

    async def _cache_store(self, symbol: str, hour_ts: int, price: Decimal, source: str) -> None:
        entry = PriceCache(symbol=symbol, timestamp=hour_ts, price_usd=price, source=source)
        self._session.add(entry)
        try:
            await self._session.flush()
        except Exception:
            # Duplicate key — another request cached it first; ignore
            await self._session.rollback()
