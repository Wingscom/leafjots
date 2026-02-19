"""Tests for PriceCache DB model."""

from decimal import Decimal

from sqlalchemy import select

from cryptotax.db.models.price_cache import PriceCache


class TestPriceCache:
    async def test_create_and_read(self, session):
        entry = PriceCache(symbol="ETH", timestamp=1700000000, price_usd=Decimal("2000.50"), source="coingecko")
        session.add(entry)
        await session.flush()

        result = await session.execute(select(PriceCache).where(PriceCache.symbol == "ETH"))
        cached = result.scalar_one()
        assert cached.price_usd == Decimal("2000.50")
        assert cached.source == "coingecko"
        assert cached.timestamp == 1700000000

    async def test_multiple_symbols(self, session):
        session.add(PriceCache(symbol="ETH", timestamp=1700000000, price_usd=Decimal("2000"), source="coingecko"))
        session.add(PriceCache(symbol="BTC", timestamp=1700000000, price_usd=Decimal("35000"), source="coingecko"))
        await session.flush()

        result = await session.execute(select(PriceCache))
        all_prices = result.scalars().all()
        assert len(all_prices) == 2

    async def test_different_timestamps(self, session):
        session.add(PriceCache(symbol="ETH", timestamp=1700000000, price_usd=Decimal("2000"), source="coingecko"))
        session.add(PriceCache(symbol="ETH", timestamp=1700003600, price_usd=Decimal("2010"), source="coingecko"))
        await session.flush()

        result = await session.execute(
            select(PriceCache).where(PriceCache.symbol == "ETH").order_by(PriceCache.timestamp)
        )
        prices = result.scalars().all()
        assert len(prices) == 2
        assert prices[0].price_usd == Decimal("2000")
        assert prices[1].price_usd == Decimal("2010")
