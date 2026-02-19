"""Schemas for /api/reports endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportGenerateRequest(BaseModel):
    entity_id: Optional[uuid.UUID] = None
    start_date: str
    end_date: str


class ReportResponse(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    status: str
    filename: Optional[str] = None
    generated_at: Optional[datetime] = None
    error_message: Optional[str] = None
