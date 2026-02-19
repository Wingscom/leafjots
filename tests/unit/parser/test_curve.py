"""Tests for CurvePoolParser — can_parse, exchange, add/remove liquidity."""

from cryptotax.parser.defi.curve import (
    ADD_LIQUIDITY_3,
    CURVE_POOLS,
    EXCHANGE,
    REMOVE_ONE_COIN,
    CurvePoolParser,
)
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import RawTransfer

WALLET = "0x1111111111111111111111111111111111111111"
POOL_3POOL = CURVE_POOLS["ethereum"][0]  # 3pool


def _make_tx(selector: str, value: str = "0") -> dict:
    return {
        "hash": "0xcurve_test",
        "from": WALLET,
        "to": POOL_3POOL,
        "value": value,
        "gasUsed": "250000",
        "gasPrice": "20000000000",
        "chain": "ethereum",
        "input": selector + "0" * 56,
    }


def _make_context(transfers: list[RawTransfer]) -> TransactionContext:
    return TransactionContext(transfers, {WALLET})


class TestCurveCanParse:
    def test_matches_3pool(self):
        parser = CurvePoolParser()
        tx_data = {"to": POOL_3POOL, "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_rejects_unknown_pool(self):
        parser = CurvePoolParser()
        tx_data = {"to": "0xunknown_pool", "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is False

    def test_matches_arbitrum_pool(self):
        parser = CurvePoolParser()
        arb_pool = CURVE_POOLS["arbitrum"][0]
        tx_data = {"to": arb_pool, "chain": "arbitrum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_wrong_chain_rejects(self):
        parser = CurvePoolParser()
        tx_data = {"to": POOL_3POOL, "chain": "arbitrum"}
        assert parser.can_parse(tx_data, _make_context([])) is False


class TestCurveExchange:
    def test_exchange_produces_swap_splits(self):
        parser = CurvePoolParser()
        tx_data = _make_tx(EXCHANGE)
        transfers = [
            RawTransfer(token_address="0xdai", from_address=WALLET, to_address=POOL_3POOL, value=1000 * 10**18, decimals=18, symbol="DAI", transfer_type="erc20"),
            RawTransfer(token_address="0xusdc", from_address=POOL_3POOL, to_address=WALLET, value=999 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        dai_splits = [s for s in non_gas if s.symbol == "DAI"]
        usdc_splits = [s for s in non_gas if s.symbol == "USDC"]
        assert any(s.quantity < 0 for s in dai_splits), "DAI should flow out"
        assert any(s.quantity > 0 for s in usdc_splits), "USDC should flow in"
        assert result.entry_type == "SWAP"


class TestCurveAddLiquidity:
    def test_add_liquidity_produces_deposit_splits(self):
        parser = CurvePoolParser()
        tx_data = _make_tx(ADD_LIQUIDITY_3)
        transfers = [
            # Tokens out to pool
            RawTransfer(token_address="0xdai", from_address=WALLET, to_address=POOL_3POOL, value=1000 * 10**18, decimals=18, symbol="DAI", transfer_type="erc20"),
            RawTransfer(token_address="0xusdc", from_address=WALLET, to_address=POOL_3POOL, value=1000 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
            # LP token received
            RawTransfer(token_address="0x3crv", from_address=POOL_3POOL, to_address=WALLET, value=2000 * 10**18, decimals=18, symbol="3CRV", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]

        # Outflows → erc20_token (negative)
        erc20_out = [s for s in non_gas if s.account_subtype == "erc20_token" and s.quantity < 0]
        assert len(erc20_out) == 2  # DAI + USDC

        # LP token in → protocol_asset (positive)
        protocol_in = [s for s in non_gas if s.account_subtype == "protocol_asset" and s.quantity > 0]
        assert len(protocol_in) == 1
        assert protocol_in[0].symbol == "3CRV"

        assert result.entry_type == "DEPOSIT"


class TestCurveRemoveLiquidity:
    def test_remove_one_coin_produces_withdrawal_splits(self):
        parser = CurvePoolParser()
        tx_data = _make_tx(REMOVE_ONE_COIN)
        transfers = [
            # LP token out (burn)
            RawTransfer(token_address="0x3crv", from_address=WALLET, to_address=POOL_3POOL, value=2000 * 10**18, decimals=18, symbol="3CRV", transfer_type="erc20"),
            # Token received
            RawTransfer(token_address="0xdai", from_address=POOL_3POOL, to_address=WALLET, value=2010 * 10**18, decimals=18, symbol="DAI", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]

        # LP burn → protocol_asset (negative)
        protocol_out = [s for s in non_gas if s.account_subtype == "protocol_asset" and s.quantity < 0]
        assert len(protocol_out) == 1
        assert protocol_out[0].symbol == "3CRV"

        # Token in → erc20_token (positive)
        erc20_in = [s for s in non_gas if s.account_subtype == "erc20_token" and s.quantity > 0]
        assert len(erc20_in) == 1
        assert erc20_in[0].symbol == "DAI"

        assert result.entry_type == "WITHDRAWAL"
