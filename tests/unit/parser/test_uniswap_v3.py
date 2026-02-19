"""Tests for UniswapV3Parser — can_parse, swap, LP add/remove."""

from cryptotax.parser.defi.uniswap_v3 import (
    DECREASE_LIQUIDITY,
    MINT_SELECTOR,
    UNISWAP_V3_NFT_MANAGER,
    UNISWAP_V3_ROUTERS,
    UniswapV3Parser,
)
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.types import RawTransfer

WALLET = "0x1111111111111111111111111111111111111111"
ROUTER = UNISWAP_V3_ROUTERS["ethereum"][0]  # SwapRouter
NFT_MGR = UNISWAP_V3_NFT_MANAGER["ethereum"]


def _make_tx(to: str, selector: str, value: str = "0") -> dict:
    return {
        "hash": "0xuni_test",
        "from": WALLET,
        "to": to,
        "value": value,
        "gasUsed": "180000",
        "gasPrice": "20000000000",
        "chain": "ethereum",
        "input": selector + "0" * 56,
    }


def _make_context(transfers: list[RawTransfer]) -> TransactionContext:
    return TransactionContext(transfers, {WALLET})


class TestUniswapV3CanParse:
    def test_matches_swap_router(self):
        parser = UniswapV3Parser()
        tx_data = {"to": ROUTER, "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_matches_nft_manager(self):
        parser = UniswapV3Parser()
        tx_data = {"to": NFT_MGR, "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_matches_universal_router(self):
        parser = UniswapV3Parser()
        universal = UNISWAP_V3_ROUTERS["ethereum"][2]  # UniversalRouter
        tx_data = {"to": universal, "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is True

    def test_rejects_unknown_address(self):
        parser = UniswapV3Parser()
        tx_data = {"to": "0xunknown", "chain": "ethereum"}
        assert parser.can_parse(tx_data, _make_context([])) is False


class TestUniswapV3Swap:
    def test_swap_produces_net_flow_splits(self):
        parser = UniswapV3Parser()
        # exactInputSingle selector
        tx_data = _make_tx(ROUTER, "0x414bf389", "1000000000000000000")
        transfers = [
            RawTransfer(from_address=WALLET, to_address=ROUTER, value=10**18, symbol="ETH", transfer_type="native"),
            RawTransfer(token_address="0xusdc", from_address=ROUTER, to_address=WALLET, value=2500 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        assert len(result.splits) > 0
        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        # Net flows: ETH out, USDC in. The native ETH outflow also uses native_asset.
        eth_splits = [s for s in result.splits if s.symbol == "ETH" and s.account_subtype == "native_asset"]
        usdc_splits = [s for s in non_gas if s.symbol == "USDC"]
        assert any(s.quantity < 0 for s in eth_splits), "Should have ETH outflow"
        assert any(s.quantity > 0 for s in usdc_splits), "Should have USDC inflow"

    def test_swap_entry_type(self):
        parser = UniswapV3Parser()
        tx_data = _make_tx(ROUTER, "0x414bf389")
        transfers = [
            RawTransfer(token_address="0xweth", from_address=WALLET, to_address=ROUTER, value=10**18, decimals=18, symbol="WETH", transfer_type="erc20"),
            RawTransfer(token_address="0xusdc", from_address=ROUTER, to_address=WALLET, value=2500 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)
        assert result.entry_type == "SWAP"


class TestUniswapV3LPAdd:
    def test_mint_produces_deposit_splits(self):
        parser = UniswapV3Parser()
        tx_data = _make_tx(NFT_MGR, MINT_SELECTOR)
        transfers = [
            RawTransfer(token_address="0xusdc", from_address=WALLET, to_address=NFT_MGR, value=1000 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
            RawTransfer(token_address="0xweth", from_address=WALLET, to_address=NFT_MGR, value=10**18, decimals=18, symbol="WETH", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        # Each token: erc20_token(-) + protocol_asset(+) = 4 splits
        assert len(non_gas) == 4
        erc20_out = [s for s in non_gas if s.account_subtype == "erc20_token"]
        protocol_in = [s for s in non_gas if s.account_subtype == "protocol_asset"]
        assert all(s.quantity < 0 for s in erc20_out)
        assert all(s.quantity > 0 for s in protocol_in)
        assert result.entry_type == "DEPOSIT"


class TestUniswapV3LPRemove:
    def test_decrease_produces_withdrawal_splits(self):
        parser = UniswapV3Parser()
        tx_data = _make_tx(NFT_MGR, DECREASE_LIQUIDITY)
        transfers = [
            RawTransfer(token_address="0xusdc", from_address=NFT_MGR, to_address=WALLET, value=1000 * 10**6, decimals=6, symbol="USDC", transfer_type="erc20"),
            RawTransfer(token_address="0xweth", from_address=NFT_MGR, to_address=WALLET, value=10**18, decimals=18, symbol="WETH", transfer_type="erc20"),
        ]
        ctx = _make_context(transfers)
        result = parser.parse(tx_data, ctx)

        non_gas = [s for s in result.splits if s.account_subtype not in ("native_asset", "wallet_expense")]
        assert len(non_gas) == 4
        protocol_out = [s for s in non_gas if s.account_subtype == "protocol_asset"]
        erc20_in = [s for s in non_gas if s.account_subtype == "erc20_token"]
        assert all(s.quantity < 0 for s in protocol_out)
        assert all(s.quantity > 0 for s in erc20_in)
        assert result.entry_type == "WITHDRAWAL"


class TestUniswapV3UnknownNFTSelector:
    def test_unknown_nft_selector_falls_through(self):
        parser = UniswapV3Parser()
        tx_data = _make_tx(NFT_MGR, "0xdeadbeef")
        ctx = _make_context([])
        result = parser.parse(tx_data, ctx)
        assert result.splits == []
