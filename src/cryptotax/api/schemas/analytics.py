"""Pydantic response models for analytics endpoints."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


# ── General Analytics ────────────────────────────────────────────────────────


class CashFlowPeriod(BaseModel):
    period: str
    inflow_usd: float
    inflow_vnd: float
    outflow_usd: float
    outflow_vnd: float
    net_usd: float
    net_vnd: float
    inflow_qty: float = 0.0
    outflow_qty: float = 0.0
    entry_count: int = 0


class KPISummaryResponse(BaseModel):
    total_inflow_usd: float
    total_inflow_vnd: float
    total_outflow_usd: float
    total_outflow_vnd: float
    net_usd: float
    net_vnd: float
    total_entries: int
    total_txs: int
    unique_tokens: int
    unique_protocols: int


class SymbolVolume(BaseModel):
    symbol: Optional[str] = None
    volume_usd: float
    inflow_usd: float
    outflow_usd: float
    tx_count: int
    total_quantity: float = 0.0


class ProtocolVolume(BaseModel):
    protocol: Optional[str] = None
    volume_usd: float
    tx_count: int
    entry_types: list[str] = []


class CompositionItem(BaseModel):
    account_type: str
    subtype: Optional[str] = None
    symbol: Optional[str] = None
    protocol: Optional[str] = None
    balance_qty: float
    balance_usd: float
    balance_vnd: float


class ActivityDay(BaseModel):
    date: Optional[str] = None
    count: int
    volume_usd: float


class EntryTypeBreakdown(BaseModel):
    entry_type: Optional[str] = None
    count: int
    volume_usd: float


class IncomeExpensePeriod(BaseModel):
    period: str
    income_usd: float
    income_vnd: float
    expense_usd: float
    expense_vnd: float
    income_count: int = 0
    expense_count: int = 0


class BalancePeriod(BaseModel):
    period: str
    symbol: str
    period_change: float
    cumulative_qty: float
    period_value_usd: float


class WalletFlow(BaseModel):
    wallet_id: str
    label: Optional[str] = None
    chain: Optional[str] = None
    inflow_usd: float
    outflow_usd: float
    net_usd: float
    tx_count: int


class ChainFlow(BaseModel):
    chain: Optional[str] = None
    inflow_usd: float
    outflow_usd: float
    net_usd: float
    tx_count: int


class OverviewResponse(BaseModel):
    kpi: KPISummaryResponse
    cash_flow: list[CashFlowPeriod]
    composition: list[CompositionItem]


# ── Tax Analytics ─────────────────────────────────────────────────────────────


class RealizedGainsPeriod(BaseModel):
    period: Optional[str] = None
    gains_usd: float
    losses_usd: float
    net_usd: float
    lot_count: int


class GainsBySymbol(BaseModel):
    symbol: Optional[str] = None
    gains_usd: float
    losses_usd: float
    net_usd: float
    lot_count: int
    avg_holding_days: float


class HoldingBucket(BaseModel):
    bucket: str
    lot_count: int
    total_gain_usd: float
    total_quantity: float


class WinnersLosersItem(BaseModel):
    symbol: Optional[str] = None
    net_gain_usd: float
    lot_count: int


class WinnersLosers(BaseModel):
    winners: list[WinnersLosersItem]
    losers: list[WinnersLosersItem]


class TaxBreakdownPeriod(BaseModel):
    period: Optional[str] = None
    taxable_count: int
    exempt_count: int
    total_value_vnd: float
    total_tax_vnd: float


class TaxByCategory(BaseModel):
    category: str
    transfer_count: int
    total_value_vnd: float
    total_tax_vnd: float


class UnrealizedPosition(BaseModel):
    symbol: Optional[str] = None
    remaining_quantity: float
    cost_basis_per_unit_usd: float
    cost_basis_usd: float
    buy_timestamp: Optional[str] = None


class CostBasisItem(BaseModel):
    symbol: Optional[str] = None
    total_quantity: float
    total_cost_usd: float
    avg_cost_per_unit_usd: float
    lot_count: int


def _to_float(val) -> float:
    """Convert Decimal or None to float."""
    if val is None:
        return 0.0
    return float(val)
