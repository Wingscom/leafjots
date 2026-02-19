import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from cryptotax.domain.enums import Chain, Exchange


class WalletCreate(BaseModel):
    chain: Chain
    address: str
    label: Optional[str] = None

    @field_validator("address")
    @classmethod
    def normalize_address(cls, v: str) -> str:
        return v.strip().lower()


class CEXWalletCreate(BaseModel):
    exchange: Exchange
    api_key: str = ""
    api_secret: str = ""
    label: Optional[str] = None


class WalletResponse(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    wallet_type: str
    chain: Optional[str] = None
    address: Optional[str] = None
    exchange: Optional[str] = None
    label: Optional[str]
    sync_status: str
    last_block_loaded: Optional[int] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WalletStatusResponse(BaseModel):
    id: uuid.UUID
    sync_status: str
    last_block_loaded: Optional[int] = None
    last_synced_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WalletList(BaseModel):
    wallets: list[WalletResponse]
    total: int
