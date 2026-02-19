"""Tests for ERC20 transfer extraction and extract_all_transfers."""

from cryptotax.parser.utils.transfers import (
    extract_all_transfers,
    extract_erc20_transfers,
)


class TestExtractErc20Transfers:
    def test_basic_erc20_transfer(self):
        token_txs = [
            {
                "contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "tokenSymbol": "USDC",
                "tokenDecimal": "6",
                "from": "0xWallet",
                "to": "0xPool",
                "value": "1000000000",
            }
        ]
        result = extract_erc20_transfers(token_txs)
        assert len(result) == 1
        t = result[0]
        assert t.symbol == "USDC"
        assert t.decimals == 6
        assert t.value == 1_000_000_000
        assert t.transfer_type == "erc20"
        assert t.from_address == "0xwallet"
        assert t.to_address == "0xpool"

    def test_multiple_transfers(self):
        token_txs = [
            {"contractAddress": "0xusdc", "tokenSymbol": "USDC", "tokenDecimal": "6", "from": "0xa", "to": "0xb", "value": "1000"},
            {"contractAddress": "0xdai", "tokenSymbol": "DAI", "tokenDecimal": "18", "from": "0xb", "to": "0xa", "value": "2000"},
        ]
        result = extract_erc20_transfers(token_txs)
        assert len(result) == 2
        assert result[0].symbol == "USDC"
        assert result[1].symbol == "DAI"

    def test_zero_value_skipped(self):
        token_txs = [
            {"contractAddress": "0xusdc", "tokenSymbol": "USDC", "tokenDecimal": "6", "from": "0xa", "to": "0xb", "value": "0"},
        ]
        result = extract_erc20_transfers(token_txs)
        assert len(result) == 0

    def test_empty_list(self):
        assert extract_erc20_transfers([]) == []

    def test_missing_fields_use_defaults(self):
        token_txs = [{"value": "500"}]
        result = extract_erc20_transfers(token_txs)
        assert len(result) == 1
        assert result[0].symbol == "UNKNOWN"
        assert result[0].decimals == 18


class TestExtractAllTransfers:
    def test_native_only(self):
        tx_data = {
            "from": "0xwallet",
            "to": "0xother",
            "value": "1000000000000000000",
        }
        result = extract_all_transfers(tx_data, "ethereum")
        assert len(result) == 1
        assert result[0].transfer_type == "native"
        assert result[0].symbol == "ETH"

    def test_erc20_only(self):
        tx_data = {
            "from": "0xwallet",
            "to": "0xother",
            "value": "0",
            "token_transfers": [
                {"contractAddress": "0xusdc", "tokenSymbol": "USDC", "tokenDecimal": "6", "from": "0xwallet", "to": "0xpool", "value": "5000000"},
            ],
        }
        result = extract_all_transfers(tx_data, "ethereum")
        assert len(result) == 1
        assert result[0].transfer_type == "erc20"
        assert result[0].symbol == "USDC"

    def test_native_plus_erc20(self):
        tx_data = {
            "from": "0xwallet",
            "to": "0xrouter",
            "value": "1000000000000000000",
            "token_transfers": [
                {"contractAddress": "0xusdc", "tokenSymbol": "USDC", "tokenDecimal": "6", "from": "0xrouter", "to": "0xwallet", "value": "2500000000"},
            ],
        }
        result = extract_all_transfers(tx_data, "ethereum")
        assert len(result) == 2
        assert result[0].transfer_type == "native"
        assert result[1].transfer_type == "erc20"

    def test_no_token_transfers_key(self):
        tx_data = {"from": "0xa", "to": "0xb", "value": "0"}
        result = extract_all_transfers(tx_data, "ethereum")
        assert len(result) == 0

    def test_polygon_native_symbol(self):
        tx_data = {"from": "0xa", "to": "0xb", "value": "1000000000000000000"}
        result = extract_all_transfers(tx_data, "polygon")
        assert len(result) == 1
        assert result[0].symbol == "MATIC"
