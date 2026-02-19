"""Reusable handler for token wrap/unwrap patterns (wstETH, SY tokens, etc.)."""

from decimal import Decimal

from cryptotax.parser.utils.types import ParsedSplit


def make_wrap_splits(
    from_symbol: str,
    from_qty: Decimal,
    to_symbol: str,
    to_qty: Decimal,
    chain: str,
) -> list[ParsedSplit]:
    """Wrap: send token A, receive token B (e.g., stETH -> wstETH).

    from_symbol(-from_qty) / to_symbol(+to_qty)
    """
    return [
        ParsedSplit(
            account_subtype="erc20_token",
            account_params={"chain": chain, "symbol": from_symbol},
            quantity=-from_qty,
            symbol=from_symbol,
        ),
        ParsedSplit(
            account_subtype="erc20_token",
            account_params={"chain": chain, "symbol": to_symbol},
            quantity=to_qty,
            symbol=to_symbol,
        ),
    ]


def make_unwrap_splits(
    from_symbol: str,
    from_qty: Decimal,
    to_symbol: str,
    to_qty: Decimal,
    chain: str,
) -> list[ParsedSplit]:
    """Unwrap: send wrapped token, receive underlying (e.g., wstETH -> stETH).

    from_symbol(-from_qty) / to_symbol(+to_qty)
    """
    return [
        ParsedSplit(
            account_subtype="erc20_token",
            account_params={"chain": chain, "symbol": from_symbol},
            quantity=-from_qty,
            symbol=from_symbol,
        ),
        ParsedSplit(
            account_subtype="erc20_token",
            account_params={"chain": chain, "symbol": to_symbol},
            quantity=to_qty,
            symbol=to_symbol,
        ),
    ]
