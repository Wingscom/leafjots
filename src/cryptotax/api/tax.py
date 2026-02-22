"""Tax API — calculate capital gains and Vietnam transfer tax."""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.accounting.tax_engine import TaxEngine
from cryptotax.api.deps import get_db
from cryptotax.api.schemas.tax import (
    ClosedLotResponse,
    OpenLotResponse,
    TaxableTransferResponse,
    TaxCalculateRequest,
    TaxCalculateResponse,
    TaxSummaryResponse,
)
from cryptotax.db.models.capital_gains import ClosedLotRecord, OpenLotRecord
from cryptotax.db.repos.entity_repo import EntityRepo

router = APIRouter(prefix="/api/tax", tags=["tax"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/calculate", response_model=TaxCalculateResponse)
async def calculate_tax(body: TaxCalculateRequest, db: DbDep) -> TaxCalculateResponse:
    """Run FIFO capital gains calculation + Vietnam 0.1% transfer tax."""
    entity_repo = EntityRepo(db)

    if body.entity_id:
        entity = await entity_repo.get_by_id(body.entity_id)
    else:
        entity = await entity_repo.get_default()

    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    try:
        start = datetime.fromisoformat(body.start_date).replace(tzinfo=None)
        end = datetime.fromisoformat(body.end_date).replace(hour=23, minute=59, second=59, tzinfo=None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    engine = TaxEngine(db)
    result = await engine.calculate(entity.id, start, end)
    await db.commit()

    return TaxCalculateResponse(
        summary=TaxSummaryResponse(
            period_start=result.period_start,
            period_end=result.period_end,
            total_realized_gain_usd=result.total_realized_gain_usd,
            total_transfer_tax_vnd=result.total_transfer_tax_vnd,
            total_exempt_vnd=result.total_exempt_vnd,
            closed_lot_count=len(result.closed_lots),
            open_lot_count=len(result.open_lots),
            taxable_transfer_count=len(result.taxable_transfers),
        ),
        closed_lots=[
            ClosedLotResponse(
                symbol=cl.symbol,
                quantity=cl.quantity,
                cost_basis_usd=cl.cost_basis_usd,
                proceeds_usd=cl.proceeds_usd,
                gain_usd=cl.gain_usd,
                holding_days=cl.holding_days,
                buy_date=cl.buy_trade.timestamp,
                sell_date=cl.sell_trade.timestamp,
            )
            for cl in result.closed_lots
        ],
        open_lots=[
            OpenLotResponse(
                symbol=ol.symbol,
                remaining_quantity=ol.remaining_quantity,
                cost_basis_per_unit_usd=ol.cost_basis_per_unit_usd,
                buy_date=ol.buy_trade.timestamp,
            )
            for ol in result.open_lots
        ],
        taxable_transfers=[
            TaxableTransferResponse(
                timestamp=tt.timestamp,
                symbol=tt.symbol,
                quantity=tt.quantity,
                value_vnd=tt.value_vnd,
                tax_amount_vnd=tt.tax_amount_vnd,
                exemption_reason=tt.exemption_reason.value if tt.exemption_reason else None,
            )
            for tt in result.taxable_transfers
        ],
    )


@router.get("/realized-gains", response_model=list[ClosedLotResponse])
async def get_realized_gains(
    db: DbDep,
    entity_id: Optional[uuid.UUID] = Query(None, description="Entity ID to scope gains"),
    symbol: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None, description="Filter by sell date from"),
    date_to: Optional[datetime] = Query(None, description="Filter by sell date to"),
    gain_only: bool = Query(False, description="Only include lots with gain_usd > 0"),
    loss_only: bool = Query(False, description="Only include lots with gain_usd < 0"),
    min_holding_days: Optional[int] = Query(None, ge=0),
    max_holding_days: Optional[int] = Query(None, ge=0),
) -> list[ClosedLotResponse]:
    """List all realized gains (closed lots), optionally scoped by entity."""
    stmt = select(ClosedLotRecord).order_by(ClosedLotRecord.sell_timestamp.desc())
    if entity_id is not None:
        stmt = stmt.where(ClosedLotRecord.entity_id == entity_id)
    if symbol is not None:
        stmt = stmt.where(ClosedLotRecord.symbol == symbol)
    if date_from is not None:
        stmt = stmt.where(ClosedLotRecord.sell_timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(ClosedLotRecord.sell_timestamp <= date_to)
    if gain_only:
        stmt = stmt.where(ClosedLotRecord.gain_usd > 0)
    if loss_only:
        stmt = stmt.where(ClosedLotRecord.gain_usd < 0)
    if min_holding_days is not None:
        stmt = stmt.where(ClosedLotRecord.holding_days >= min_holding_days)
    if max_holding_days is not None:
        stmt = stmt.where(ClosedLotRecord.holding_days <= max_holding_days)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        ClosedLotResponse(
            symbol=r.symbol,
            quantity=r.quantity,
            cost_basis_usd=r.cost_basis_usd,
            proceeds_usd=r.proceeds_usd,
            gain_usd=r.gain_usd,
            holding_days=r.holding_days,
            buy_date=r.buy_timestamp or r.created_at,
            sell_date=r.sell_timestamp or r.created_at,
        )
        for r in records
    ]


@router.get("/open-lots", response_model=list[OpenLotResponse])
async def get_open_lots(
    db: DbDep,
    entity_id: Optional[uuid.UUID] = Query(None, description="Entity ID to scope lots"),
    symbol: Optional[str] = Query(None),
    min_quantity: Optional[float] = Query(None, ge=0, description="Minimum remaining quantity"),
) -> list[OpenLotResponse]:
    """List all open (unrealized) positions, optionally scoped by entity."""
    stmt = select(OpenLotRecord).order_by(OpenLotRecord.buy_timestamp.asc())
    if entity_id is not None:
        stmt = stmt.where(OpenLotRecord.entity_id == entity_id)
    if symbol is not None:
        stmt = stmt.where(OpenLotRecord.symbol == symbol)
    if min_quantity is not None:
        stmt = stmt.where(OpenLotRecord.remaining_quantity >= min_quantity)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        OpenLotResponse(
            symbol=r.symbol,
            remaining_quantity=r.remaining_quantity,
            cost_basis_per_unit_usd=r.cost_basis_per_unit_usd,
            buy_date=r.buy_timestamp or r.created_at,
        )
        for r in records
    ]


@router.get("/summary", response_model=TaxSummaryResponse | None)
async def get_tax_summary(
    db: DbDep,
    entity_id: Optional[uuid.UUID] = Query(None, description="Entity ID to scope summary"),
):
    """Get latest tax summary from persisted data, optionally scoped by entity."""
    # Aggregate from closed/open lot records
    closed_stmt = select(ClosedLotRecord)
    open_stmt = select(OpenLotRecord)
    if entity_id is not None:
        closed_stmt = closed_stmt.where(ClosedLotRecord.entity_id == entity_id)
        open_stmt = open_stmt.where(OpenLotRecord.entity_id == entity_id)

    closed_result = await db.execute(closed_stmt)
    closed = closed_result.scalars().all()

    open_result = await db.execute(open_stmt)
    open_lots = open_result.scalars().all()

    if not closed and not open_lots:
        return None

    from decimal import Decimal
    total_gain = sum((r.gain_usd for r in closed), Decimal(0))

    return TaxSummaryResponse(
        period_start=min((r.buy_timestamp for r in closed if r.buy_timestamp), default=datetime.now()),
        period_end=max((r.sell_timestamp for r in closed if r.sell_timestamp), default=datetime.now()),
        total_realized_gain_usd=total_gain,
        total_transfer_tax_vnd=Decimal(0),  # Only available from full calculate
        total_exempt_vnd=Decimal(0),
        closed_lot_count=len(closed),
        open_lot_count=len(open_lots),
        taxable_transfer_count=0,
    )
