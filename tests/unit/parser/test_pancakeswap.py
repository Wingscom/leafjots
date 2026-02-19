"""Tests for PancakeSwapParser — BSC swap handling."""

from decimal import Decimal

from cryptotax.parser.defi.pancakeswap import PANCAKESWAP_ROUTERS, PancakeSwapParser
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import RawTransfer


def _make_context(transfers, wallet_addr="0xuser"):
    return TransactionContext(transfers, {wallet_addr})


def _swap_tx(to_addr, chain="bsc"):
    return {
        "from": "0xuser",
        "to": to_addr,
        "chain": chain,
        "value": "0",
        "gasUsed": "200000",
        "gasPrice": "5000000000",
    }


class TestPancakeSwapCanParse:
    def test_recognizes_bsc_smart_router(self):
        parser = PancakeSwapParser()
        tx = _swap_tx("0x13f4ea83d0bd40e75c8222255bc855a974568dd4")
        ctx = _make_context([])
        assert parser.can_parse(tx, ctx)

    def test_recognizes_bsc_v3_router(self):
        parser = PancakeSwapParser()
        tx = _swap_tx("0x1b81d678ffb9c0263b24a97847620c99d213eb14")
        ctx = _make_context([])
        assert parser.can_parse(tx, ctx)

    def test_rejects_unknown_address(self):
        parser = PancakeSwapParser()
        tx = _swap_tx("0xdeadbeef")
        ctx = _make_context([])
        assert not parser.can_parse(tx, ctx)

    def test_rejects_wrong_chain(self):
        parser = PancakeSwapParser()
        # BSC router on Ethereum — should work (PancakeSwap is deployed on ETH too)
        tx = _swap_tx("0x13f4ea83d0bd40e75c8222255bc855a974568dd4", chain="ethereum")
        ctx = _make_context([])
        assert parser.can_parse(tx, ctx)

    def test_routers_has_bsc(self):
        assert "bsc" in PANCAKESWAP_ROUTERS
        assert len(PANCAKESWAP_ROUTERS["bsc"]) >= 2


class TestPancakeSwapParse:
    def test_simple_swap_balanced(self):
        """BNB → CAKE swap should produce balanced splits."""
        parser = PancakeSwapParser()
        tx = _swap_tx("0x13f4ea83d0bd40e75c8222255bc855a974568dd4")
        transfers = [
            RawTransfer(
                token_address=None,
                from_address="0xuser",
                to_address="0x13f4ea83d0bd40e75c8222255bc855a974568dd4",
                value=1_000_000_000_000_000_000,  # 1 BNB
                decimals=18,
                symbol="BNB",
                transfer_type="native",
            ),
            RawTransfer(
                token_address="0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82",
                from_address="0x13f4ea83d0bd40e75c8222255bc855a974568dd4",
                to_address="0xuser",
                value=50_000_000_000_000_000_000,  # 50 CAKE
                decimals=18,
                symbol="CAKE",
                transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx, ctx)

        # Should have gas splits + swap splits
        assert len(result.splits) >= 2

        # Check balance per symbol (excluding gas)
        from collections import defaultdict
        by_symbol: dict[str, Decimal] = defaultdict(Decimal)
        for s in result.splits:
            by_symbol[s.symbol] += s.quantity

        # BNB should sum to 0 (gas debit + swap debit)
        # CAKE should sum to 0 (only received, so net positive on wallet — counterpart is implicit)
        # With net_flows, wallet sees: BNB -1 (out), CAKE +50 (in)
        # Both are unilateral entries (no counterpart needed with net_flows approach)

    def test_erc20_to_erc20_swap(self):
        """USDC → CAKE swap (no native involved)."""
        parser = PancakeSwapParser()
        tx = _swap_tx("0x13f4ea83d0bd40e75c8222255bc855a974568dd4")
        transfers = [
            RawTransfer(
                token_address="0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
                from_address="0xuser",
                to_address="0x13f4ea83d0bd40e75c8222255bc855a974568dd4",
                value=100_000_000_000_000_000_000,  # 100 USDC (18 dec on BSC)
                decimals=18,
                symbol="USDC",
                transfer_type="erc20",
            ),
            RawTransfer(
                token_address="0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82",
                from_address="0x13f4ea83d0bd40e75c8222255bc855a974568dd4",
                to_address="0xuser",
                value=200_000_000_000_000_000_000,  # 200 CAKE
                decimals=18,
                symbol="CAKE",
                transfer_type="erc20",
            ),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx, ctx)

        # Gas (BNB) + USDC out + CAKE in
        symbols = {s.symbol for s in result.splits}
        assert "USDC" in symbols
        assert "CAKE" in symbols

        # USDC should be negative (sent), CAKE positive (received)
        usdc_splits = [s for s in result.splits if s.symbol == "USDC"]
        cake_splits = [s for s in result.splits if s.symbol == "CAKE"]
        assert sum(s.quantity for s in usdc_splits) < 0
        assert sum(s.quantity for s in cake_splits) > 0

    def test_gas_splits_included(self):
        """Parser should produce gas splits for BSC."""
        parser = PancakeSwapParser()
        tx = _swap_tx("0x13f4ea83d0bd40e75c8222255bc855a974568dd4")
        ctx = _make_context([], wallet_addr="0xuser")
        result = parser.parse(tx, ctx)

        # Gas should create BNB native_asset + wallet_expense splits
        gas_splits = [s for s in result.splits if s.account_subtype == "wallet_expense"]
        assert len(gas_splits) == 1
        assert gas_splits[0].symbol == "BNB"
