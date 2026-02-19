"""Tests for CoinGeckoProvider with mocked HTTP."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from cryptotax.infra.price.coingecko import CoinGeckoProvider, SYMBOL_TO_COINGECKO


class TestCoinGeckoProvider:
    def test_symbol_mapping_coverage(self):
        assert "ETH" in SYMBOL_TO_COINGECKO
        assert "BTC" in SYMBOL_TO_COINGECKO
        assert "USDC" in SYMBOL_TO_COINGECKO
        assert "WETH" in SYMBOL_TO_COINGECKO

    @pytest.mark.asyncio
    async def test_stablecoin_returns_one(self):
        mock_http = MagicMock()
        provider = CoinGeckoProvider(http_client=mock_http)

        price = await provider.get_price("USDC", 1700000000)
        assert price == Decimal("1.0")

        price = await provider.get_price("USDT", 1700000000)
        assert price == Decimal("1.0")

        price = await provider.get_price("DAI", 1700000000)
        assert price == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_unknown_symbol_returns_none(self):
        mock_http = MagicMock()
        provider = CoinGeckoProvider(http_client=mock_http)

        price = await provider.get_price("UNKNOWN_TOKEN_XYZ", 1700000000)
        assert price is None

    @pytest.mark.asyncio
    async def test_successful_price_fetch(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "prices": [
                [1700000000000, 2050.25],
                [1700003600000, 2055.50],
            ]
        }

        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        provider = CoinGeckoProvider(http_client=mock_http)

        price = await provider.get_price("ETH", 1700000000)
        assert price is not None
        assert price == Decimal("2050.25")

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        mock_response = MagicMock()
        mock_response.status_code = 429

        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        provider = CoinGeckoProvider(http_client=mock_http)

        price = await provider.get_price("ETH", 1700000000)
        assert price is None

    @pytest.mark.asyncio
    async def test_empty_prices_returns_none(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"prices": []}

        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        provider = CoinGeckoProvider(http_client=mock_http)

        price = await provider.get_price("ETH", 1700000000)
        assert price is None
