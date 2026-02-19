"""GenericEVMParser — Layer 1 fallback that handles gas fees + simple transfers."""

from decimal import Decimal

from cryptotax.domain.enums import EntryType
from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.gas import make_gas_splits, native_symbol
from cryptotax.parser.utils.types import ParsedSplit, ParseResult


class GenericEVMParser(BaseParser):
    """Always-fallback parser. Handles:
    1. Gas fee -> native_asset / expense_gas splits
    2. Simple native transfers -> native_asset / external_transfer splits
    3. Anything remaining -> UNKNOWN entry type
    """

    PARSER_NAME = "GenericEVMParser"
    ENTRY_TYPE = EntryType.TRANSFER

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        return True  # Always matches as fallback

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        splits: list[ParsedSplit] = []
        chain = tx_data.get("chain", "ethereum")
        symbol = native_symbol(chain)

        # 1. Gas fee
        gas_splits = make_gas_splits(tx_data, chain, context)
        splits.extend(gas_splits)

        # 2. Net transfer flows for wallet addresses
        net = context.net_flows()
        has_value_transfer = False

        for addr, token_flows in net.items():
            for tok_symbol, qty in token_flows.items():
                if qty == Decimal(0):
                    continue
                has_value_transfer = True

                if tok_symbol == symbol and qty < 0:
                    splits.append(ParsedSplit(
                        account_subtype="native_asset",
                        account_params={"chain": chain},
                        quantity=qty,
                        symbol=tok_symbol,
                    ))
                    splits.append(ParsedSplit(
                        account_subtype="external_transfer",
                        account_params={"chain": chain, "ext_address": self._find_counterpart(tx_data, addr)},
                        quantity=-qty,
                        symbol=tok_symbol,
                    ))
                elif tok_symbol == symbol and qty > 0:
                    splits.append(ParsedSplit(
                        account_subtype="native_asset",
                        account_params={"chain": chain},
                        quantity=qty,
                        symbol=tok_symbol,
                    ))
                    splits.append(ParsedSplit(
                        account_subtype="external_transfer",
                        account_params={"chain": chain, "ext_address": self._find_counterpart(tx_data, addr)},
                        quantity=-qty,
                        symbol=tok_symbol,
                    ))
                else:
                    # ERC20 token — find actual counterpart address
                    splits.append(ParsedSplit(
                        account_subtype="erc20_token",
                        account_params={"chain": chain, "symbol": tok_symbol},
                        quantity=qty,
                        symbol=tok_symbol,
                    ))
                    splits.append(ParsedSplit(
                        account_subtype="external_transfer",
                        account_params={"chain": chain, "ext_address": self._find_counterpart(tx_data, addr)},
                        quantity=-qty,
                        symbol=tok_symbol,
                    ))

        # Determine entry type immutably (no more self.ENTRY_TYPE mutation)
        if not has_value_transfer and gas_splits:
            entry_type = EntryType.GAS_FEE
        elif not has_value_transfer and not gas_splits:
            entry_type = EntryType.UNKNOWN
        else:
            entry_type = EntryType.TRANSFER

        return self._make_result(splits, entry_type)

    def _find_counterpart(self, tx_data: dict, wallet_addr: str) -> str:
        """Find the non-wallet address in a transfer."""
        from_addr = tx_data.get("from", "").lower()
        to_addr = tx_data.get("to", "").lower()
        if from_addr == wallet_addr.lower():
            return to_addr
        return from_addr
