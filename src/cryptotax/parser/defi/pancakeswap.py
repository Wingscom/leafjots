"""PancakeSwap Parser — swaps on BSC (and Ethereum) via PancakeSwap V3 routers.

PancakeSwap V3 is a Uniswap V3 fork with identical swap interface.
Uses net_flows approach (same as UniswapV3Parser) for reliable swap detection.
"""

from decimal import Decimal

from cryptotax.domain.enums import EntryType
from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.gas import make_gas_splits, native_symbol
from cryptotax.parser.utils.types import ParsedSplit, ParseResult

# Known PancakeSwap router addresses per chain (all lowercase)
PANCAKESWAP_ROUTERS: dict[str, list[str]] = {
    "bsc": [
        "0x13f4ea83d0bd40e75c8222255bc855a974568dd4",  # SmartRouter
        "0x1b81d678ffb9c0263b24a97847620c99d213eb14",  # V3 SwapRouter
    ],
    "ethereum": [
        "0x13f4ea83d0bd40e75c8222255bc855a974568dd4",  # SmartRouter (Ethereum deployment)
    ],
}


def _all_known_addresses(chain: str) -> set[str]:
    return set(PANCAKESWAP_ROUTERS.get(chain, []))


class PancakeSwapParser(BaseParser):
    """Handles PancakeSwap swaps via net-flow detection."""

    PARSER_NAME = "PancakeSwapParser"
    ENTRY_TYPE = EntryType.SWAP

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        to_addr = tx_data.get("to", "").lower()
        chain = tx_data.get("chain", "bsc")
        return to_addr in _all_known_addresses(chain)

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        chain = tx_data.get("chain", "bsc")
        splits: list[ParsedSplit] = list(make_gas_splits(tx_data, chain, context))

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
                splits.append(ParsedSplit(
                    account_subtype=subtype,
                    account_params=params,
                    quantity=qty,
                    symbol=tok_symbol,
                ))

        return self._make_result(splits)
