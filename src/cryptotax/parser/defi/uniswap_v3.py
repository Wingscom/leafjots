"""Uniswap V3 Parser — swaps via routers and LP via NonfungiblePositionManager.

For simple swaps, GenericSwapParser already works. This parser adds:
- Correct protocol attribution (entry shows "UniswapV3Parser")
- Multi-hop swap handling via net_flows
- LP position management (Mint/Burn/Collect)
"""

from decimal import Decimal

from cryptotax.domain.enums import EntryType
from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.gas import make_gas_splits, native_symbol
from cryptotax.parser.utils.types import ParsedSplit, ParseResult

# Known addresses per chain (all lowercase)
UNISWAP_V3_ROUTERS: dict[str, list[str]] = {
    "ethereum": [
        "0xe592427a0aece92de3edee1f18e0157c05861564",  # SwapRouter
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",  # SwapRouter02
        "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",  # UniversalRouter
    ],
    "arbitrum": [
        "0xe592427a0aece92de3edee1f18e0157c05861564",
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",
    ],
    "polygon": [
        "0xe592427a0aece92de3edee1f18e0157c05861564",
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",
    ],
    "optimism": [
        "0xe592427a0aece92de3edee1f18e0157c05861564",
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",
    ],
    "base": [
        "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",
    ],
}

UNISWAP_V3_NFT_MANAGER: dict[str, str] = {
    "ethereum": "0xc36442b4a4522e871399cd717abdd847ab11fe88",
    "arbitrum": "0xc36442b4a4522e871399cd717abdd847ab11fe88",
    "polygon": "0xc36442b4a4522e871399cd717abdd847ab11fe88",
    "optimism": "0xc36442b4a4522e871399cd717abdd847ab11fe88",
    "base": "0x03a520b32c04bf3beef7beb72e919cf822ed34f1",
}

PROTOCOL = "uniswap_v3"

# LP function selectors
MINT_SELECTOR = "0x88316456"
INCREASE_LIQUIDITY = "0x219f5d17"
DECREASE_LIQUIDITY = "0x0c49ccbe"
COLLECT_SELECTOR = "0xfc6f7865"
MULTICALL_SELECTOR = "0xac9650d8"

LP_ADD_SELECTORS = {MINT_SELECTOR, INCREASE_LIQUIDITY}
LP_REMOVE_SELECTORS = {DECREASE_LIQUIDITY, COLLECT_SELECTOR}


def _all_known_addresses(chain: str) -> set[str]:
    """All Uniswap V3 addresses for a chain (routers + NFT manager)."""
    addrs = set(UNISWAP_V3_ROUTERS.get(chain, []))
    nft = UNISWAP_V3_NFT_MANAGER.get(chain)
    if nft:
        addrs.add(nft)
    return addrs


class UniswapV3Parser(BaseParser):
    """Handles Uniswap V3 swaps and LP operations."""

    PARSER_NAME = "UniswapV3Parser"
    ENTRY_TYPE = EntryType.SWAP

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        to_addr = tx_data.get("to", "").lower()
        chain = tx_data.get("chain", "ethereum")
        return to_addr in _all_known_addresses(chain)

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        chain = tx_data.get("chain", "ethereum")
        to_addr = tx_data.get("to", "").lower()
        input_data = tx_data.get("input", "")
        selector = input_data[:10].lower() if len(input_data) >= 10 else ""

        splits = list(make_gas_splits(tx_data, chain, context))

        nft_mgr = UNISWAP_V3_NFT_MANAGER.get(chain, "")

        if to_addr == nft_mgr:
            # LP operation
            if selector in LP_ADD_SELECTORS:
                entry_type = EntryType.DEPOSIT
                splits.extend(self._handle_lp_add(tx_data, context, chain))
            elif selector in LP_REMOVE_SELECTORS:
                entry_type = EntryType.WITHDRAWAL
                splits.extend(self._handle_lp_remove(tx_data, context, chain))
            elif selector == MULTICALL_SELECTOR:
                entry_type = EntryType.SWAP
                splits.extend(self._handle_net_flows(tx_data, context, chain))
            else:
                return self._make_result([])  # Fall through
        else:
            # Router swap — use net flows (handles multi-hop)
            entry_type = EntryType.SWAP
            splits.extend(self._handle_net_flows(tx_data, context, chain))

        return self._make_result(splits, entry_type)

    def _handle_net_flows(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Net-flow approach: works for swaps, multicalls, and complex routing."""
        splits: list[ParsedSplit] = []
        nat_sym = native_symbol(chain)
        net = context.net_flows()

        for addr, flows in net.items():
            if not context.is_wallet(addr):
                continue
            for tok_symbol, qty in flows.items():
                if qty == Decimal(0):
                    continue
                subtype = "native_asset" if tok_symbol == nat_sym else "erc20_token"
                params = {"chain": chain} if tok_symbol == nat_sym else {"chain": chain, "symbol": tok_symbol}
                splits.append(ParsedSplit(account_subtype=subtype, account_params=params, quantity=qty, symbol=tok_symbol))

        return splits

    def _handle_lp_add(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Mint/IncreaseLiquidity: tokens out -> protocol_asset in."""
        splits: list[ParsedSplit] = []
        wallet = tx_data.get("from", "").lower()

        while True:
            transfer = context.pop_transfer(from_address=wallet, transfer_type="erc20")
            if transfer is None:
                break
            qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals
            splits.append(ParsedSplit(
                account_subtype="erc20_token",
                account_params={"chain": chain, "symbol": transfer.symbol},
                quantity=-qty, symbol=transfer.symbol,
            ))
            splits.append(ParsedSplit(
                account_subtype="protocol_asset",
                account_params={"chain": chain, "protocol": PROTOCOL},
                quantity=qty, symbol=transfer.symbol,
            ))

        # Handle refunds (change returned by Uniswap)
        while True:
            refund = context.pop_transfer(to_address=wallet, transfer_type="erc20")
            if refund is None:
                break
            qty = Decimal(str(refund.value)) / Decimal(10) ** refund.decimals
            splits.append(ParsedSplit(
                account_subtype="protocol_asset",
                account_params={"chain": chain, "protocol": PROTOCOL},
                quantity=-qty, symbol=refund.symbol,
            ))
            splits.append(ParsedSplit(
                account_subtype="erc20_token",
                account_params={"chain": chain, "symbol": refund.symbol},
                quantity=qty, symbol=refund.symbol,
            ))

        return splits

    def _handle_lp_remove(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """DecreaseLiquidity/Collect: protocol_asset out -> tokens in."""
        splits: list[ParsedSplit] = []
        wallet = tx_data.get("from", "").lower()

        while True:
            transfer = context.pop_transfer(to_address=wallet, transfer_type="erc20")
            if transfer is None:
                break
            qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals
            splits.append(ParsedSplit(
                account_subtype="protocol_asset",
                account_params={"chain": chain, "protocol": PROTOCOL},
                quantity=-qty, symbol=transfer.symbol,
            ))
            splits.append(ParsedSplit(
                account_subtype="erc20_token",
                account_params={"chain": chain, "symbol": transfer.symbol},
                quantity=qty, symbol=transfer.symbol,
            ))

        return splits
