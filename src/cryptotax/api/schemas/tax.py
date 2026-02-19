"""Pydantic schemas for tax API."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TaxCalculateRequest(BaseModel):
    entity_id: uuid.UUID | None = None  # None = use default entity
    start_date: str  # ISO format: "2025-01-01"
    end_date: str  # ISO format: "2025-12-31"


class ClosedLotResponse(BaseModel):
    symbol: str
    quantity: Decimal
    cost_basis_usd: Decimal
    proceeds_usd: Decimal
    gain_usd: Decimal
    holding_days: int
    buy_date: datetime
    sell_date: datetime


class OpenLotResponse(BaseModel):
    symbol: str
    remaining_quantity: Decimal
    cost_basis_per_unit_usd: Decimal
    buy_date: datetime


class TaxableTransferResponse(BaseModel):
    timestamp: datetime
    symbol: str
    quantity: Decimal
    value_vnd: Decimal
    tax_amount_vnd: Decimal
    exemption_reason: str | None = None


class TaxSummaryResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    total_realized_gain_usd: Decimal
    total_transfer_tax_vnd: Decimal
    total_exempt_vnd: Decimal
    closed_lot_count: int
    open_lot_count: int
    taxable_transfer_count: int


class TaxCalculateResponse(BaseModel):
    summary: TaxSummaryResponse
    closed_lots: list[ClosedLotResponse]
    open_lots: list[OpenLotResponse]
    taxable_transfers: list[TaxableTransferResponse]
