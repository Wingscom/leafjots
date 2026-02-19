"""Schemas for /api/imports endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CsvImportResponse(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    exchange: str
    filename: str
    row_count: int
    parsed_count: int
    error_count: int
    status: str
    created_at: datetime


class CsvImportListResponse(BaseModel):
    imports: list[CsvImportResponse]
    total: int


class CsvImportRowResponse(BaseModel):
    id: uuid.UUID
    row_number: int
    utc_time: str
    account: str
    operation: str
    coin: str
    change: str
    remark: Optional[str] = None
    status: str
    error_message: Optional[str] = None


class CsvImportDetailResponse(CsvImportResponse):
    rows: list[CsvImportRowResponse]


class UploadResponse(BaseModel):
    import_id: uuid.UUID
    filename: str
    row_count: int
    status: str


class ParseImportResponse(BaseModel):
    import_id: uuid.UUID
    total: int
    parsed: int
    errors: int
    skipped: int


class ImportSummaryResponse(BaseModel):
    import_id: uuid.UUID
    total: int
    operation_counts: dict[str, int]
    status_counts: dict[str, int]
