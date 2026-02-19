from decimal import Decimal

from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import RawTransfer


def _make_transfer(from_addr: str = "0xaaa", to_addr: str = "0xbbb", value: int = 10**18, symbol: str = "ETH") -> RawTransfer:
    return RawTransfer(
        token_address=None,
        from_address=from_addr,
        to_address=to_addr,
        value=value,
        decimals=18,
        symbol=symbol,
        transfer_type="native",
    )


class TestTransactionContext:
    def test_is_wallet(self):
        ctx = TransactionContext([], {"0xAAA", "0xBBB"})
        assert ctx.is_wallet("0xaaa")
        assert ctx.is_wallet("0xAAA")
        assert not ctx.is_wallet("0xccc")

    def test_pop_transfer_removes(self):
        t = _make_transfer()
        ctx = TransactionContext([t], {"0xaaa"})
        popped = ctx.pop_transfer(from_address="0xaaa")
        assert popped is not None
        assert popped.from_address == "0xaaa"
        assert len(ctx.remaining_transfers()) == 0

    def test_pop_transfer_not_found(self):
        ctx = TransactionContext([_make_transfer()], {"0xaaa"})
        result = ctx.pop_transfer(from_address="0xzzz")
        assert result is None
        assert len(ctx.remaining_transfers()) == 1

    def test_peek_transfers_no_consume(self):
        t = _make_transfer()
        ctx = TransactionContext([t], {"0xaaa"})
        peeked = ctx.peek_transfers(from_address="0xaaa")
        assert len(peeked) == 1
        assert len(ctx.remaining_transfers()) == 1  # Not consumed

    def test_remaining_transfers(self):
        ctx = TransactionContext([_make_transfer(), _make_transfer(from_addr="0xccc")], {"0xaaa"})
        assert len(ctx.remaining_transfers()) == 2
        ctx.pop_transfer(from_address="0xaaa")
        assert len(ctx.remaining_transfers()) == 1

    def test_net_flows_outgoing(self):
        t = _make_transfer(from_addr="0xaaa", to_addr="0xbbb", value=10**18)
        ctx = TransactionContext([t], {"0xaaa"})
        flows = ctx.net_flows()
        assert "0xaaa" in flows
        assert flows["0xaaa"]["ETH"] == Decimal("-1")

    def test_net_flows_incoming(self):
        t = _make_transfer(from_addr="0xbbb", to_addr="0xaaa", value=10**18)
        ctx = TransactionContext([t], {"0xaaa"})
        flows = ctx.net_flows()
        assert "0xaaa" in flows
        assert flows["0xaaa"]["ETH"] == Decimal("1")

    def test_net_flows_both_wallets(self):
        t = _make_transfer(from_addr="0xaaa", to_addr="0xbbb", value=10**18)
        ctx = TransactionContext([t], {"0xaaa", "0xbbb"})
        flows = ctx.net_flows()
        assert flows["0xaaa"]["ETH"] == Decimal("-1")
        assert flows["0xbbb"]["ETH"] == Decimal("1")

    def test_net_flows_multiple_tokens(self):
        t1 = _make_transfer(from_addr="0xaaa", to_addr="0xbbb", value=10**18, symbol="ETH")
        t2 = _make_transfer(from_addr="0xbbb", to_addr="0xaaa", value=2000 * 10**6, symbol="USDC")
        t2.decimals = 6
        ctx = TransactionContext([t1, t2], {"0xaaa"})
        flows = ctx.net_flows()
        assert flows["0xaaa"]["ETH"] == Decimal("-1")
        assert flows["0xaaa"]["USDC"] == Decimal("2000")

    def test_pop_by_to_address(self):
        t = _make_transfer(from_addr="0xaaa", to_addr="0xbbb")
        ctx = TransactionContext([t], {"0xaaa"})
        popped = ctx.pop_transfer(to_address="0xBBB")  # Case insensitive
        assert popped is not None
