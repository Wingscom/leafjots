import uuid
from datetime import datetime

from pydantic import BaseModel


class EntityCreateRequest(BaseModel):
    name: str
    base_currency: str = "VND"


class EntityUpdateRequest(BaseModel):
    name: str | None = None
    base_currency: str | None = None


class EntityResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_currency: str
    wallet_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EntityListResponse(BaseModel):
    entities: list[EntityResponse]
    total: int
