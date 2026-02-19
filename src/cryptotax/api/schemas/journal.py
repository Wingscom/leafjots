import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class JournalSplitResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    account_label: str | None = None
    account_type: str | None = None
    symbol: str | None = None
    quantity: Decimal
    value_usd: Optional[Decimal] = None
    value_vnd: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class JournalEntryResponse(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    transaction_id: Optional[int] = None
    entry_type: str
    description: Optional[str] = None
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class JournalEntryDetail(JournalEntryResponse):
    splits: list[JournalSplitResponse] = []


class JournalList(BaseModel):
    entries: list[JournalEntryResponse]
    total: int
    limit: int
    offset: int
