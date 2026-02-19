"""Tests for MorphoBlueParser and MetaMorphoVaultParser."""

from decimal import Decimal

from cryptotax.parser.defi.morpho import (
    BORROW_SELECTOR,
    METAMORPHO_VAULTS,
    MORPHO_BLUE,
    REPAY_SELECTOR,
    SUPPLY_COLLATERAL_SELECTOR,
    SUPPLY_SELECTOR,
    VAULT_DEPOSIT_SELECTOR,
    VAULT_WITHDRAW_SELECTOR,
    WITHDRAW_COLLATERAL_SELECTOR,
    WITHDRAW_SELECTOR,
    MetaMorphoVaultParser,
    MorphoBlueParser,
)
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import RawTransfer

WALLET = "0x1111111111111111111111111111111111111111"
MORPHO_POOL = MORPHO_BLUE["ethereum"]
VAULT = METAMORPHO_VAULTS["ethereum"][0]  # Steakhouse USDC


def _make_tx(to: str, selector: str, value: str = "0") -> dict:
    return {
        "hash": "0xmorpho_test",
        "from": WALLET,
        "to": to,
        "value": value,
        "gasUsed": "200000",
        "gasPrice": "20000000000",
        "chain": "ethereum",
        "input": selector + "0" * 56,
    }


def _make_context(transfers: list[RawTransfer]) -> TransactionContext:
    return TransactionContext(transfers, {WALLET})


# --- MorphoBlueParser ---

class TestMorphoBlueCanParse:
    def test_matches_ethereum_morpho(self):
        parser = MorphoBlueParser()
        tx_data = {"to": MORPHO_POOL, "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_rejects_unknown_address(self):
        parser = MorphoBlueParser()
        tx_data = {"to": "0xdeadbeef", "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is False

    def test_rejects_wrong_chain(self):
        parser = MorphoBlueParser()
        tx_data = {"to": MORPHO_POOL, "chain": "arbitrum"}
        assert parser.can_parse(tx_data, _make_context([])) is False


class TestMorphoBlueSupply:
    def test_supply_produces_deposit_splits(self):
        parser = MorphoBlueParser()
        tx_data = _make_tx(MORPHO_POOL, SUPPLY_SELECTOR)
        transfers = [
            RawTransfer(token_address="0xusdc", from_address=WALLET, to_address=MORPHO_POOL, value=1000 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2
        assert result.entry_type == "DEPOSIT"

        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        protocol = [s for s in non_gas if s.account_subtype == "protocol_asset"][0]
        assert erc20.symbol == "USDC"
        assert erc20.quantity == Decimal("-1000")
        assert protocol.quantity == Decimal("1000")


class TestMorphoBlueWithdraw:
    def test_withdraw_produces_withdrawal_splits(self):
        parser = MorphoBlueParser()
        tx_data = _make_tx(MORPHO_POOL, WITHDRAW_SELECTOR)
        transfers = [
            RawTransfer(token_address="0xusdc", from_address=MORPHO_POOL, to_address=WALLET, value=500 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2
        assert result.entry_type == "WITHDRAWAL"

        protocol = [s for s in non_gas if s.account_subtype == "protocol_asset"][0]
        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        assert protocol.quantity < 0
        assert erc20.quantity > 0


class TestMorphoBlueBorrow:
    def test_borrow_produces_debt_splits(self):
        parser = MorphoBlueParser()
        tx_data = _make_tx(MORPHO_POOL, BORROW_SELECTOR)
        transfers = [
            RawTransfer(token_address="0xdai", from_address=MORPHO_POOL, to_address=WALLET, value=500 * 10**18, decimals=18, symbol="DAI", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2
        assert result.entry_type == "BORROW"

        debt = [s for s in non_gas if s.account_subtype == "protocol_debt"][0]
        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        assert debt.quantity < 0
        assert erc20.quantity > 0


class TestMorphoBlueRepay:
    def test_repay_produces_repay_splits(self):
        parser = MorphoBlueParser()
        tx_data = _make_tx(MORPHO_POOL, REPAY_SELECTOR)
        transfers = [
            RawTransfer(token_address="0xdai", from_address=WALLET, to_address=MORPHO_POOL, value=500 * 10**18, decimals=18, symbol="DAI", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2
        assert result.entry_type == "REPAY"

        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        debt = [s for s in non_gas if s.account_subtype == "protocol_debt"][0]
        assert erc20.quantity < 0
        assert debt.quantity > 0


class TestMorphoBlueCollateral:
    def test_supply_collateral_produces_deposit(self):
        parser = MorphoBlueParser()
        tx_data = _make_tx(MORPHO_POOL, SUPPLY_COLLATERAL_SELECTOR)
        transfers = [
            RawTransfer(token_address="0xweth", from_address=WALLET, to_address=MORPHO_POOL, value=10**18, decimals=18, symbol="WETH", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2
        assert result.entry_type == "DEPOSIT"

    def test_withdraw_collateral_produces_withdrawal(self):
        parser = MorphoBlueParser()
        tx_data = _make_tx(MORPHO_POOL, WITHDRAW_COLLATERAL_SELECTOR)
        transfers = [
            RawTransfer(token_address="0xweth", from_address=MORPHO_POOL, to_address=WALLET, value=10**18, decimals=18, symbol="WETH", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2
        assert result.entry_type == "WITHDRAWAL"


class TestMorphoBlueUnknown:
    def test_unknown_selector_returns_empty(self):
        parser = MorphoBlueParser()
        tx_data = _make_tx(MORPHO_POOL, "0xdeadbeef")
        ctx = _make_context([])
        result = parser.parse(tx_data, ctx)
        assert result.splits == []


# --- MetaMorphoVaultParser ---

class TestMetaMorphoCanParse:
    def test_matches_known_vault(self):
        parser = MetaMorphoVaultParser()
        tx_data = {"to": VAULT, "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_rejects_unknown_vault(self):
        parser = MetaMorphoVaultParser()
        tx_data = {"to": "0xunknown", "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is False


class TestMetaMorphoDeposit:
    def test_vault_deposit(self):
        parser = MetaMorphoVaultParser()
        tx_data = _make_tx(VAULT, VAULT_DEPOSIT_SELECTOR)
        transfers = [
            # User sends USDC to vault
            RawTransfer(token_address="0xusdc", from_address=WALLET, to_address=VAULT, value=1000 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
            # Vault mints shares to user
            RawTransfer(token_address=VAULT, from_address=VAULT, to_address=WALLET, value=1000 * 10**18, decimals=18, symbol="mmUSDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2
        assert result.entry_type == "DEPOSIT"

        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        protocol = [s for s in non_gas if s.account_subtype == "protocol_asset"][0]
        assert erc20.symbol == "USDC"
        assert erc20.quantity < 0
        assert protocol.quantity > 0


class TestMetaMorphoWithdraw:
    def test_vault_withdraw(self):
        parser = MetaMorphoVaultParser()
        tx_data = _make_tx(VAULT, VAULT_WITHDRAW_SELECTOR)
        transfers = [
            # Vault sends USDC to user
            RawTransfer(token_address="0xusdc", from_address=VAULT, to_address=WALLET, value=1000 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
            # User burns shares
            RawTransfer(token_address=VAULT, from_address=WALLET, to_address=VAULT, value=1000 * 10**18, decimals=18, symbol="mmUSDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2
        assert result.entry_type == "WITHDRAWAL"

        protocol = [s for s in non_gas if s.account_subtype == "protocol_asset"][0]
        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"][0]
        assert protocol.quantity < 0
        assert erc20.quantity > 0


class TestMetaMorphoUnknown:
    def test_unknown_selector_returns_empty(self):
        parser = MetaMorphoVaultParser()
        tx_data = _make_tx(VAULT, "0xdeadbeef")
        ctx = _make_context([])
        result = parser.parse(tx_data, ctx)
        assert result.splits == []
