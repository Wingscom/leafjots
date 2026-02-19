"""Pendle Parser — router swaps, SY mint/redeem, YT yield claiming.

Pendle uses a router contract for swaps. SY (Standardized Yield) tokens wrap
underlying yield-bearing tokens. PT (Principal Token) and YT (Yield Token)
represent fixed and variable yield positions.

Uses net-flow analysis for router swaps, transfer consumption for SY/YT ops.
"""

from decimal import Decimal

from cryptotax.domain.enums import EntryType
from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.handlers.common import make_yield_splits
from cryptotax.parser.handlers.wrap import make_wrap_splits, make_unwrap_splits
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.gas import make_gas_splits, native_symbol
from cryptotax.parser.utils.types import ParsedSplit, ParseResult

# Pendle Router V3 per chain
PENDLE_ROUTER: dict[str, str] = {
    "ethereum": "0x00000000005bbb0ef59571e58418f9a4357b68a0",
    "arbitrum": "0x00000000005bbb0ef59571e58418f9a4357b68a0",
}

# Pendle Router V4 (newer deployments)
PENDLE_ROUTER_V4: dict[str, str] = {
    "ethereum": "0x888888888889758f76e7103c6cbf23abbf58f946",
    "arbitrum": "0x888888888889758f76e7103c6cbf23abbf58f946",
}

# Function selectors
# Router swaps
SWAP_EXACT_TOKEN_FOR_PT = "0x3a369032"
SWAP_EXACT_PT_FOR_TOKEN = "0x773a3d5c"
SWAP_EXACT_TOKEN_FOR_YT = "0x462b3c2d"
SWAP_EXACT_YT_FOR_TOKEN = "0x8682cd41"
# SY operations
MINT_SY_FROM_TOKEN = "0x69b16f40"
REDEEM_SY_TO_TOKEN = "0x4d99ee94"
# YT yield
REDEEM_DUE_INTEREST_AND_REWARDS = "0x2a7a1662"

SWAP_SELECTORS = {
    SWAP_EXACT_TOKEN_FOR_PT,
    SWAP_EXACT_PT_FOR_TOKEN,
    SWAP_EXACT_TOKEN_FOR_YT,
    SWAP_EXACT_YT_FOR_TOKEN,
}

PROTOCOL = "pendle"


def _all_pendle_addresses(chain: str) -> set[str]:
    """All Pendle router addresses for a chain."""
    addrs: set[str] = set()
    if chain in PENDLE_ROUTER:
        addrs.add(PENDLE_ROUTER[chain])
    if chain in PENDLE_ROUTER_V4:
        addrs.add(PENDLE_ROUTER_V4[chain])
    return addrs


class PendleParser(BaseParser):
    """Handles Pendle router swaps, SY mint/redeem, and YT yield claiming."""

    PARSER_NAME = "PendleParser"
    ENTRY_TYPE = EntryType.SWAP

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        to_addr = tx_data.get("to", "").lower()
        chain = tx_data.get("chain", "ethereum")
        return to_addr in _all_pendle_addresses(chain)

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        chain = tx_data.get("chain", "ethereum")
        input_data = tx_data.get("input", "")
        selector = input_data[:10].lower() if len(input_data) >= 10 else ""

        splits = list(make_gas_splits(tx_data, chain, context))

        if selector in SWAP_SELECTORS:
            entry_type = EntryType.SWAP
            splits.extend(self._handle_swap(tx_data, context, chain))
        elif selector == MINT_SY_FROM_TOKEN:
            entry_type = EntryType.DEPOSIT
            splits.extend(self._handle_sy_mint(tx_data, context, chain))
        elif selector == REDEEM_SY_TO_TOKEN:
            entry_type = EntryType.WITHDRAWAL
            splits.extend(self._handle_sy_redeem(tx_data, context, chain))
        elif selector == REDEEM_DUE_INTEREST_AND_REWARDS:
            entry_type = EntryType.TRANSFER
            splits.extend(self._handle_yield_claim(tx_data, context, chain))
        else:
            # Unknown selector — use net flows as fallback
            entry_type = EntryType.SWAP
            splits.extend(self._handle_swap(tx_data, context, chain))

        return self._make_result(splits, entry_type)

    def _handle_swap(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Net-flow approach for router swaps (handles multi-hop)."""
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

    def _handle_sy_mint(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Mint SY: send underlying token, receive SY token (wrap pattern)."""
        wallet = tx_data.get("from", "").lower()

        # Underlying token sent
        token_out = context.pop_transfer(from_address=wallet, transfer_type="erc20")
        if token_out is None:
            return []
        out_qty = Decimal(str(token_out.value)) / Decimal(10) ** token_out.decimals

        # SY token received
        sy_in = context.pop_transfer(to_address=wallet, transfer_type="erc20")
        sy_qty = out_qty
        sy_symbol = f"SY-{token_out.symbol}"
        if sy_in is not None:
            sy_qty = Decimal(str(sy_in.value)) / Decimal(10) ** sy_in.decimals
            sy_symbol = sy_in.symbol

        return make_wrap_splits(token_out.symbol, out_qty, sy_symbol, sy_qty, chain)

    def _handle_sy_redeem(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Redeem SY: burn SY token, receive underlying (unwrap pattern)."""
        wallet = tx_data.get("from", "").lower()

        # SY token sent (burn)
        sy_out = context.pop_transfer(from_address=wallet, transfer_type="erc20")
        if sy_out is None:
            return []
        sy_qty = Decimal(str(sy_out.value)) / Decimal(10) ** sy_out.decimals

        # Underlying received
        token_in = context.pop_transfer(to_address=wallet, transfer_type="erc20")
        token_qty = sy_qty
        token_symbol = sy_out.symbol.replace("SY-", "")
        if token_in is not None:
            token_qty = Decimal(str(token_in.value)) / Decimal(10) ** token_in.decimals
            token_symbol = token_in.symbol

        return make_unwrap_splits(sy_out.symbol, sy_qty, token_symbol, token_qty, chain)

    def _handle_yield_claim(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Claim YT yield: income recognition for accrued interest/rewards."""
        wallet = tx_data.get("from", "").lower()
        splits: list[ParsedSplit] = []

        # Consume all incoming transfers as yield
        while True:
            transfer = context.pop_transfer(to_address=wallet, transfer_type="erc20")
            if transfer is None:
                break
            qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals
            if qty > 0:
                splits.extend(make_yield_splits(transfer.symbol, qty, PROTOCOL, chain, tag="Pendle Yield"))

        return splits
