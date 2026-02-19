import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TransactionResponse(BaseModel):
    id: int
    wallet_id: uuid.UUID
    chain: str
    tx_hash: str
    block_number: Optional[int]
    timestamp: Optional[int]
    from_addr: Optional[str]
    to_addr: Optional[str]
    value_wei: Optional[int]
    gas_used: Optional[int]
    status: str
    entry_type: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionDetail(TransactionResponse):
    tx_data: Optional[str]
    updated_at: datetime


class TransactionList(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    limit: int
    offset: int
