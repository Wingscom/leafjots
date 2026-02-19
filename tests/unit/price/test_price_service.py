"""Tests for PriceService — cache hit/miss behavior."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from cryptotax.db.models.price_cache import PriceCache
from cryptotax.infra.price.service import PriceService, _round_to_hour


class TestRoundToHour:
    def test_exact_hour(self):
        assert _round_to_hour(1700000000) == 1699999200  # Rounds down

    def test_mid_hour(self):
        ts = 1700000000 + 1800  # 30 min after
        assert _round_to_hour(ts) == 1699999200  # Still in the same hour bucket

    def test_zero(self):
        assert _round_to_hour(0) == 0


class TestPriceServiceCacheHit:
    async def test_cache_hit_returns_price(self, session):
        # Pre-populate cache
        session.add(PriceCache(symbol="ETH", timestamp=1699999200, price_usd=Decimal("2000"), source="coingecko"))
        await session.flush()

        service = PriceService(session, coingecko=None)
        price = await service.get_price_usd("ETH", 1700000000)  # rounds to 1699999200
        assert price == Decimal("2000")

    async def test_cache_miss_no_provider_returns_none(self, session):
        service = PriceService(session, coingecko=None)
        price = await service.get_price_usd("ETH", 1700000000)
        assert price is None


class TestPriceServiceFetch:
    async def test_cache_miss_fetches_and_stores(self, session):
        mock_coingecko = MagicMock()
        mock_coingecko.get_price = AsyncMock(return_value=Decimal("2500"))

        service = PriceService(session, coingecko=mock_coingecko)
        price = await service.get_price_usd("ETH", 1700000000)

        assert price == Decimal("2500")
        mock_coingecko.get_price.assert_called_once()

        # Verify it was cached
        price2 = await service.get_price_usd("ETH", 1700000000)
        assert price2 == Decimal("2500")
        # Should NOT call provider again (cache hit)
        assert mock_coingecko.get_price.call_count == 1


class TestPriceSplit:
    async def test_price_split_positive_quantity(self, session):
        session.add(PriceCache(symbol="ETH", timestamp=1699999200, price_usd=Decimal("2000"), source="test"))
        await session.flush()

        service = PriceService(session)
        value_usd, value_vnd = await service.price_split("ETH", Decimal("1.5"), 1700000000)

        assert value_usd == Decimal("3000")  # 1.5 * 2000
        assert value_vnd == Decimal("75000000")  # 3000 * 25000

    async def test_price_split_negative_quantity(self, session):
        session.add(PriceCache(symbol="ETH", timestamp=1699999200, price_usd=Decimal("2000"), source="test"))
        await session.flush()

        service = PriceService(session)
        value_usd, value_vnd = await service.price_split("ETH", Decimal("-1.5"), 1700000000)

        assert value_usd == Decimal("-3000")
        assert value_vnd == Decimal("-75000000")

    async def test_price_split_no_price_returns_none(self, session):
        service = PriceService(session)
        value_usd, value_vnd = await service.price_split("UNKNOWN", Decimal("1"), 1700000000)
        assert value_usd is None
        assert value_vnd is None
