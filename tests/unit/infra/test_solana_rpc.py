"""Tests for SolanaRPCClient — JSON-RPC communication."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cryptotax.infra.blockchain.solana.rpc_client import SolanaRPCClient


@pytest.fixture()
def mock_http():
    return AsyncMock()


@pytest.fixture()
def rpc(mock_http):
    return SolanaRPCClient(rpc_url="https://api.mainnet-beta.solana.com", http_client=mock_http)


def _mock_response(data: dict):
    resp = MagicMock()
    resp.json.return_value = data
    return resp


class TestGetSignatures:
    async def test_returns_signatures(self, rpc, mock_http):
        sigs = [
            {"signature": "sig1", "slot": 100, "blockTime": 1700000000, "err": None},
            {"signature": "sig2", "slot": 101, "blockTime": 1700000001, "err": None},
        ]
        mock_http.post.return_value = _mock_response({"jsonrpc": "2.0", "id": 1, "result": sigs})

        result = await rpc.get_signatures("SomeAddress123")
        assert len(result) == 2
        assert result[0]["signature"] == "sig1"
        assert result[1]["slot"] == 101

    async def test_empty_result(self, rpc, mock_http):
        mock_http.post.return_value = _mock_response({"jsonrpc": "2.0", "id": 1, "result": []})

        result = await rpc.get_signatures("SomeAddress123")
        assert result == []

    async def test_none_result(self, rpc, mock_http):
        mock_http.post.return_value = _mock_response({"jsonrpc": "2.0", "id": 1, "result": None})

        result = await rpc.get_signatures("SomeAddress123")
        assert result == []

    async def test_pagination_params(self, rpc, mock_http):
        mock_http.post.return_value = _mock_response({"jsonrpc": "2.0", "id": 1, "result": []})

        await rpc.get_signatures("Addr", before="prevSig", limit=500)
        call_args = mock_http.post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
        params = payload["params"]
        assert params[1]["before"] == "prevSig"
        assert params[1]["limit"] == 500


class TestGetTransaction:
    async def test_returns_parsed_tx(self, rpc, mock_http):
        tx_data = {
            "transaction": {"message": {"accountKeys": [{"pubkey": "abc"}]}},
            "meta": {"fee": 5000, "preBalances": [100], "postBalances": [95]},
            "blockTime": 1700000000,
        }
        mock_http.post.return_value = _mock_response({"jsonrpc": "2.0", "id": 1, "result": tx_data})

        result = await rpc.get_transaction("someSig123")
        assert result is not None
        assert result["meta"]["fee"] == 5000

    async def test_not_found_returns_none(self, rpc, mock_http):
        mock_http.post.return_value = _mock_response({"jsonrpc": "2.0", "id": 1, "result": None})

        result = await rpc.get_transaction("missingTx")
        assert result is None


class TestGetSlot:
    async def test_returns_slot_number(self, rpc, mock_http):
        mock_http.post.return_value = _mock_response({"jsonrpc": "2.0", "id": 1, "result": 123456789})

        result = await rpc.get_slot()
        assert result == 123456789


class TestRPCErrors:
    async def test_rpc_error_raises(self, rpc, mock_http):
        """RPC errors are retried 5 times, then wrapped in tenacity.RetryError."""
        from tenacity import RetryError

        mock_http.post.return_value = _mock_response({
            "jsonrpc": "2.0", "id": 1,
            "error": {"code": -32600, "message": "Invalid request"},
        })

        with pytest.raises(RetryError):
            await rpc.get_slot()

        # Verify it retried 5 times
        assert mock_http.post.call_count == 5
