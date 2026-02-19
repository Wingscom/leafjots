from cryptotax.parser.generic.swap import GenericSwapParser
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import RawTransfer

WALLET = "0x1111111111111111111111111111111111111111"


def _make_swap_context() -> tuple[dict, TransactionContext]:
    """Simulate a swap: wallet sends 1 ETH, receives 2000 USDC."""
    transfers = [
        RawTransfer(
            token_address=None,
            from_address=WALLET,
            to_address="0xrouter",
            value=10**18,
            decimals=18,
            symbol="ETH",
            transfer_type="native",
        ),
        RawTransfer(
            token_address="0xusdc_contract",
            from_address="0xrouter",
            to_address=WALLET,
            value=2000 * 10**6,
            decimals=6,
            symbol="USDC",
            transfer_type="erc20",
        ),
    ]
    tx_data = {
        "hash": "0xswap",
        "from": WALLET,
        "to": "0xrouter",
        "value": "1000000000000000000",
        "gasUsed": "150000",
        "gasPrice": "25000000000",
        "chain": "ethereum",
    }
    ctx = TransactionContext(transfers, {WALLET})
    return tx_data, ctx


class TestGenericSwapParser:
    def test_can_parse_detects_swap(self):
        parser = GenericSwapParser()
        _, ctx = _make_swap_context()
        assert parser.can_parse({}, ctx) is True

    def test_can_parse_rejects_simple_transfer(self):
        parser = GenericSwapParser()
        transfers = [
            RawTransfer(
                from_address=WALLET,
                to_address="0xbbb",
                value=10**18,
                symbol="ETH",
            ),
        ]
        ctx = TransactionContext(transfers, {WALLET})
        assert parser.can_parse({}, ctx) is False

    def test_parse_swap_produces_splits(self):
        parser = GenericSwapParser()
        tx_data, ctx = _make_swap_context()
        result = parser.parse(tx_data, ctx)

        assert len(result.splits) > 0

        # Gas fee: wallet_expense (+gas) and native_asset (-gas) should pair up
        gas_expense = [s for s in result.splits if s.account_subtype == "wallet_expense"]
        assert len(gas_expense) == 1
        assert gas_expense[0].quantity > 0  # expense is positive

        # Swap: should have ETH outflow and USDC inflow
        non_gas = [s for s in result.splits if s.account_subtype != "wallet_expense"]
        eth_non_gas = [s for s in non_gas if s.symbol == "ETH"]
        usdc_non_gas = [s for s in non_gas if s.symbol == "USDC"]
        assert any(s.quantity < 0 for s in eth_non_gas), "Should have ETH outflow"
        assert any(s.quantity > 0 for s in usdc_non_gas), "Should have USDC inflow"

    def test_parser_name_and_entry_type(self):
        parser = GenericSwapParser()
        assert parser.PARSER_NAME == "GenericSwapParser"
        assert parser.ENTRY_TYPE.value == "SWAP"

    def test_can_parse_same_token_in_out_is_not_swap(self):
        """If same token goes out and comes back, it's not a swap."""
        parser = GenericSwapParser()
        transfers = [
            RawTransfer(from_address=WALLET, to_address="0xpool", value=10**18, symbol="ETH"),
            RawTransfer(from_address="0xpool", to_address=WALLET, value=5 * 10**17, symbol="ETH"),
        ]
        ctx = TransactionContext(transfers, {WALLET})
        # Net flow is -0.5 ETH (only outflow, no different token inflow)
        assert parser.can_parse({}, ctx) is False
