"""Reusable handler functions for DeFi accounting patterns.

All functions return balanced list[ParsedSplit] (sum=0 per symbol).
"""

from decimal import Decimal

from cryptotax.parser.utils.types import ParsedSplit


def make_deposit_splits(symbol: str, qty: Decimal, protocol: str, chain: str) -> list[ParsedSplit]:
    """Deposit: token_asset decreases, protocol_asset increases."""
    return [
        ParsedSplit(account_subtype="erc20_token", account_params={"chain": chain, "symbol": symbol}, quantity=-qty, symbol=symbol),
        ParsedSplit(account_subtype="protocol_asset", account_params={"chain": chain, "protocol": protocol}, quantity=qty, symbol=symbol),
    ]


def make_withdrawal_splits(symbol: str, qty: Decimal, protocol: str, chain: str) -> list[ParsedSplit]:
    """Withdraw: protocol_asset decreases, token_asset increases."""
    return [
        ParsedSplit(account_subtype="protocol_asset", account_params={"chain": chain, "protocol": protocol}, quantity=-qty, symbol=symbol),
        ParsedSplit(account_subtype="erc20_token", account_params={"chain": chain, "symbol": symbol}, quantity=qty, symbol=symbol),
    ]


def make_borrow_splits(symbol: str, qty: Decimal, protocol: str, chain: str) -> list[ParsedSplit]:
    """Borrow: debt increases (negative liability), token_asset increases."""
    return [
        ParsedSplit(account_subtype="protocol_debt", account_params={"chain": chain, "protocol": protocol}, quantity=-qty, symbol=symbol),
        ParsedSplit(account_subtype="erc20_token", account_params={"chain": chain, "symbol": symbol}, quantity=qty, symbol=symbol),
    ]


def make_repay_splits(symbol: str, qty: Decimal, protocol: str, chain: str) -> list[ParsedSplit]:
    """Repay: token_asset decreases, debt decreases (positive = reduce liability)."""
    return [
        ParsedSplit(account_subtype="erc20_token", account_params={"chain": chain, "symbol": symbol}, quantity=-qty, symbol=symbol),
        ParsedSplit(account_subtype="protocol_debt", account_params={"chain": chain, "protocol": protocol}, quantity=qty, symbol=symbol),
    ]


def make_yield_splits(symbol: str, qty: Decimal, protocol: str, chain: str, tag: str = "Interest") -> list[ParsedSplit]:
    """Yield/claim: income decreases (negative), token_asset increases."""
    return [
        ParsedSplit(account_subtype="wallet_income", account_params={"chain": chain, "tag": tag}, quantity=-qty, symbol=symbol),
        ParsedSplit(account_subtype="erc20_token", account_params={"chain": chain, "symbol": symbol}, quantity=qty, symbol=symbol),
    ]
