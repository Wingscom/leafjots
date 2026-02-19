"""Gas fee calculation utilities."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptotax.parser.utils.context import TransactionContext
    from cryptotax.parser.utils.types import ParsedSplit

# Native token symbol per chain
NATIVE_SYMBOLS: dict[str, str] = {
    "ethereum": "ETH",
    "arbitrum": "ETH",
    "optimism": "ETH",
    "base": "ETH",
    "polygon": "MATIC",
    "bsc": "BNB",
    "avalanche": "AVAX",
    "solana": "SOL",
}


def native_symbol(chain: str) -> str:
    return NATIVE_SYMBOLS.get(chain, "ETH")


def calculate_gas_fee_wei(tx_data: dict, chain: str = "ethereum") -> int:
    """Calculate gas fee in smallest unit (wei for EVM, lamports for Solana).

    EVM: gasUsed × gasPrice + l1Fee (for L2s).
    Solana: meta.fee (already in lamports).
    """
    if chain == "solana":
        meta = tx_data.get("meta", {})
        return int(meta.get("fee", 0)) if meta else 0

    gas_used = int(tx_data.get("gasUsed", 0))
    gas_price = int(tx_data.get("gasPrice", 0))
    gas_fee = gas_used * gas_price

    # L2 l1Fee (Optimism, Base, Arbitrum)
    l1_fee = tx_data.get("l1Fee")
    if l1_fee is not None:
        if isinstance(l1_fee, str):
            l1_fee = int(l1_fee, 16) if l1_fee.startswith("0x") else int(l1_fee)
        gas_fee += l1_fee

    return gas_fee


def calculate_gas_fee_decimal(tx_data: dict, chain: str = "ethereum", native_decimals: int = 18) -> Decimal:
    """Calculate gas fee as a Decimal (human-readable units)."""
    wei = calculate_gas_fee_wei(tx_data, chain)
    if wei == 0:
        return Decimal(0)
    return Decimal(str(wei)) / Decimal(10) ** native_decimals


def make_gas_splits(tx_data: dict, chain: str, context: TransactionContext) -> list[ParsedSplit]:
    """Create gas fee split pair if TX sender is our wallet.

    Returns [native_asset(-fee), wallet_expense(+fee)] or [] if not applicable.
    """
    from cryptotax.parser.utils.types import ParsedSplit

    from_addr = tx_data.get("from", "").lower()
    if not context.is_wallet(from_addr):
        return []

    native_decimals = 9 if chain == "solana" else 18
    gas_fee = calculate_gas_fee_decimal(tx_data, chain, native_decimals)
    if gas_fee <= 0:
        return []

    symbol = native_symbol(chain)
    return [
        ParsedSplit(
            account_subtype="native_asset",
            account_params={"chain": chain},
            quantity=-gas_fee,
            symbol=symbol,
        ),
        ParsedSplit(
            account_subtype="wallet_expense",
            account_params={"chain": chain, "label": "Gas Fees"},
            quantity=gas_fee,
            symbol=symbol,
        ),
    ]
