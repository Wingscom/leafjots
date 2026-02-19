from decimal import Decimal

from pydantic import BaseModel


class ParseTestRequest(BaseModel):
    tx_hash: str


class ParsedSplitResponse(BaseModel):
    account_label: str
    account_type: str
    symbol: str
    quantity: Decimal


class ParseTestResponse(BaseModel):
    tx_hash: str
    parser_name: str
    entry_type: str
    splits: list[ParsedSplitResponse]
    balanced: bool
    warnings: list[str]


class ParseWalletResponse(BaseModel):
    processed: int
    errors: int
    total: int


class ParseStatsResponse(BaseModel):
    total: int
    parsed: int
    errors: int
    unknown: int
