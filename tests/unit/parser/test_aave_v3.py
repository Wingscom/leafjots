"""Tests for AaveV3Parser — can_parse, supply, withdraw, borrow, repay."""

from cryptotax.parser.defi.aave_v3 import (
    AAVE_V3_POOL,
    BORROW_SELECTOR,
    REPAY_SELECTOR,
    SUPPLY_SELECTOR,
    WITHDRAW_SELECTOR,
    AaveV3Parser,
)
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import RawTransfer

WALLET = "0x1111111111111111111111111111111111111111"
POOL = AAVE_V3_POOL["ethereum"]


def _make_tx(selector: str, value: str = "0") -> dict:
    return {
        "hash": "0xaave_test",
        "from": WALLET,
        "to": POOL,
        "value": value,
        "gasUsed": "200000",
        "gasPrice": "20000000000",
        "chain": "ethereum",
        "input": selector + "0" * 56,
    }


def _make_context(transfers: list[RawTransfer]) -> TransactionContext:
    return TransactionContext(transfers, {WALLET})


class TestAaveV3CanParse:
    def test_matches_ethereum_pool(self):
        parser = AaveV3Parser()
        tx_data = {"to": POOL, "chain": "ethereum"}
        ctx = _make_context([])
        assert parser.can_parse(tx_data, ctx) is True

    def test_rejects_unknown_address(self):
        parser = AaveV3Parser()
        tx_data = {"to": "0xdeadbeef", "chain": "ethereum"}
        ctx = _make_context([])
        assert parser.can_parse(tx_data, ctx) is False

    def test_matches_arbitrum_pool(self):
        parser = AaveV3Parser()
        tx_data = {"to": AAVE_V3_POOL["arbitrum"], "chain": "arbitrum"}
        ctx = _make_context([])
        assert parser.can_parse(tx_data, ctx) is True

    def test_wrong_chain_rejects(self):
        parser = AaveV3Parser()
        # Ethereum pool address but claiming arbitrum chain
        tx_data = {"to": POOL, "chain": "arbitrum"}
        ctx = _make_context([])
        assert parser.can_parse(tx_data, ctx) is False


class TestAaveV3Supply:
    def test_supply_produces_deposit_splits(self):
        parser = AaveV3Parser()
        tx_data = _make_tx(SUPPLY_SELECTOR)
        transfers = [
            # Wallet sends USDC to pool
            RawTransfer(token_address="0xusdc", from_address=WALLET, to_address=POOL, value=1000 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
            # Pool sends aUSDC to wallet (mint)
            RawTransfer(token_address="0xausdc", from_address=POOL, to_address=WALLET, value=1000 * 10**6, decimals=6, symbol="aUSDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        # Should have gas splits + deposit splits
        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2

        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        protocol = [s for s in non_gas if s.account_subtype == "protocol_asset"][0]
        assert erc20.symbol == "USDC"
        assert erc20.quantity < 0  # token leaves wallet
        assert protocol.quantity > 0  # protocol asset increases

    def test_supply_entry_type(self):
        parser = AaveV3Parser()
        tx_data = _make_tx(SUPPLY_SELECTOR)
        transfers = [
            RawTransfer(token_address="0xusdc", from_address=WALLET, to_address=POOL, value=10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)
        assert result.entry_type == "DEPOSIT"


class TestAaveV3Withdraw:
    def test_withdraw_produces_withdrawal_splits(self):
        parser = AaveV3Parser()
        tx_data = _make_tx(WITHDRAW_SELECTOR)
        transfers = [
            # Pool sends USDC to wallet
            RawTransfer(token_address="0xusdc", from_address=POOL, to_address=WALLET, value=500 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
            # Wallet sends aUSDC to pool (burn)
            RawTransfer(token_address="0xausdc", from_address=WALLET, to_address=POOL, value=500 * 10**6, decimals=6, symbol="aUSDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2

        protocol = [s for s in non_gas if s.account_subtype == "protocol_asset"][0]
        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        assert protocol.quantity < 0
        assert erc20.quantity > 0
        assert result.entry_type == "WITHDRAWAL"


class TestAaveV3Borrow:
    def test_borrow_produces_debt_splits(self):
        parser = AaveV3Parser()
        tx_data = _make_tx(BORROW_SELECTOR)
        transfers = [
            # Pool sends DAI to wallet
            RawTransfer(token_address="0xdai", from_address=POOL, to_address=WALLET, value=500 * 10**18, decimals=18, symbol="DAI", transfer_type="erc20"),
            # Debt token mint (zero-address → wallet)
            RawTransfer(token_address="0xdebt", from_address="0x0000000000000000000000000000000000000000", to_address=WALLET, value=500 * 10**18, decimals=18, symbol="debtDAI", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2

        debt = [s for s in non_gas if s.account_subtype == "protocol_debt"][0]
        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        assert debt.quantity < 0  # liability increases
        assert erc20.quantity > 0  # asset increases
        assert result.entry_type == "BORROW"


class TestAaveV3Repay:
    def test_repay_produces_repay_splits(self):
        parser = AaveV3Parser()
        tx_data = _make_tx(REPAY_SELECTOR)
        transfers = [
            # Wallet sends DAI to pool
            RawTransfer(token_address="0xdai", from_address=WALLET, to_address=POOL, value=500 * 10**18, decimals=18, symbol="DAI", transfer_type="erc20"),
            # Debt token burn (wallet → zero-address)
            RawTransfer(token_address="0xdebt", from_address=WALLET, to_address="0x0000000000000000000000000000000000000000", value=500 * 10**18, decimals=18, symbol="debtDAI", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2

        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        debt = [s for s in non_gas if s.account_subtype == "protocol_debt"][0]
        assert erc20.quantity < 0  # asset decreases
        assert debt.quantity > 0   # liability decreases
        assert result.entry_type == "REPAY"


class TestAaveV3UnknownSelector:
    def test_unknown_selector_returns_empty(self):
        parser = AaveV3Parser()
        tx_data = _make_tx("0xdeadbeef")
        ctx = _make_context([])
        result = parser.parse(tx_data, ctx)
        assert result.splits == []
