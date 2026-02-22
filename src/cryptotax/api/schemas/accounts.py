import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class AccountResponse(BaseModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    account_type: str
    subtype: str
    symbol: Optional[str] = None
    protocol: Optional[str] = None
    balance_type: Optional[str] = None
    label: Optional[str] = None
    current_balance: Decimal = Decimal(0)
    balance_usd: Decimal = Decimal(0)
    balance_vnd: Decimal = Decimal(0)

    model_config = {"from_attributes": True}


class AccountList(BaseModel):
    accounts: list[AccountResponse]


class AccountHistorySplit(BaseModel):
    id: uuid.UUID
    journal_entry_id: uuid.UUID
    quantity: Decimal
    value_usd: Optional[Decimal] = None
    value_vnd: Optional[Decimal] = None
    created_at: str

    model_config = {"from_attributes": True}


class AccountHistory(BaseModel):
    splits: list[AccountHistorySplit]
    total: int
    limit: int
    offset: int
