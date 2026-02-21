"""TaxAnalyticsRepo — analytics queries on capital gains and taxable transfers."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.capital_gains import ClosedLotRecord, OpenLotRecord
from cryptotax.db.models.taxable_transfer import TaxableTransferRecord


class TaxAnalyticsRepo:
    """Repository for tax-related analytics queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── 1. Realized Gains Series ─────────────────────────────────────

    async def get_realized_gains_series(
        self,
        entity_id: uuid.UUID,
        granularity: str = "month",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Realized gains/losses grouped by period from ClosedLotRecord."""
        period = func.date_trunc(granularity, ClosedLotRecord.sell_timestamp).label("period")

        stmt = (
            select(
                period,
                func.coalesce(
                    func.sum(case((ClosedLotRecord.gain_usd > 0, ClosedLotRecord.gain_usd), else_=Decimal(0))),
                    Decimal(0),
                ).label("gains_usd"),
                func.coalesce(
                    func.sum(case((ClosedLotRecord.gain_usd < 0, ClosedLotRecord.gain_usd), else_=Decimal(0))),
                    Decimal(0),
                ).label("losses_usd"),
                func.coalesce(func.sum(ClosedLotRecord.gain_usd), Decimal(0)).label("net_usd"),
                func.count().label("lot_count"),
            )
            .where(ClosedLotRecord.entity_id == entity_id)
        )

        if date_from is not None:
            stmt = stmt.where(ClosedLotRecord.sell_timestamp >= date_from)
        if date_to is not None:
            stmt = stmt.where(ClosedLotRecord.sell_timestamp <= date_to)
        if symbol is not None:
            stmt = stmt.where(ClosedLotRecord.symbol == symbol)

        stmt = stmt.group_by(period).order_by(period)
        result = await self._session.execute(stmt)

        return [
            {
                "period": row.period.isoformat() if row.period else None,
                "gains_usd": row.gains_usd or Decimal(0),
                "losses_usd": row.losses_usd or Decimal(0),
                "net_usd": row.net_usd or Decimal(0),
                "lot_count": row.lot_count,
            }
            for row in result.all()
        ]

    # ── 2. Realized Gains by Symbol ──────────────────────────────────

    async def get_realized_gains_by_symbol(
        self,
        entity_id: uuid.UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Realized gains/losses grouped by symbol."""
        stmt = (
            select(
                ClosedLotRecord.symbol,
                func.coalesce(
                    func.sum(case((ClosedLotRecord.gain_usd > 0, ClosedLotRecord.gain_usd), else_=Decimal(0))),
                    Decimal(0),
                ).label("gains_usd"),
                func.coalesce(
                    func.sum(case((ClosedLotRecord.gain_usd < 0, ClosedLotRecord.gain_usd), else_=Decimal(0))),
                    Decimal(0),
                ).label("losses_usd"),
                func.coalesce(func.sum(ClosedLotRecord.gain_usd), Decimal(0)).label("net_usd"),
                func.count().label("lot_count"),
                func.coalesce(func.avg(ClosedLotRecord.holding_days), 0).label("avg_holding_days"),
            )
            .where(ClosedLotRecord.entity_id == entity_id)
        )

        if date_from is not None:
            stmt = stmt.where(ClosedLotRecord.sell_timestamp >= date_from)
        if date_to is not None:
            stmt = stmt.where(ClosedLotRecord.sell_timestamp <= date_to)
        if symbol is not None:
            stmt = stmt.where(ClosedLotRecord.symbol == symbol)

        stmt = stmt.group_by(ClosedLotRecord.symbol).order_by(func.sum(ClosedLotRecord.gain_usd).desc())
        result = await self._session.execute(stmt)

        return [
            {
                "symbol": row.symbol,
                "gains_usd": row.gains_usd or Decimal(0),
                "losses_usd": row.losses_usd or Decimal(0),
                "net_usd": row.net_usd or Decimal(0),
                "lot_count": row.lot_count,
                "avg_holding_days": float(row.avg_holding_days or 0),
            }
            for row in result.all()
        ]

    # ── 3. Holding Period Distribution ───────────────────────────────

    async def get_holding_period_distribution(
        self,
        entity_id: uuid.UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Holding period bucketed distribution of closed lots."""
        bucket = case(
            (ClosedLotRecord.holding_days < 7, "< 7 days"),
            (ClosedLotRecord.holding_days < 30, "7-30 days"),
            (ClosedLotRecord.holding_days < 90, "30-90 days"),
            (ClosedLotRecord.holding_days < 365, "90-365 days"),
            else_="> 365 days",
        ).label("bucket")

        # Preserve sort order
        bucket_order = case(
            (ClosedLotRecord.holding_days < 7, 1),
            (ClosedLotRecord.holding_days < 30, 2),
            (ClosedLotRecord.holding_days < 90, 3),
            (ClosedLotRecord.holding_days < 365, 4),
            else_=5,
        ).label("bucket_order")

        stmt = (
            select(
                bucket,
                bucket_order,
                func.count().label("lot_count"),
                func.coalesce(func.sum(ClosedLotRecord.gain_usd), Decimal(0)).label("total_gain_usd"),
                func.coalesce(func.sum(ClosedLotRecord.quantity), Decimal(0)).label("total_quantity"),
            )
            .where(ClosedLotRecord.entity_id == entity_id)
        )

        if date_from is not None:
            stmt = stmt.where(ClosedLotRecord.sell_timestamp >= date_from)
        if date_to is not None:
            stmt = stmt.where(ClosedLotRecord.sell_timestamp <= date_to)
        if symbol is not None:
            stmt = stmt.where(ClosedLotRecord.symbol == symbol)

        stmt = stmt.group_by(bucket, bucket_order).order_by(bucket_order)
        result = await self._session.execute(stmt)

        return [
            {
                "bucket": row.bucket,
                "lot_count": row.lot_count,
                "total_gain_usd": row.total_gain_usd or Decimal(0),
                "total_quantity": row.total_quantity or Decimal(0),
            }
            for row in result.all()
        ]

    # ── 4. Winners and Losers ────────────────────────────────────────

    async def get_winners_losers(
        self,
        entity_id: uuid.UUID,
        limit: int = 10,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Top N winners and losers by realized gain."""
        base_filters = [ClosedLotRecord.entity_id == entity_id]
        if date_from is not None:
            base_filters.append(ClosedLotRecord.sell_timestamp >= date_from)
        if date_to is not None:
            base_filters.append(ClosedLotRecord.sell_timestamp <= date_to)
        if symbol is not None:
            base_filters.append(ClosedLotRecord.symbol == symbol)

        def _build_query(order_desc: bool):
            stmt = (
                select(
                    ClosedLotRecord.symbol,
                    func.coalesce(func.sum(ClosedLotRecord.gain_usd), Decimal(0)).label("net_gain_usd"),
                    func.count().label("lot_count"),
                )
                .where(*base_filters)
                .group_by(ClosedLotRecord.symbol)
            )
            if order_desc:
                stmt = stmt.order_by(func.sum(ClosedLotRecord.gain_usd).desc())
            else:
                stmt = stmt.order_by(func.sum(ClosedLotRecord.gain_usd).asc())
            return stmt.limit(limit)

        winners_result = await self._session.execute(_build_query(order_desc=True))
        losers_result = await self._session.execute(_build_query(order_desc=False))

        def _format(rows):
            return [
                {
                    "symbol": row.symbol,
                    "net_gain_usd": row.net_gain_usd or Decimal(0),
                    "lot_count": row.lot_count,
                }
                for row in rows
            ]

        return {
            "winners": _format(winners_result.all()),
            "losers": _format(losers_result.all()),
        }

    # ── 5. Tax Breakdown ─────────────────────────────────────────────

    async def get_tax_breakdown(
        self,
        entity_id: uuid.UUID,
        granularity: str = "month",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Tax breakdown from TaxableTransferRecord grouped by period."""
        period = func.date_trunc(granularity, TaxableTransferRecord.timestamp).label("period")

        stmt = (
            select(
                period,
                func.count().filter(TaxableTransferRecord.exemption_reason.is_(None)).label("taxable_count"),
                func.count().filter(TaxableTransferRecord.exemption_reason.is_not(None)).label("exempt_count"),
                func.coalesce(func.sum(TaxableTransferRecord.value_vnd), Decimal(0)).label("total_value_vnd"),
                func.coalesce(func.sum(TaxableTransferRecord.tax_amount_vnd), Decimal(0)).label("total_tax_vnd"),
            )
            .where(TaxableTransferRecord.entity_id == entity_id)
        )

        if date_from is not None:
            stmt = stmt.where(TaxableTransferRecord.timestamp >= date_from)
        if date_to is not None:
            stmt = stmt.where(TaxableTransferRecord.timestamp <= date_to)
        if symbol is not None:
            stmt = stmt.where(TaxableTransferRecord.symbol == symbol)

        stmt = stmt.group_by(period).order_by(period)
        result = await self._session.execute(stmt)

        return [
            {
                "period": row.period.isoformat() if row.period else None,
                "taxable_count": row.taxable_count,
                "exempt_count": row.exempt_count,
                "total_value_vnd": row.total_value_vnd or Decimal(0),
                "total_tax_vnd": row.total_tax_vnd or Decimal(0),
            }
            for row in result.all()
        ]

    # ── 6. Tax by Category ───────────────────────────────────────────

    async def get_tax_by_category(
        self,
        entity_id: uuid.UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Tax amounts grouped by exemption_reason (NULL = taxable)."""
        category = func.coalesce(TaxableTransferRecord.exemption_reason, "TAXABLE").label("category")

        stmt = (
            select(
                category,
                func.count().label("transfer_count"),
                func.coalesce(func.sum(TaxableTransferRecord.value_vnd), Decimal(0)).label("total_value_vnd"),
                func.coalesce(func.sum(TaxableTransferRecord.tax_amount_vnd), Decimal(0)).label("total_tax_vnd"),
            )
            .where(TaxableTransferRecord.entity_id == entity_id)
        )

        if date_from is not None:
            stmt = stmt.where(TaxableTransferRecord.timestamp >= date_from)
        if date_to is not None:
            stmt = stmt.where(TaxableTransferRecord.timestamp <= date_to)
        if symbol is not None:
            stmt = stmt.where(TaxableTransferRecord.symbol == symbol)

        stmt = stmt.group_by(category).order_by(category)
        result = await self._session.execute(stmt)

        return [
            {
                "category": row.category,
                "transfer_count": row.transfer_count,
                "total_value_vnd": row.total_value_vnd or Decimal(0),
                "total_tax_vnd": row.total_tax_vnd or Decimal(0),
            }
            for row in result.all()
        ]

    # ── 7. Unrealized PnL ───────────────────────────────────────────

    async def get_unrealized_pnl(
        self,
        entity_id: uuid.UUID,
        symbol: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Open lots with cost basis info (current price deferred to frontend)."""
        stmt = (
            select(
                OpenLotRecord.symbol,
                OpenLotRecord.remaining_quantity,
                OpenLotRecord.cost_basis_per_unit_usd,
                (OpenLotRecord.remaining_quantity * OpenLotRecord.cost_basis_per_unit_usd).label("cost_basis_usd"),
                OpenLotRecord.buy_timestamp,
            )
            .where(OpenLotRecord.entity_id == entity_id)
            .where(OpenLotRecord.remaining_quantity > 0)
        )

        if symbol is not None:
            stmt = stmt.where(OpenLotRecord.symbol == symbol)

        stmt = stmt.order_by(OpenLotRecord.symbol, OpenLotRecord.buy_timestamp)
        result = await self._session.execute(stmt)

        return [
            {
                "symbol": row.symbol,
                "remaining_quantity": row.remaining_quantity,
                "cost_basis_per_unit_usd": row.cost_basis_per_unit_usd,
                "cost_basis_usd": row.cost_basis_usd or Decimal(0),
                "buy_timestamp": row.buy_timestamp.isoformat() if row.buy_timestamp else None,
            }
            for row in result.all()
        ]

    # ── 8. Cost Basis Summary ────────────────────────────────────────

    async def get_cost_basis_summary(
        self,
        entity_id: uuid.UUID,
        symbol: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Aggregated cost basis per symbol from open lots."""
        total_qty = func.sum(OpenLotRecord.remaining_quantity).label("total_quantity")
        total_cost = func.sum(
            OpenLotRecord.remaining_quantity * OpenLotRecord.cost_basis_per_unit_usd
        ).label("total_cost_usd")

        stmt = (
            select(
                OpenLotRecord.symbol,
                total_qty,
                total_cost,
                func.count().label("lot_count"),
            )
            .where(OpenLotRecord.entity_id == entity_id)
            .where(OpenLotRecord.remaining_quantity > 0)
        )

        if symbol is not None:
            stmt = stmt.where(OpenLotRecord.symbol == symbol)

        stmt = stmt.group_by(OpenLotRecord.symbol).order_by(OpenLotRecord.symbol)
        result = await self._session.execute(stmt)

        return [
            {
                "symbol": row.symbol,
                "total_quantity": row.total_quantity or Decimal(0),
                "total_cost_usd": row.total_cost_usd or Decimal(0),
                "avg_cost_per_unit_usd": (
                    (row.total_cost_usd / row.total_quantity)
                    if row.total_quantity and row.total_quantity > 0
                    else Decimal(0)
                ),
                "lot_count": row.lot_count,
            }
            for row in result.all()
        ]
