from collections import defaultdict
from decimal import Decimal

from cryptotax.parser.generic.evm import GenericEVMParser
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.transfers import extract_transfers_from_etherscan


WALLET = "0x1111111111111111111111111111111111111111"

ETH_TRANSFER = {
    "hash": "0xabc",
    "from": WALLET,
    "to": "0x2222222222222222222222222222222222222222",
    "value": "1000000000000000000",
    "gasUsed": "21000",
    "gasPrice": "20000000000",
    "chain": "ethereum",
}


def _assert_balanced(result_or_splits):
    """Accept either a ParseResult or a list of splits."""
    splits = result_or_splits.splits if hasattr(result_or_splits, 'splits') else result_or_splits
    by_symbol = defaultdict(Decimal)
    for s in splits:
        by_symbol[s.symbol] += s.quantity
    for sym, total in by_symbol.items():
        assert total == Decimal(0), f"Imbalanced: {sym}={total}"


class TestGenericEVMParser:
    def test_can_parse_always_true(self):
        parser = GenericEVMParser()
        ctx = TransactionContext([], {WALLET})
        assert parser.can_parse({}, ctx) is True

    def test_parse_eth_transfer_outgoing(self):
        parser = GenericEVMParser()
        transfers = extract_transfers_from_etherscan(ETH_TRANSFER, "ethereum")
        ctx = TransactionContext(transfers, {WALLET})

        result = parser.parse(ETH_TRANSFER, ctx)
        assert len(result.splits) > 0

        # Must be balanced
        _assert_balanced(result)

        # Should have gas splits + transfer splits
        symbols = {s.symbol for s in result.splits}
        assert "ETH" in symbols

    def test_parse_gas_only_tx(self):
        """TX with value=0 but gas paid (e.g., contract approval)."""
        tx_data = {
            "hash": "0xapproval",
            "from": WALLET,
            "to": "0x3333333333333333333333333333333333333333",
            "value": "0",
            "gasUsed": "46000",
            "gasPrice": "30000000000",
            "chain": "ethereum",
        }
        parser = GenericEVMParser()
        transfers = extract_transfers_from_etherscan(tx_data, "ethereum")
        ctx = TransactionContext(transfers, {WALLET})

        result = parser.parse(tx_data, ctx)
        _assert_balanced(result)

        # Should have gas expense splits
        subtypes = {s.account_subtype for s in result.splits}
        assert "native_asset" in subtypes
        assert "wallet_expense" in subtypes

    def test_parse_incoming_transfer(self):
        tx_data = {
            "hash": "0xincoming",
            "from": "0x9999999999999999999999999999999999999999",
            "to": WALLET,
            "value": "500000000000000000",
            "gasUsed": "21000",
            "gasPrice": "10000000000",
            "chain": "ethereum",
        }
        parser = GenericEVMParser()
        transfers = extract_transfers_from_etherscan(tx_data, "ethereum")
        ctx = TransactionContext(transfers, {WALLET})

        result = parser.parse(tx_data, ctx)
        _assert_balanced(result)

        # Wallet should have a positive native_asset split (incoming)
        native_splits = [s for s in result.splits if s.account_subtype == "native_asset"]
        assert any(s.quantity > 0 for s in native_splits)

    def test_parser_name(self):
        assert GenericEVMParser.PARSER_NAME == "GenericEVMParser"
