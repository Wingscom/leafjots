"""Tests for LidoParser — submit, wrap, unwrap."""

from decimal import Decimal

from cryptotax.parser.defi.lido import (
    LIDO_STETH,
    LIDO_WSTETH,
    SUBMIT_SELECTOR,
    UNWRAP_SELECTOR,
    WRAP_SELECTOR,
    LidoParser,
)
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import RawTransfer

WALLET = "0x1111111111111111111111111111111111111111"
STETH = LIDO_STETH["ethereum"]
WSTETH = LIDO_WSTETH["ethereum"]


def _make_tx(to: str, selector: str, value: str = "0") -> dict:
    return {
        "hash": "0xlido_test",
        "from": WALLET,
        "to": to,
        "value": value,
        "gasUsed": "100000",
        "gasPrice": "20000000000",
        "chain": "ethereum",
        "input": selector + "0" * 56,
    }


def _make_context(transfers: list[RawTransfer]) -> TransactionContext:
    return TransactionContext(transfers, {WALLET})


class TestLidoCanParse:
    def test_matches_steth(self):
        parser = LidoParser()
        tx_data = {"to": STETH, "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_matches_wsteth(self):
        parser = LidoParser()
        tx_data = {"to": WSTETH, "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_matches_arb_wsteth(self):
        parser = LidoParser()
        arb_wsteth = LIDO_WSTETH["arbitrum"]
        tx_data = {"to": arb_wsteth, "chain": "arbitrum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_rejects_unknown(self):
        parser = LidoParser()
        tx_data = {"to": "0xdeadbeef", "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is False


class TestLidoSubmit:
    def test_submit_eth_staking(self):
        parser = LidoParser()
        tx_data = _make_tx(STETH, SUBMIT_SELECTOR, "1000000000000000000")  # 1 ETH
        transfers = [
            # stETH minted to wallet
            RawTransfer(
                token_address=STETH, from_address=STETH, to_address=WALLET,
                value=10**18, decimals=18, symbol="stETH", transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("wallet_expense",)]
        assert result.entry_type == "DEPOSIT"

        # ETH out (native_asset negative) + protocol asset in (positive)
        native = [s for s in non_gas if s.account_subtype == "native_asset"]
        protocol = [s for s in non_gas if s.account_subtype == "protocol_asset"]
        assert any(s.quantity < 0 for s in native), "ETH should leave wallet"
        assert any(s.quantity > 0 for s in protocol), "Protocol asset should increase"


class TestLidoWrap:
    def test_wrap_steth_to_wsteth(self):
        parser = LidoParser()
        tx_data = _make_tx(WSTETH, WRAP_SELECTOR)
        transfers = [
            # stETH sent to wstETH contract
            RawTransfer(
                token_address=STETH, from_address=WALLET, to_address=WSTETH,
                value=10**18, decimals=18, symbol="stETH", transfer_type="erc20",
            ),
            # wstETH received
            RawTransfer(
                token_address=WSTETH, from_address=WSTETH, to_address=WALLET,
                value=8 * 10**17, decimals=18, symbol="wstETH", transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert result.entry_type == "SWAP"
        assert len(non_gas) == 2

        steth_split = [s for s in non_gas if s.symbol == "stETH"][0]
        wsteth_split = [s for s in non_gas if s.symbol == "wstETH"][0]
        assert steth_split.quantity < 0
        assert wsteth_split.quantity > 0


class TestLidoUnwrap:
    def test_unwrap_wsteth_to_steth(self):
        parser = LidoParser()
        tx_data = _make_tx(WSTETH, UNWRAP_SELECTOR)
        transfers = [
            # wstETH sent (burned)
            RawTransfer(
                token_address=WSTETH, from_address=WALLET, to_address=WSTETH,
                value=8 * 10**17, decimals=18, symbol="wstETH", transfer_type="erc20",
            ),
            # stETH received
            RawTransfer(
                token_address=STETH, from_address=WSTETH, to_address=WALLET,
                value=10**18, decimals=18, symbol="stETH", transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert result.entry_type == "SWAP"
        assert len(non_gas) == 2

        wsteth_split = [s for s in non_gas if s.symbol == "wstETH"][0]
        steth_split = [s for s in non_gas if s.symbol == "stETH"][0]
        assert wsteth_split.quantity < 0
        assert steth_split.quantity > 0


class TestLidoUnknown:
    def test_unknown_selector_returns_empty(self):
        parser = LidoParser()
        tx_data = _make_tx(STETH, "0xdeadbeef")
        ctx = _make_context([])
        result = parser.parse(tx_data, ctx)
        assert result.splits == []
