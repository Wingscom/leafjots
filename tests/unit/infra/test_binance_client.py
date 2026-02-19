"""Tests for BinanceClient — HMAC signing + API calls."""

import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cryptotax.infra.cex.binance_client import BinanceClient


@pytest.fixture()
def mock_http():
    return AsyncMock()


@pytest.fixture()
def client(mock_http):
    return BinanceClient(api_key="test_key", api_secret="test_secret", http_client=mock_http)


def _mock_response(data):
    resp = MagicMock()
    resp.json.return_value = data
    return resp


class TestHMACSigning:
    def test_sign_adds_timestamp_and_signature(self, client):
        params = {"symbol": "BTCUSDT", "limit": 10}
        with patch("cryptotax.infra.cex.binance_client.time") as mock_time:
            mock_time.time.return_value = 1700000000.0
            signed = client._sign(params)

        assert signed["timestamp"] == 1700000000000
        assert "signature" in signed
        # Verify HMAC-SHA256
        from urllib.parse import urlencode
        query = urlencode({"symbol": "BTCUSDT", "limit": 10, "timestamp": 1700000000000})
        expected_sig = hmac.new(b"test_secret", query.encode(), hashlib.sha256).hexdigest()
        assert signed["signature"] == expected_sig

    def test_sign_deterministic(self, client):
        """Same params + time → same signature."""
        with patch("cryptotax.infra.cex.binance_client.time") as mock_time:
            mock_time.time.return_value = 1700000000.0
            sig1 = client._sign({"a": "1"})
            mock_time.time.return_value = 1700000000.0
            sig2 = client._sign({"a": "1"})
        assert sig1["signature"] == sig2["signature"]


class TestGetSpotTrades:
    async def test_returns_trades(self, client, mock_http):
        trades = [
            {"id": 1, "symbol": "BTCUSDT", "qty": "0.5", "quoteQty": "15000", "isBuyer": True, "time": 1700000000000},
        ]
        mock_http.get.return_value = _mock_response(trades)

        result = await client.get_spot_trades("BTCUSDT")
        assert len(result) == 1
        assert result[0]["id"] == 1

    async def test_empty_result(self, client, mock_http):
        mock_http.get.return_value = _mock_response([])
        result = await client.get_spot_trades("BTCUSDT")
        assert result == []

    async def test_with_start_time(self, client, mock_http):
        mock_http.get.return_value = _mock_response([])
        await client.get_spot_trades("BTCUSDT", start_time=1700000000000)
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", call_args[0][1] if len(call_args[0]) > 1 else {})
        assert params["startTime"] == 1700000000000


class TestGetDeposits:
    async def test_returns_deposits(self, client, mock_http):
        deposits = [
            {"txId": "abc123", "coin": "ETH", "amount": "1.5", "insertTime": 1700000000000},
        ]
        mock_http.get.return_value = _mock_response(deposits)

        result = await client.get_deposits()
        assert len(result) == 1
        assert result[0]["coin"] == "ETH"


class TestGetWithdrawals:
    async def test_returns_withdrawals(self, client, mock_http):
        withdrawals = [
            {"id": "wd1", "coin": "BTC", "amount": "0.1", "transactionFee": "0.0005", "applyTime": "2024-01-01T00:00:00Z"},
        ]
        mock_http.get.return_value = _mock_response(withdrawals)

        result = await client.get_withdrawals()
        assert len(result) == 1
        assert result[0]["coin"] == "BTC"


class TestAPIErrors:
    async def test_api_error_raises(self, client, mock_http):
        from cryptotax.exceptions import ExternalServiceError

        mock_http.get.return_value = _mock_response({"code": -1000, "msg": "Unknown error"})

        with pytest.raises(ExternalServiceError, match="Unknown error"):
            await client.get_spot_trades("BTCUSDT")

        assert mock_http.get.call_count == 3
