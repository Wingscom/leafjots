"""Tests for reusable handler functions — all must produce balanced splits."""

from decimal import Decimal

from cryptotax.parser.handlers.common import (
    make_borrow_splits,
    make_deposit_splits,
    make_repay_splits,
    make_withdrawal_splits,
    make_yield_splits,
)


def _assert_balanced(splits, symbol: str):
    """Verify splits sum to zero for the given symbol."""
    total = sum(s.quantity for s in splits if s.symbol == symbol)
    assert total == Decimal(0), f"Splits unbalanced for {symbol}: sum={total}"


class TestMakeDepositSplits:
    def test_produces_two_splits(self):
        splits = make_deposit_splits("USDC", Decimal("1000"), "aave_v3", "ethereum")
        assert len(splits) == 2

    def test_balanced(self):
        splits = make_deposit_splits("USDC", Decimal("1000"), "aave_v3", "ethereum")
        _assert_balanced(splits, "USDC")

    def test_subtypes(self):
        splits = make_deposit_splits("USDC", Decimal("1000"), "aave_v3", "ethereum")
        subtypes = {s.account_subtype for s in splits}
        assert subtypes == {"erc20_token", "protocol_asset"}

    def test_directions(self):
        splits = make_deposit_splits("USDC", Decimal("500"), "aave_v3", "ethereum")
        erc20 = [s for s in splits if s.account_subtype == "erc20_token"][0]
        protocol = [s for s in splits if s.account_subtype == "protocol_asset"][0]
        assert erc20.quantity == Decimal("-500")
        assert protocol.quantity == Decimal("500")


class TestMakeWithdrawalSplits:
    def test_produces_two_splits(self):
        splits = make_withdrawal_splits("DAI", Decimal("2000"), "aave_v3", "ethereum")
        assert len(splits) == 2

    def test_balanced(self):
        splits = make_withdrawal_splits("DAI", Decimal("2000"), "aave_v3", "ethereum")
        _assert_balanced(splits, "DAI")

    def test_directions(self):
        splits = make_withdrawal_splits("DAI", Decimal("2000"), "aave_v3", "ethereum")
        protocol = [s for s in splits if s.account_subtype == "protocol_asset"][0]
        erc20 = [s for s in splits if s.account_subtype == "erc20_token"][0]
        assert protocol.quantity == Decimal("-2000")
        assert erc20.quantity == Decimal("2000")


class TestMakeBorrowSplits:
    def test_produces_two_splits(self):
        splits = make_borrow_splits("DAI", Decimal("500"), "aave_v3", "ethereum")
        assert len(splits) == 2

    def test_balanced(self):
        splits = make_borrow_splits("DAI", Decimal("500"), "aave_v3", "ethereum")
        _assert_balanced(splits, "DAI")

    def test_directions(self):
        splits = make_borrow_splits("DAI", Decimal("500"), "aave_v3", "ethereum")
        debt = [s for s in splits if s.account_subtype == "protocol_debt"][0]
        erc20 = [s for s in splits if s.account_subtype == "erc20_token"][0]
        assert debt.quantity == Decimal("-500")  # liability increases
        assert erc20.quantity == Decimal("500")  # asset increases


class TestMakeRepaySplits:
    def test_produces_two_splits(self):
        splits = make_repay_splits("DAI", Decimal("500"), "aave_v3", "ethereum")
        assert len(splits) == 2

    def test_balanced(self):
        splits = make_repay_splits("DAI", Decimal("500"), "aave_v3", "ethereum")
        _assert_balanced(splits, "DAI")

    def test_directions(self):
        splits = make_repay_splits("DAI", Decimal("500"), "aave_v3", "ethereum")
        erc20 = [s for s in splits if s.account_subtype == "erc20_token"][0]
        debt = [s for s in splits if s.account_subtype == "protocol_debt"][0]
        assert erc20.quantity == Decimal("-500")  # asset decreases
        assert debt.quantity == Decimal("500")    # liability decreases (positive!)


class TestMakeYieldSplits:
    def test_produces_two_splits(self):
        splits = make_yield_splits("USDC", Decimal("10"), "aave_v3", "ethereum")
        assert len(splits) == 2

    def test_balanced(self):
        splits = make_yield_splits("USDC", Decimal("10"), "aave_v3", "ethereum")
        _assert_balanced(splits, "USDC")

    def test_directions(self):
        splits = make_yield_splits("USDC", Decimal("10"), "aave_v3", "ethereum")
        income = [s for s in splits if s.account_subtype == "wallet_income"][0]
        erc20 = [s for s in splits if s.account_subtype == "erc20_token"][0]
        assert income.quantity == Decimal("-10")  # income is negative in double-entry
        assert erc20.quantity == Decimal("10")

    def test_custom_tag(self):
        splits = make_yield_splits("USDC", Decimal("10"), "aave_v3", "ethereum", tag="Rewards")
        income = [s for s in splits if s.account_subtype == "wallet_income"][0]
        assert income.account_params["tag"] == "Rewards"
