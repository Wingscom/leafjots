import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ParseErrorResponse(BaseModel):
    id: uuid.UUID
    transaction_id: Optional[int] = None
    wallet_id: Optional[uuid.UUID] = None
    tx_hash: Optional[str] = None
    chain: Optional[str] = None
    error_type: str
    message: Optional[str] = None
    stack_trace: Optional[str] = None
    resolved: bool
    created_at: datetime
    diagnostic_data: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class ErrorList(BaseModel):
    errors: list[ParseErrorResponse]
    total: int
    limit: int
    offset: int


class ErrorSummaryResponse(BaseModel):
    total: int = 0
    by_type: dict[str, int] = {}
    resolved: int = 0
    unresolved: int = 0
