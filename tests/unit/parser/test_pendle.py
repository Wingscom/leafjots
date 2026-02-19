"""Tests for PendleParser — router swaps, SY mint/redeem, yield claiming."""

from decimal import Decimal

from cryptotax.parser.defi.pendle import (
    MINT_SY_FROM_TOKEN,
    PENDLE_ROUTER,
    REDEEM_DUE_INTEREST_AND_REWARDS,
    REDEEM_SY_TO_TOKEN,
    SWAP_EXACT_TOKEN_FOR_PT,
    PendleParser,
)
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import RawTransfer

WALLET = "0x1111111111111111111111111111111111111111"
ROUTER = PENDLE_ROUTER["ethereum"]


def _make_tx(selector: str, value: str = "0") -> dict:
    return {
        "hash": "0xpendle_test",
        "from": WALLET,
        "to": ROUTER,
        "value": value,
        "gasUsed": "300000",
        "gasPrice": "20000000000",
        "chain": "ethereum",
        "input": selector + "0" * 56,
    }


def _make_context(transfers: list[RawTransfer]) -> TransactionContext:
    return TransactionContext(transfers, {WALLET})


class TestPendleCanParse:
    def test_matches_router(self):
        parser = PendleParser()
        tx_data = {"to": ROUTER, "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_rejects_unknown(self):
        parser = PendleParser()
        tx_data = {"to": "0xdeadbeef", "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is False


class TestPendleSwap:
    def test_swap_token_for_pt(self):
        parser = PendleParser()
        tx_data = _make_tx(SWAP_EXACT_TOKEN_FOR_PT)
        transfers = [
            # USDC sent to router
            RawTransfer(
                token_address="0xusdc", from_address=WALLET, to_address=ROUTER,
                value=1000 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20",
            ),
            # PT-USDC received
            RawTransfer(
                token_address="0xpt_usdc", from_address=ROUTER, to_address=WALLET,
                value=1050 * 10**6, decimals=6, symbol="PT-USDC", transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        assert result.entry_type == "SWAP"
        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]

        usdc_splits = [s for s in non_gas if s.symbol == "USDC"]
        pt_splits = [s for s in non_gas if s.symbol == "PT-USDC"]
        assert any(s.quantity < 0 for s in usdc_splits), "USDC should flow out"
        assert any(s.quantity > 0 for s in pt_splits), "PT-USDC should flow in"


class TestPendleSYMint:
    def test_sy_mint(self):
        parser = PendleParser()
        tx_data = _make_tx(MINT_SY_FROM_TOKEN)
        transfers = [
            # Underlying sent
            RawTransfer(
                token_address="0xsteth", from_address=WALLET, to_address=ROUTER,
                value=10**18, decimals=18, symbol="stETH", transfer_type="erc20",
            ),
            # SY received
            RawTransfer(
                token_address="0xsy_steth", from_address=ROUTER, to_address=WALLET,
                value=10**18, decimals=18, symbol="SY-stETH", transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        assert result.entry_type == "DEPOSIT"
        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2

        steth = [s for s in non_gas if s.symbol == "stETH"][0]
        sy = [s for s in non_gas if s.symbol == "SY-stETH"][0]
        assert steth.quantity < 0
        assert sy.quantity > 0


class TestPendleSYRedeem:
    def test_sy_redeem(self):
        parser = PendleParser()
        tx_data = _make_tx(REDEEM_SY_TO_TOKEN)
        transfers = [
            # SY burned
            RawTransfer(
                token_address="0xsy_steth", from_address=WALLET, to_address=ROUTER,
                value=10**18, decimals=18, symbol="SY-stETH", transfer_type="erc20",
            ),
            # Underlying received
            RawTransfer(
                token_address="0xsteth", from_address=ROUTER, to_address=WALLET,
                value=10**18, decimals=18, symbol="stETH", transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        assert result.entry_type == "WITHDRAWAL"
        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 2

        sy = [s for s in non_gas if s.symbol == "SY-stETH"][0]
        steth = [s for s in non_gas if s.symbol == "stETH"][0]
        assert sy.quantity < 0
        assert steth.quantity > 0


class TestPendleYieldClaim:
    def test_yield_claim_produces_income(self):
        parser = PendleParser()
        tx_data = _make_tx(REDEEM_DUE_INTEREST_AND_REWARDS)
        transfers = [
            # Yield token received
            RawTransfer(
                token_address="0xusdc", from_address=ROUTER, to_address=WALLET,
                value=50 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        assert result.entry_type == "TRANSFER"
        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]

        income = [s for s in non_gas if s.account_subtype == "wallet_income"]
        erc20 = [s for s in non_gas if s.account_subtype == "erc20_token"]
        assert len(income) == 1
        assert income[0].quantity < 0  # income is negative in double-entry
        assert len(erc20) == 1
        assert erc20[0].quantity > 0  # asset increases

    def test_yield_claim_multiple_tokens(self):
        parser = PendleParser()
        tx_data = _make_tx(REDEEM_DUE_INTEREST_AND_REWARDS)
        transfers = [
            RawTransfer(
                token_address="0xusdc", from_address=ROUTER, to_address=WALLET,
                value=50 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20",
            ),
            RawTransfer(
                token_address="0xpendle", from_address=ROUTER, to_address=WALLET,
                value=100 * 10**18, decimals=18, symbol="PENDLE", transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        # 2 tokens × 2 splits (income + erc20) = 4
        assert len(non_gas) == 4

        symbols = {s.symbol for s in non_gas}
        assert "USDC" in symbols
        assert "PENDLE" in symbols
