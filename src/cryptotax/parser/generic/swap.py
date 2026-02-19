"""GenericSwapParser — Layer 2 detects token A↔B swap patterns."""

from decimal import Decimal

from cryptotax.domain.enums import EntryType
from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.gas import make_gas_splits, native_symbol
from cryptotax.parser.utils.types import ParsedSplit, ParseResult


class GenericSwapParser(BaseParser):
    """Detects swap pattern: wallet has exactly 1 token out + 1 token in (different tokens).

    Works for any DEX (Uniswap, Curve, PancakeSwap, etc.) without knowing the protocol.
    """

    PARSER_NAME = "GenericSwapParser"
    ENTRY_TYPE = EntryType.SWAP

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        net = context.net_flows()
        for addr, flows in net.items():
            if not context.is_wallet(addr):
                continue
            outflows = [s for s, amt in flows.items() if amt < 0]
            inflows = [s for s, amt in flows.items() if amt > 0]
            if len(outflows) >= 1 and len(inflows) >= 1:
                # At least one token out and one token in — swap pattern
                out_symbols = set(outflows)
                in_symbols = set(inflows)
                if out_symbols != in_symbols:
                    return True
        return False

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        splits: list[ParsedSplit] = []
        chain = tx_data.get("chain", "ethereum")
        nat_sym = native_symbol(chain)

        # Gas fee first
        splits.extend(make_gas_splits(tx_data, chain, context))

        # Find swap flows
        net = context.net_flows()
        for addr, flows in net.items():
            if not context.is_wallet(addr):
                continue

            for tok_symbol, qty in flows.items():
                if qty == Decimal(0):
                    continue

                if tok_symbol == nat_sym:
                    subtype = "native_asset"
                    params: dict = {"chain": chain}
                else:
                    subtype = "erc20_token"
                    params = {"chain": chain, "symbol": tok_symbol}

                splits.append(ParsedSplit(
                    account_subtype=subtype,
                    account_params=params,
                    quantity=qty,
                    symbol=tok_symbol,
                ))

        return self._make_result(splits)
