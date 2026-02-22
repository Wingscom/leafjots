"""Analytics API router — 19 endpoints for comprehensive dashboard analytics."""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db, resolve_entity
from cryptotax.api.schemas.analytics import (
    ActivityDay,
    BalancePeriod,
    CashFlowPeriod,
    ChainFlow,
    CompositionItem,
    CostBasisItem,
    EntryTypeBreakdown,
    GainsBySymbol,
    HoldingBucket,
    IncomeExpensePeriod,
    KPISummaryResponse,
    OverviewResponse,
    ProtocolVolume,
    RealizedGainsPeriod,
    SymbolVolume,
    TaxBreakdownPeriod,
    TaxByCategory,
    UnrealizedPosition,
    WalletFlow,
    WinnersLosers,
    WinnersLosersItem,
    _to_float,
)
from cryptotax.db.models.entity import Entity
from cryptotax.db.repos.analytics_repo import AnalyticsRepo
from cryptotax.db.repos.tax_analytics_repo import TaxAnalyticsRepo

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _build_filters(
    entity: Entity,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    wallet_id: Optional[uuid.UUID] = None,
    chain: Optional[str] = None,
    symbol: Optional[str] = None,
    entry_type: Optional[str] = None,
    account_type: Optional[str] = None,
    protocol: Optional[str] = None,
    account_subtype: Optional[str] = None,
) -> dict:
    """Build kwargs dict for AnalyticsRepo method calls."""
    f: dict = {"entity_id": entity.id}
    if date_from is not None:
        f["date_from"] = date_from
    if date_to is not None:
        f["date_to"] = date_to
    if wallet_id is not None:
        f["wallet_id"] = wallet_id
    if chain is not None:
        f["chain"] = chain
    if symbol is not None:
        f["symbol"] = symbol
    if entry_type is not None:
        f["entry_type"] = entry_type
    if account_type is not None:
        f["account_type"] = account_type
    if protocol is not None:
        f["protocol"] = protocol
    if account_subtype is not None:
        f["account_subtype"] = account_subtype
    return f


# ── 1. Overview ──────────────────────────────────────────────────────────────


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
) -> OverviewResponse:
    """Combined KPI + cash flow (last 12 months) + composition snapshot."""
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, date_from=date_from, date_to=date_to)

    kpi_data = await repo.get_kpi_summary(**f)
    cash_flow_data = await repo.get_cash_flow_series(granularity="month", **f)
    composition_data = await repo.get_composition_snapshot(**f)

    kpi = KPISummaryResponse(
        total_inflow_usd=_to_float(kpi_data["total_inflow_usd"]),
        total_inflow_vnd=_to_float(kpi_data["total_inflow_vnd"]),
        total_outflow_usd=_to_float(kpi_data["total_outflow_usd"]),
        total_outflow_vnd=_to_float(kpi_data["total_outflow_vnd"]),
        net_usd=_to_float(kpi_data["net_usd"]),
        net_vnd=_to_float(kpi_data["net_vnd"]),
        total_entries=kpi_data["total_entries"],
        total_txs=kpi_data["total_txs"],
        unique_tokens=kpi_data["unique_tokens"],
        unique_protocols=kpi_data["unique_protocols"],
    )
    cash_flow = [
        CashFlowPeriod(
            period=r["period"] or "",
            inflow_usd=_to_float(r["inflow_usd"]),
            inflow_vnd=_to_float(r["inflow_vnd"]),
            outflow_usd=_to_float(r["outflow_usd"]),
            outflow_vnd=_to_float(r["outflow_vnd"]),
            net_usd=_to_float(r["net_usd"]),
            net_vnd=_to_float(r["net_vnd"]),
            inflow_qty=_to_float(r.get("inflow_qty", 0)),
            outflow_qty=_to_float(r.get("outflow_qty", 0)),
            entry_count=r.get("entry_count", 0),
        )
        for r in cash_flow_data
    ]
    composition = [
        CompositionItem(
            account_type=r["account_type"],
            subtype=r["subtype"],
            symbol=r["symbol"],
            protocol=r["protocol"],
            balance_qty=_to_float(r["total_quantity"]),
            balance_usd=_to_float(r["total_value_usd"]),
            balance_vnd=_to_float(r["total_value_vnd"]),
        )
        for r in composition_data
    ]
    return OverviewResponse(kpi=kpi, cash_flow=cash_flow, composition=composition)


# ── 2. Cash Flow ─────────────────────────────────────────────────────────────


@router.get("/cash-flow", response_model=list[CashFlowPeriod])
async def get_cash_flow(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    granularity: str = Query("month"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    wallet_id: Optional[uuid.UUID] = Query(None),
    chain: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
) -> list[CashFlowPeriod]:
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, date_from=date_from, date_to=date_to, wallet_id=wallet_id, chain=chain, symbol=symbol)
    rows = await repo.get_cash_flow_series(granularity=granularity, **f)
    return [
        CashFlowPeriod(
            period=r["period"] or "",
            inflow_usd=_to_float(r["inflow_usd"]),
            inflow_vnd=_to_float(r["inflow_vnd"]),
            outflow_usd=_to_float(r["outflow_usd"]),
            outflow_vnd=_to_float(r["outflow_vnd"]),
            net_usd=_to_float(r["net_usd"]),
            net_vnd=_to_float(r["net_vnd"]),
            inflow_qty=_to_float(r.get("inflow_qty", 0)),
            outflow_qty=_to_float(r.get("outflow_qty", 0)),
            entry_count=r.get("entry_count", 0),
        )
        for r in rows
    ]


# ── 3. Income/Expense ─────────────────────────────────────────────────────────


@router.get("/income-expense", response_model=list[IncomeExpensePeriod])
async def get_income_expense(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    granularity: str = Query("month"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    wallet_id: Optional[uuid.UUID] = Query(None),
    chain: Optional[str] = Query(None),
) -> list[IncomeExpensePeriod]:
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, date_from=date_from, date_to=date_to, wallet_id=wallet_id, chain=chain)
    rows = await repo.get_income_expense_series(granularity=granularity, **f)
    return [
        IncomeExpensePeriod(
            period=r["period"] or "",
            income_usd=_to_float(r["income_usd"]),
            income_vnd=_to_float(r["income_vnd"]),
            expense_usd=_to_float(r["expense_usd"]),
            expense_vnd=_to_float(r["expense_vnd"]),
            income_count=r.get("income_count", 0),
            expense_count=r.get("expense_count", 0),
        )
        for r in rows
    ]


# ── 4. Balance Over Time ──────────────────────────────────────────────────────


@router.get("/balance-over-time", response_model=list[BalancePeriod])
async def get_balance_over_time(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    granularity: str = Query("month"),
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    wallet_id: Optional[uuid.UUID] = Query(None),
) -> list[BalancePeriod]:
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, date_from=date_from, date_to=date_to, wallet_id=wallet_id)
    symbol_list = [s.strip() for s in symbols.split(",")] if symbols else None
    rows = await repo.get_balance_over_time(granularity=granularity, symbols=symbol_list, **f)
    return [
        BalancePeriod(
            period=r["period"] or "",
            symbol=r["symbol"],
            period_change=_to_float(r["period_change"]),
            cumulative_qty=_to_float(r["cumulative_quantity"]),
            period_value_usd=_to_float(r["period_value_usd"]),
        )
        for r in rows
    ]


# ── 5. Top Symbols ────────────────────────────────────────────────────────────


@router.get("/top-symbols", response_model=list[SymbolVolume])
async def get_top_symbols(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    limit: int = Query(20, ge=1, le=100),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    wallet_id: Optional[uuid.UUID] = Query(None),
    chain: Optional[str] = Query(None),
    entry_type: Optional[str] = Query(None),
) -> list[SymbolVolume]:
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, date_from=date_from, date_to=date_to, wallet_id=wallet_id, chain=chain, entry_type=entry_type)
    rows = await repo.get_top_symbols_by_volume(limit=limit, **f)
    return [
        SymbolVolume(
            symbol=r["symbol"],
            volume_usd=_to_float(r["volume_usd"]),
            inflow_usd=_to_float(r["inflow_usd"]),
            outflow_usd=_to_float(r["outflow_usd"]),
            tx_count=r["entry_count"],
            total_quantity=_to_float(r.get("total_quantity", 0)),
        )
        for r in rows
    ]


# ── 6. Top Protocols ──────────────────────────────────────────────────────────


@router.get("/top-protocols", response_model=list[ProtocolVolume])
async def get_top_protocols(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    limit: int = Query(20, ge=1, le=100),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    wallet_id: Optional[uuid.UUID] = Query(None),
    chain: Optional[str] = Query(None),
) -> list[ProtocolVolume]:
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, date_from=date_from, date_to=date_to, wallet_id=wallet_id, chain=chain)
    rows = await repo.get_top_protocols_by_volume(limit=limit, **f)
    return [
        ProtocolVolume(
            protocol=r["protocol"],
            volume_usd=_to_float(r["volume_usd"]),
            tx_count=r["entry_count"],
            entry_types=[t for t in (r["entry_types"] or []) if t is not None],
        )
        for r in rows
    ]


# ── 7. Composition ────────────────────────────────────────────────────────────


@router.get("/composition", response_model=list[CompositionItem])
async def get_composition(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    account_type: Optional[str] = Query(None),
    protocol: Optional[str] = Query(None),
    account_subtype: Optional[str] = Query(None),
    wallet_id: Optional[uuid.UUID] = Query(None),
) -> list[CompositionItem]:
    repo = AnalyticsRepo(db)
    f = _build_filters(
        entity,
        account_type=account_type,
        protocol=protocol,
        account_subtype=account_subtype,
        wallet_id=wallet_id,
    )
    rows = await repo.get_composition_snapshot(**f)
    return [
        CompositionItem(
            account_type=r["account_type"],
            subtype=r["subtype"],
            symbol=r["symbol"],
            protocol=r["protocol"],
            balance_qty=_to_float(r["total_quantity"]),
            balance_usd=_to_float(r["total_value_usd"]),
            balance_vnd=_to_float(r["total_value_vnd"]),
        )
        for r in rows
    ]


# ── 8. Activity ───────────────────────────────────────────────────────────────


@router.get("/activity", response_model=list[ActivityDay])
async def get_activity(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    days: int = Query(365, ge=1, le=3650),
    wallet_id: Optional[uuid.UUID] = Query(None),
    chain: Optional[str] = Query(None),
    entry_type: Optional[str] = Query(None),
) -> list[ActivityDay]:
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, wallet_id=wallet_id, chain=chain, entry_type=entry_type)
    rows = await repo.get_activity_heatmap(days=days, **f)
    return [
        ActivityDay(
            date=r["date"],
            count=r["entry_count"],
            volume_usd=_to_float(r["volume_usd"]),
        )
        for r in rows
    ]


# ── 9. Entry Types ────────────────────────────────────────────────────────────


@router.get("/entry-types", response_model=list[EntryTypeBreakdown])
async def get_entry_types(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    wallet_id: Optional[uuid.UUID] = Query(None),
    chain: Optional[str] = Query(None),
) -> list[EntryTypeBreakdown]:
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, date_from=date_from, date_to=date_to, wallet_id=wallet_id, chain=chain)
    rows = await repo.get_entry_type_breakdown(**f)
    return [
        EntryTypeBreakdown(
            entry_type=r["entry_type"],
            count=r["entry_count"],
            volume_usd=_to_float(r["volume_usd"]),
        )
        for r in rows
    ]


# ── 10. Flow by Wallet ────────────────────────────────────────────────────────


@router.get("/flow-by-wallet", response_model=list[WalletFlow])
async def get_flow_by_wallet(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    chain: Optional[str] = Query(None),
) -> list[WalletFlow]:
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, date_from=date_from, date_to=date_to, chain=chain)
    rows = await repo.get_flow_by_wallet(**f)
    return [
        WalletFlow(
            wallet_id=r["wallet_id"],
            label=r["wallet_label"],
            chain=r["chain"],
            inflow_usd=_to_float(r["inflow_usd"]),
            outflow_usd=_to_float(r["outflow_usd"]),
            net_usd=_to_float(r["net_usd"]),
            tx_count=0,  # flow_by_wallet doesn't return tx_count separately
        )
        for r in rows
    ]


# ── 11. Flow by Chain ─────────────────────────────────────────────────────────


@router.get("/flow-by-chain", response_model=list[ChainFlow])
async def get_flow_by_chain(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
) -> list[ChainFlow]:
    repo = AnalyticsRepo(db)
    f = _build_filters(entity, date_from=date_from, date_to=date_to)
    rows = await repo.get_flow_by_chain(**f)
    return [
        ChainFlow(
            chain=r["chain"],
            inflow_usd=_to_float(r["inflow_usd"]),
            outflow_usd=_to_float(r["outflow_usd"]),
            net_usd=_to_float(r["net_usd"]),
            tx_count=r["entry_count"],
        )
        for r in rows
    ]


# ── Tax endpoints ─────────────────────────────────────────────────────────────


# ── 12. Tax: Gains Over Time ──────────────────────────────────────────────────


@router.get("/tax/gains-over-time", response_model=list[RealizedGainsPeriod])
async def get_tax_gains_over_time(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    granularity: str = Query("month"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    symbol: Optional[str] = Query(None),
) -> list[RealizedGainsPeriod]:
    repo = TaxAnalyticsRepo(db)
    rows = await repo.get_realized_gains_series(
        entity.id, granularity=granularity, date_from=date_from, date_to=date_to, symbol=symbol
    )
    return [
        RealizedGainsPeriod(
            period=r["period"],
            gains_usd=_to_float(r["gains_usd"]),
            losses_usd=_to_float(r["losses_usd"]),
            net_usd=_to_float(r["net_usd"]),
            lot_count=r["lot_count"],
        )
        for r in rows
    ]


# ── 13. Tax: Gains by Symbol ──────────────────────────────────────────────────


@router.get("/tax/gains-by-symbol", response_model=list[GainsBySymbol])
async def get_tax_gains_by_symbol(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    symbol: Optional[str] = Query(None),
) -> list[GainsBySymbol]:
    repo = TaxAnalyticsRepo(db)
    rows = await repo.get_realized_gains_by_symbol(
        entity.id, date_from=date_from, date_to=date_to, symbol=symbol
    )
    return [
        GainsBySymbol(
            symbol=r["symbol"],
            gains_usd=_to_float(r["gains_usd"]),
            losses_usd=_to_float(r["losses_usd"]),
            net_usd=_to_float(r["net_usd"]),
            lot_count=r["lot_count"],
            avg_holding_days=r["avg_holding_days"],
        )
        for r in rows
    ]


# ── 14. Tax: Holding Distribution ─────────────────────────────────────────────


@router.get("/tax/holding-distribution", response_model=list[HoldingBucket])
async def get_tax_holding_distribution(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    symbol: Optional[str] = Query(None),
) -> list[HoldingBucket]:
    repo = TaxAnalyticsRepo(db)
    rows = await repo.get_holding_period_distribution(
        entity.id, date_from=date_from, date_to=date_to, symbol=symbol
    )
    return [
        HoldingBucket(
            bucket=r["bucket"],
            lot_count=r["lot_count"],
            total_gain_usd=_to_float(r["total_gain_usd"]),
            total_quantity=_to_float(r["total_quantity"]),
        )
        for r in rows
    ]


# ── 15. Tax: Winners/Losers ───────────────────────────────────────────────────


@router.get("/tax/winners-losers", response_model=WinnersLosers)
async def get_tax_winners_losers(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    limit: int = Query(10, ge=1, le=50),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    symbol: Optional[str] = Query(None),
) -> WinnersLosers:
    repo = TaxAnalyticsRepo(db)
    data = await repo.get_winners_losers(
        entity.id, limit=limit, date_from=date_from, date_to=date_to, symbol=symbol
    )
    return WinnersLosers(
        winners=[
            WinnersLosersItem(
                symbol=r["symbol"],
                net_gain_usd=_to_float(r["net_gain_usd"]),
                lot_count=r["lot_count"],
            )
            for r in data["winners"]
        ],
        losers=[
            WinnersLosersItem(
                symbol=r["symbol"],
                net_gain_usd=_to_float(r["net_gain_usd"]),
                lot_count=r["lot_count"],
            )
            for r in data["losers"]
        ],
    )


# ── 16. Tax: Breakdown ────────────────────────────────────────────────────────


@router.get("/tax/breakdown", response_model=list[TaxBreakdownPeriod])
async def get_tax_breakdown(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    granularity: str = Query("month"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    symbol: Optional[str] = Query(None),
) -> list[TaxBreakdownPeriod]:
    repo = TaxAnalyticsRepo(db)
    rows = await repo.get_tax_breakdown(
        entity.id, granularity=granularity, date_from=date_from, date_to=date_to, symbol=symbol
    )
    return [
        TaxBreakdownPeriod(
            period=r["period"],
            taxable_count=r["taxable_count"],
            exempt_count=r["exempt_count"],
            total_value_vnd=_to_float(r["total_value_vnd"]),
            total_tax_vnd=_to_float(r["total_tax_vnd"]),
        )
        for r in rows
    ]


# ── 17. Tax: By Category ──────────────────────────────────────────────────────


@router.get("/tax/by-category", response_model=list[TaxByCategory])
async def get_tax_by_category(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    symbol: Optional[str] = Query(None),
) -> list[TaxByCategory]:
    repo = TaxAnalyticsRepo(db)
    rows = await repo.get_tax_by_category(
        entity.id, date_from=date_from, date_to=date_to, symbol=symbol
    )
    return [
        TaxByCategory(
            category=r["category"],
            transfer_count=r["transfer_count"],
            total_value_vnd=_to_float(r["total_value_vnd"]),
            total_tax_vnd=_to_float(r["total_tax_vnd"]),
        )
        for r in rows
    ]


# ── 18. Tax: Unrealized ───────────────────────────────────────────────────────


@router.get("/tax/unrealized", response_model=list[UnrealizedPosition])
async def get_tax_unrealized(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    symbol: Optional[str] = Query(None),
) -> list[UnrealizedPosition]:
    repo = TaxAnalyticsRepo(db)
    rows = await repo.get_unrealized_pnl(entity.id, symbol=symbol)
    return [
        UnrealizedPosition(
            symbol=r["symbol"],
            remaining_quantity=_to_float(r["remaining_quantity"]),
            cost_basis_per_unit_usd=_to_float(r["cost_basis_per_unit_usd"]),
            cost_basis_usd=_to_float(r["cost_basis_usd"]),
            buy_timestamp=r["buy_timestamp"],
        )
        for r in rows
    ]


# ── 19. Tax: Cost Basis ───────────────────────────────────────────────────────


@router.get("/tax/cost-basis", response_model=list[CostBasisItem])
async def get_tax_cost_basis(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    symbol: Optional[str] = Query(None),
) -> list[CostBasisItem]:
    repo = TaxAnalyticsRepo(db)
    rows = await repo.get_cost_basis_summary(entity.id, symbol=symbol)
    return [
        CostBasisItem(
            symbol=r["symbol"],
            total_quantity=_to_float(r["total_quantity"]),
            total_cost_usd=_to_float(r["total_cost_usd"]),
            avg_cost_per_unit_usd=_to_float(r["avg_cost_per_unit_usd"]),
            lot_count=r["lot_count"],
        )
        for r in rows
    ]
