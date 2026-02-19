"""Tests for Binance CEX parsers — Trade, Deposit, Withdrawal."""

from decimal import Decimal

import pytest

from cryptotax.parser.cex.binance import (
    BinanceDepositParser,
    BinanceTradeParser,
    BinanceWithdrawalParser,
    _parse_pair,
)
from cryptotax.parser.utils.context import TransactionContext


@pytest.fixture()
def empty_context():
    return TransactionContext(transfers=[], wallet_addresses=set())


class TestParsePair:
    def test_btcusdt(self):
        assert _parse_pair("BTCUSDT") == ("BTC", "USDT")

    def test_ethbtc(self):
        assert _parse_pair("ETHBTC") == ("ETH", "BTC")

    def test_solusdc(self):
        assert _parse_pair("SOLUSDC") == ("SOL", "USDC")

    def test_bnbeth(self):
        assert _parse_pair("BNBETH") == ("BNB", "ETH")

    def test_short_symbol(self):
        base, quote = _parse_pair("XY")
        # Falls through to fallback
        assert isinstance(base, str)
        assert isinstance(quote, str)


class TestBinanceTradeParser:
    def test_can_parse_trade(self, empty_context):
        parser = BinanceTradeParser()
        tx_data = {"chain": "binance", "symbol": "BTCUSDT", "qty": "0.5", "quoteQty": "15000"}
        assert parser.can_parse(tx_data, empty_context) is True

    def test_cannot_parse_non_binance(self, empty_context):
        parser = BinanceTradeParser()
        tx_data = {"chain": "ethereum", "symbol": "BTCUSDT", "qty": "0.5", "quoteQty": "15000"}
        assert parser.can_parse(tx_data, empty_context) is False

    def test_cannot_parse_without_trade_fields(self, empty_context):
        parser = BinanceTradeParser()
        tx_data = {"chain": "binance", "coin": "ETH", "amount": "1.0"}
        assert parser.can_parse(tx_data, empty_context) is False

    def test_parse_buy_trade(self, empty_context):
        parser = BinanceTradeParser()
        tx_data = {
            "chain": "binance",
            "symbol": "BTCUSDT",
            "qty": "0.5",
            "quoteQty": "15000",
            "isBuyer": True,
            "commission": "0.001",
            "commissionAsset": "BTC",
        }
        result = parser.parse(tx_data, empty_context)
        splits = result.splits

        # 4 splits: BTC +0.5 (asset), USDT -15000 (asset), BTC -0.001 (fee from asset), BTC +0.001 (expense)
        assert len(splits) == 4

        # Check cex_asset splits
        cex_splits = [s for s in splits if s.account_subtype == "cex_asset"]
        btc_cex = [s for s in cex_splits if s.symbol == "BTC"]
        usdt_cex = [s for s in cex_splits if s.symbol == "USDT"]

        assert sum(s.quantity for s in btc_cex) == Decimal("0.499")  # +0.5 - 0.001
        assert sum(s.quantity for s in usdt_cex) == Decimal("-15000")

        # Fee expense split
        expense_splits = [s for s in splits if s.account_subtype == "wallet_expense"]
        assert len(expense_splits) == 1
        assert expense_splits[0].symbol == "BTC"
        assert expense_splits[0].quantity == Decimal("0.001")

    def test_parse_sell_trade(self, empty_context):
        parser = BinanceTradeParser()
        tx_data = {
            "chain": "binance",
            "symbol": "ETHUSDT",
            "qty": "2.0",
            "quoteQty": "5000",
            "isBuyer": False,
            "commission": "5.0",
            "commissionAsset": "USDT",
        }
        result = parser.parse(tx_data, empty_context)
        splits = result.splits

        # 4 splits: ETH -2 (asset), USDT +5000 (asset), USDT -5 (fee from asset), USDT +5 (expense)
        assert len(splits) == 4

        cex_splits = [s for s in splits if s.account_subtype == "cex_asset"]
        eth_cex = [s for s in cex_splits if s.symbol == "ETH"]
        usdt_cex = [s for s in cex_splits if s.symbol == "USDT"]

        assert sum(s.quantity for s in eth_cex) == Decimal("-2.0")
        assert sum(s.quantity for s in usdt_cex) == Decimal("4995")  # +5000 - 5

        expense_splits = [s for s in splits if s.account_subtype == "wallet_expense"]
        assert len(expense_splits) == 1
        assert expense_splits[0].symbol == "USDT"
        assert expense_splits[0].quantity == Decimal("5.0")

    def test_parse_trade_no_fee(self, empty_context):
        parser = BinanceTradeParser()
        tx_data = {
            "chain": "binance",
            "symbol": "BTCUSDT",
            "qty": "1.0",
            "quoteQty": "30000",
            "isBuyer": True,
            "commission": "0",
            "commissionAsset": "BTC",
        }
        result = parser.parse(tx_data, empty_context)
        # 2 splits (no fee splits since commission=0)
        assert len(result.splits) == 2

    def test_parse_trade_csv_format(self, empty_context):
        """CSV-imported trades use 'side' instead of 'isBuyer'."""
        parser = BinanceTradeParser()
        tx_data = {
            "chain": "binance",
            "symbol": "BTCUSDT",
            "qty": "0.5",
            "quoteQty": "15000",
            "side": "BUY",
            "commission": "0.001",
            "commissionAsset": "BTC",
        }
        result = parser.parse(tx_data, empty_context)
        # Should parse as buy
        cex_splits = [s for s in result.splits if s.account_subtype == "cex_asset"]
        btc_cex = [s for s in cex_splits if s.symbol == "BTC"]
        assert any(s.quantity > 0 for s in btc_cex)  # Bought BTC


class TestBinanceDepositParser:
    def test_can_parse_deposit(self, empty_context):
        parser = BinanceDepositParser()
        tx_data = {"chain": "binance", "depositOrderId": "dep123", "coin": "ETH", "amount": "1.0"}
        assert parser.can_parse(tx_data, empty_context) is True

    def test_can_parse_deposit_alt(self, empty_context):
        parser = BinanceDepositParser()
        tx_data = {"chain": "binance", "txId": "abc", "insertTime": 1700000000000, "coin": "ETH", "amount": "1.0"}
        assert parser.can_parse(tx_data, empty_context) is True

    def test_cannot_parse_trade(self, empty_context):
        parser = BinanceDepositParser()
        tx_data = {"chain": "binance", "symbol": "BTCUSDT", "qty": "0.5", "quoteQty": "15000"}
        assert parser.can_parse(tx_data, empty_context) is False

    def test_parse_deposit(self, empty_context):
        parser = BinanceDepositParser()
        tx_data = {
            "chain": "binance",
            "depositOrderId": "dep123",
            "coin": "ETH",
            "amount": "1.5",
            "address": "0xabc",
        }
        result = parser.parse(tx_data, empty_context)
        assert len(result.splits) == 2

        by_symbol = {}
        for s in result.splits:
            by_symbol.setdefault(s.symbol, Decimal(0))
            by_symbol[s.symbol] += s.quantity
        assert by_symbol["ETH"] == Decimal(0)


class TestBinanceWithdrawalParser:
    def test_can_parse_withdrawal(self, empty_context):
        parser = BinanceWithdrawalParser()
        tx_data = {
            "chain": "binance",
            "withdrawOrderId": "wd123",
            "coin": "BTC",
            "amount": "0.1",
            "transactionFee": "0.0005",
        }
        assert parser.can_parse(tx_data, empty_context) is True

    def test_can_parse_withdrawal_alt(self, empty_context):
        parser = BinanceWithdrawalParser()
        tx_data = {
            "chain": "binance",
            "applyTime": "2024-01-01",
            "transactionFee": "0.001",
            "coin": "ETH",
            "amount": "1.0",
        }
        assert parser.can_parse(tx_data, empty_context) is True

    def test_cannot_parse_deposit(self, empty_context):
        parser = BinanceWithdrawalParser()
        tx_data = {"chain": "binance", "depositOrderId": "dep1", "coin": "ETH", "amount": "1.0"}
        assert parser.can_parse(tx_data, empty_context) is False

    def test_parse_withdrawal(self, empty_context):
        parser = BinanceWithdrawalParser()
        tx_data = {
            "chain": "binance",
            "withdrawOrderId": "wd1",
            "coin": "BTC",
            "amount": "0.1",
            "transactionFee": "0.0005",
            "address": "bc1qxyz",
        }
        result = parser.parse(tx_data, empty_context)
        assert len(result.splits) == 3  # cex_asset, external_transfer, expense

        by_symbol = {}
        for s in result.splits:
            by_symbol.setdefault(s.symbol, Decimal(0))
            by_symbol[s.symbol] += s.quantity
        assert by_symbol["BTC"] == Decimal(0)

    def test_parse_withdrawal_no_fee(self, empty_context):
        parser = BinanceWithdrawalParser()
        tx_data = {
            "chain": "binance",
            "withdrawOrderId": "wd2",
            "coin": "USDT",
            "amount": "100",
            "transactionFee": "0",
        }
        result = parser.parse(tx_data, empty_context)
        assert len(result.splits) == 2  # No fee split

        by_symbol = {}
        for s in result.splits:
            by_symbol.setdefault(s.symbol, Decimal(0))
            by_symbol[s.symbol] += s.quantity
        assert by_symbol["USDT"] == Decimal(0)
