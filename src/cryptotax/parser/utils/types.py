"""Core data types for the parser engine."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class RawTransfer(BaseModel):
    """A single token transfer extracted from TX data (before accounting resolution)."""

    token_address: str | None = None  # None = native (ETH/MATIC/etc.)
    from_address: str
    to_address: str
    value: int  # wei / smallest unit
    decimals: int = 18
    symbol: str = "ETH"
    transfer_type: str = "native"  # native | internal | erc20 | nft


class EventData(BaseModel):
    """A decoded contract event from TX logs."""

    event: str  # event name, e.g. "Transfer", "Supply"
    address: str  # contract that emitted
    log_index: int = 0
    args: dict[str, Any] = {}


class ParsedSplit(BaseModel):
    """One leg of a journal entry produced by a parser. Quantity MUST sum to 0 across all splits per symbol."""

    account_subtype: str  # maps to Account STI: native_asset, erc20_token, etc.
    account_params: dict[str, Any] = {}  # extra kwargs for AccountMapper lookup
    quantity: Decimal  # positive = increase, negative = decrease
    symbol: str


class ParseResult(BaseModel):
    """Immutable result from a parser.parse() call. Replaces mutable self.ENTRY_TYPE."""

    splits: list[ParsedSplit]
    entry_type: str  # EntryType value (e.g. "SWAP", "TRANSFER")
    parser_name: str
