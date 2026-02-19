"""Tests for FIFO lot matching algorithm — pure functions."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from cryptotax.accounting.fifo import fifo_match, trades_from_splits
from cryptotax.domain.enums.tax import TradeSide
from cryptotax.domain.models.tax import Trade


def _trade(side: str, qty: str, price: str, days_offset: int = 0) -> Trade:
    ts = datetime(2025, 1, 1, tzinfo=timezone.utc).replace(day=1 + days_offset)
    return Trade(
        symbol="ETH",
        side=TradeSide(side),
        quantity=Decimal(qty),
        price_usd=Decimal(price),
        value_usd=Decimal(qty) * Decimal(price),
        timestamp=ts,
        journal_entry_id=uuid.uuid4(),
    )


class TestFifoMatchBasic:
    def test_single_buy_sell(self):
        trades = [_trade("BUY", "1", "2000", 0), _trade("SELL", "1", "3000", 10)]
        closed, open_lots = fifo_match(trades)

        assert len(closed) == 1
        assert len(open_lots) == 0
        assert closed[0].quantity == Decimal("1")
        assert closed[0].cost_basis_usd == Decimal("2000")
        assert closed[0].proceeds_usd == Decimal("3000")
        assert closed[0].gain_usd == Decimal("1000")
        assert closed[0].holding_days == 10

    def test_partial_sell(self):
        trades = [_trade("BUY", "2", "2000", 0), _trade("SELL", "1", "3000", 5)]
        closed, open_lots = fifo_match(trades)

        assert len(closed) == 1
        assert closed[0].quantity == Decimal("1")
        assert closed[0].gain_usd == Decimal("1000")

        assert len(open_lots) == 1
        assert open_lots[0].remaining_quantity == Decimal("1")

    def test_only_buys(self):
        trades = [_trade("BUY", "1", "2000", 0), _trade("BUY", "2", "2500", 5)]
        closed, open_lots = fifo_match(trades)

        assert len(closed) == 0
        assert len(open_lots) == 2
        assert open_lots[0].remaining_quantity == Decimal("1")
        assert open_lots[1].remaining_quantity == Decimal("2")

    def test_no_trades(self):
        closed, open_lots = fifo_match([])
        assert closed == []
        assert open_lots == []


class TestFifoMatchFIFOOrder:
    def test_oldest_lot_consumed_first(self):
        """FIFO: the first buy (day 0 at $1000) should be consumed before the second buy (day 5 at $2000)."""
        trades = [
            _trade("BUY", "1", "1000", 0),
            _trade("BUY", "1", "2000", 5),
            _trade("SELL", "1", "3000", 10),
        ]
        closed, open_lots = fifo_match(trades)

        assert len(closed) == 1
        assert closed[0].cost_basis_usd == Decimal("1000")  # First buy consumed
        assert closed[0].gain_usd == Decimal("2000")

        assert len(open_lots) == 1
        assert open_lots[0].cost_basis_per_unit_usd == Decimal("2000")  # Second buy remains

    def test_sell_spans_multiple_lots(self):
        trades = [
            _trade("BUY", "1", "1000", 0),
            _trade("BUY", "1", "2000", 5),
            _trade("SELL", "1.5", "3000", 10),
        ]
        closed, open_lots = fifo_match(trades)

        assert len(closed) == 2  # Spans two lots
        # First lot: 1 ETH at $1000
        assert closed[0].quantity == Decimal("1")
        assert closed[0].cost_basis_usd == Decimal("1000")
        # Second lot: 0.5 ETH at $2000
        assert closed[1].quantity == Decimal("0.5")
        assert closed[1].cost_basis_usd == Decimal("1000")  # 0.5 * 2000

        assert len(open_lots) == 1
        assert open_lots[0].remaining_quantity == Decimal("0.5")


class TestFifoMatchLoss:
    def test_realized_loss(self):
        trades = [_trade("BUY", "1", "3000", 0), _trade("SELL", "1", "2000", 10)]
        closed, _ = fifo_match(trades)

        assert len(closed) == 1
        assert closed[0].gain_usd == Decimal("-1000")  # Loss


class TestFifoMatchMultipleSymbols:
    def test_sell_all(self):
        trades = [
            _trade("BUY", "2", "2000", 0),
            _trade("SELL", "2", "3000", 10),
        ]
        closed, open_lots = fifo_match(trades)
        assert len(closed) == 1
        assert len(open_lots) == 0
        assert closed[0].quantity == Decimal("2")


class TestTradesFromSplits:
    def test_positive_asset_is_buy(self):
        splits = [{
            "account_type": "ASSET",
            "account_subtype": "erc20_token",
            "symbol": "ETH",
            "quantity": Decimal("1"),
            "value_usd": Decimal("2000"),
            "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "journal_entry_id": uuid.uuid4(),
            "description": "test",
        }]
        trades = trades_from_splits(splits, "ETH")
        assert len(trades) == 1
        assert trades[0].side == TradeSide.BUY

    def test_negative_asset_is_sell(self):
        splits = [{
            "account_type": "ASSET",
            "account_subtype": "native_asset",
            "symbol": "ETH",
            "quantity": Decimal("-1"),
            "value_usd": Decimal("-2000"),
            "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "journal_entry_id": uuid.uuid4(),
            "description": "test",
        }]
        trades = trades_from_splits(splits, "ETH")
        assert len(trades) == 1
        assert trades[0].side == TradeSide.SELL

    def test_expense_account_ignored(self):
        splits = [{
            "account_type": "EXPENSE",
            "account_subtype": "wallet_expense",
            "symbol": "ETH",
            "quantity": Decimal("0.01"),
            "value_usd": Decimal("20"),
            "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "journal_entry_id": uuid.uuid4(),
            "description": "gas",
        }]
        trades = trades_from_splits(splits, "ETH")
        assert len(trades) == 0

    def test_zero_quantity_ignored(self):
        splits = [{
            "account_type": "ASSET",
            "account_subtype": "erc20_token",
            "symbol": "ETH",
            "quantity": Decimal("0"),
            "value_usd": Decimal("0"),
            "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "journal_entry_id": uuid.uuid4(),
            "description": "test",
        }]
        trades = trades_from_splits(splits, "ETH")
        assert len(trades) == 0

    def test_wrong_symbol_ignored(self):
        splits = [{
            "account_type": "ASSET",
            "account_subtype": "erc20_token",
            "symbol": "USDC",
            "quantity": Decimal("100"),
            "value_usd": Decimal("100"),
            "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "journal_entry_id": uuid.uuid4(),
            "description": "test",
        }]
        trades = trades_from_splits(splits, "ETH")
        assert len(trades) == 0

    def test_sorted_by_timestamp(self):
        splits = [
            {
                "account_type": "ASSET", "account_subtype": "erc20_token", "symbol": "ETH",
                "quantity": Decimal("1"), "value_usd": Decimal("2000"),
                "timestamp": datetime(2025, 6, 1, tzinfo=timezone.utc),
                "journal_entry_id": uuid.uuid4(), "description": "",
            },
            {
                "account_type": "ASSET", "account_subtype": "erc20_token", "symbol": "ETH",
                "quantity": Decimal("1"), "value_usd": Decimal("1000"),
                "timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "journal_entry_id": uuid.uuid4(), "description": "",
            },
        ]
        trades = trades_from_splits(splits, "ETH")
        assert len(trades) == 2
        assert trades[0].timestamp < trades[1].timestamp
