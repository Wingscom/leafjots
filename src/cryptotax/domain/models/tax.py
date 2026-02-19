"""Domain types for FIFO capital gains and Vietnam tax calculation."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from cryptotax.domain.enums.tax import TaxExemptionReason, TradeSide


class Trade(BaseModel):
    """A BUY or SELL event derived from journal splits."""

    symbol: str
    side: TradeSide
    quantity: Decimal  # Always positive
    price_usd: Decimal  # Per-unit price
    value_usd: Decimal  # Total value (quantity * price_usd)
    timestamp: datetime
    journal_entry_id: uuid.UUID
    description: str = ""


class OpenLot(BaseModel):
    """An unmatched (or partially matched) buy position."""

    symbol: str
    buy_trade: Trade
    remaining_quantity: Decimal
    cost_basis_per_unit_usd: Decimal  # = buy_trade.price_usd


class ClosedLot(BaseModel):
    """A realized gain/loss from FIFO matching a sell against a buy."""

    symbol: str
    buy_trade: Trade
    sell_trade: Trade
    quantity: Decimal  # Matched quantity
    cost_basis_usd: Decimal  # quantity * buy price
    proceeds_usd: Decimal  # quantity * sell price
    gain_usd: Decimal  # proceeds - cost_basis
    holding_days: int  # (sell_timestamp - buy_timestamp).days


class TaxableTransfer(BaseModel):
    """A transfer subject to Vietnam 0.1% tax."""

    timestamp: datetime
    symbol: str
    quantity: Decimal
    value_vnd: Decimal
    tax_amount_vnd: Decimal  # value_vnd * 0.001
    exemption_reason: TaxExemptionReason | None = None  # None = taxable


class TaxSummary(BaseModel):
    """Summary of tax calculation for a period."""

    period_start: datetime
    period_end: datetime
    total_realized_gain_usd: Decimal = Decimal(0)
    total_transfer_tax_vnd: Decimal = Decimal(0)
    total_exempt_vnd: Decimal = Decimal(0)
    closed_lots: list[ClosedLot] = []
    open_lots: list[OpenLot] = []
    taxable_transfers: list[TaxableTransfer] = []
