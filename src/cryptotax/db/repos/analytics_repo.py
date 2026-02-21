"""AnalyticsRepo — comprehensive analytics queries on journal/account data."""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.account import Account
from cryptotax.db.models.journal import JournalEntry, JournalSplit
from cryptotax.db.models.wallet import Wallet


class AnalyticsRepo:
    """Repository for analytics queries across journal entries, splits, accounts, and wallets."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(
        self,
        *,
        entity_id: uuid.UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        wallet_id: Optional[uuid.UUID] = None,
        chain: Optional[str] = None,
        symbol: Optional[str] = None,
        entry_type: Optional[str] = None,
        account_type: Optional[str] = None,
        protocol: Optional[str] = None,
        account_subtype: Optional[str] = None,
    ):
        """Build base select with common joins and WHERE filters.

        Returns a select() on (JournalEntry, JournalSplit, Account, Wallet)
        with all common filters applied.
        """
        stmt = (
            select(JournalEntry, JournalSplit, Account, Wallet)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
        )

        if date_from is not None:
            stmt = stmt.where(JournalEntry.timestamp >= date_from)
        if date_to is not None:
            stmt = stmt.where(JournalEntry.timestamp <= date_to)
        if wallet_id is not None:
            stmt = stmt.where(Wallet.id == wallet_id)
        if chain is not None:
            stmt = stmt.where(Wallet.chain == chain)
        if symbol is not None:
            stmt = stmt.where(Account.symbol == symbol)
        if entry_type is not None:
            stmt = stmt.where(JournalEntry.entry_type == entry_type)
        if account_type is not None:
            stmt = stmt.where(Account.account_type == account_type)
        if protocol is not None:
            stmt = stmt.where(Account.protocol == protocol)
        if account_subtype is not None:
            stmt = stmt.where(Account.subtype == account_subtype)

        return stmt

    def _extract_filters(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Extract known filter keys from kwargs."""
        known = {
            "entity_id", "date_from", "date_to", "wallet_id", "chain",
            "symbol", "entry_type", "account_type", "protocol", "account_subtype",
        }
        return {k: v for k, v in kwargs.items() if k in known and v is not None}

    # ── 1. Cash Flow Series ──────────────────────────────────────────

    async def get_cash_flow_series(
        self, granularity: str = "month", **filters: Any
    ) -> list[dict[str, Any]]:
        """Inflow/outflow series for ASSET accounts grouped by period."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        period = func.date_trunc(granularity, JournalEntry.timestamp).label("period")
        inflow_usd = func.coalesce(
            func.sum(case((JournalSplit.quantity > 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
        ).label("inflow_usd")
        inflow_vnd = func.coalesce(
            func.sum(case((JournalSplit.quantity > 0, JournalSplit.value_vnd), else_=Decimal(0))), Decimal(0)
        ).label("inflow_vnd")
        outflow_usd = func.coalesce(
            func.sum(case((JournalSplit.quantity < 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
        ).label("outflow_usd")
        outflow_vnd = func.coalesce(
            func.sum(case((JournalSplit.quantity < 0, JournalSplit.value_vnd), else_=Decimal(0))), Decimal(0)
        ).label("outflow_vnd")

        stmt = (
            select(period, inflow_usd, inflow_vnd, outflow_usd, outflow_vnd)
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .where(Account.account_type == "ASSET")
        )

        for key, val in f.items():
            stmt = self._apply_filter(stmt, key, val)

        stmt = stmt.group_by(period).order_by(period)
        result = await self._session.execute(stmt)

        return [
            {
                "period": row.period.isoformat() if row.period else None,
                "inflow_usd": row.inflow_usd or Decimal(0),
                "inflow_vnd": row.inflow_vnd or Decimal(0),
                "outflow_usd": row.outflow_usd or Decimal(0),
                "outflow_vnd": row.outflow_vnd or Decimal(0),
                "net_usd": (row.inflow_usd or Decimal(0)) + (row.outflow_usd or Decimal(0)),
                "net_vnd": (row.inflow_vnd or Decimal(0)) + (row.outflow_vnd or Decimal(0)),
            }
            for row in result.all()
        ]

    # ── 2. KPI Summary ───────────────────────────────────────────────

    async def get_kpi_summary(self, **filters: Any) -> dict[str, Any]:
        """Aggregate KPIs: totals, counts, unique tokens/protocols."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        # Monetary aggregates from ASSET splits
        money_stmt = (
            select(
                func.coalesce(
                    func.sum(case((JournalSplit.quantity > 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
                ).label("total_inflow_usd"),
                func.coalesce(
                    func.sum(case((JournalSplit.quantity > 0, JournalSplit.value_vnd), else_=Decimal(0))), Decimal(0)
                ).label("total_inflow_vnd"),
                func.coalesce(
                    func.sum(case((JournalSplit.quantity < 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
                ).label("total_outflow_usd"),
                func.coalesce(
                    func.sum(case((JournalSplit.quantity < 0, JournalSplit.value_vnd), else_=Decimal(0))), Decimal(0)
                ).label("total_outflow_vnd"),
            )
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .where(Account.account_type == "ASSET")
        )
        for key, val in f.items():
            money_stmt = self._apply_filter(money_stmt, key, val)

        money_result = await self._session.execute(money_stmt)
        money = money_result.one()

        # Count aggregates (all account types)
        count_stmt = (
            select(
                func.count(func.distinct(JournalEntry.id)).label("total_entries"),
                func.count(func.distinct(JournalEntry.transaction_id)).label("total_txs"),
                func.count(func.distinct(Account.symbol)).label("unique_tokens"),
                func.count(func.distinct(Account.protocol)).label("unique_protocols"),
            )
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
        )
        for key, val in f.items():
            count_stmt = self._apply_filter(count_stmt, key, val)

        count_result = await self._session.execute(count_stmt)
        counts = count_result.one()

        return {
            "total_inflow_usd": money.total_inflow_usd or Decimal(0),
            "total_inflow_vnd": money.total_inflow_vnd or Decimal(0),
            "total_outflow_usd": money.total_outflow_usd or Decimal(0),
            "total_outflow_vnd": money.total_outflow_vnd or Decimal(0),
            "net_usd": (money.total_inflow_usd or Decimal(0)) + (money.total_outflow_usd or Decimal(0)),
            "net_vnd": (money.total_inflow_vnd or Decimal(0)) + (money.total_outflow_vnd or Decimal(0)),
            "total_entries": counts.total_entries,
            "total_txs": counts.total_txs,
            "unique_tokens": counts.unique_tokens,
            "unique_protocols": counts.unique_protocols,
        }

    # ── 3. Top Symbols by Volume ─────────────────────────────────────

    async def get_top_symbols_by_volume(
        self, limit: int = 20, **filters: Any
    ) -> list[dict[str, Any]]:
        """Top symbols ranked by absolute USD volume."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        stmt = (
            select(
                Account.symbol,
                func.sum(func.abs(func.coalesce(JournalSplit.value_usd, Decimal(0)))).label("volume_usd"),
                func.coalesce(
                    func.sum(case((JournalSplit.quantity > 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
                ).label("inflow_usd"),
                func.coalesce(
                    func.sum(case((JournalSplit.quantity < 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
                ).label("outflow_usd"),
                func.count(func.distinct(JournalEntry.id)).label("entry_count"),
            )
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .where(Account.symbol.is_not(None))
        )

        for key, val in f.items():
            stmt = self._apply_filter(stmt, key, val)

        stmt = stmt.group_by(Account.symbol).order_by(func.sum(func.abs(func.coalesce(JournalSplit.value_usd, Decimal(0)))).desc()).limit(limit)
        result = await self._session.execute(stmt)

        return [
            {
                "symbol": row.symbol,
                "volume_usd": row.volume_usd or Decimal(0),
                "inflow_usd": row.inflow_usd or Decimal(0),
                "outflow_usd": row.outflow_usd or Decimal(0),
                "entry_count": row.entry_count,
            }
            for row in result.all()
        ]

    # ── 4. Top Protocols by Volume ───────────────────────────────────

    async def get_top_protocols_by_volume(
        self, limit: int = 20, **filters: Any
    ) -> list[dict[str, Any]]:
        """Top protocols ranked by absolute USD volume."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        stmt = (
            select(
                Account.protocol,
                func.sum(func.abs(func.coalesce(JournalSplit.value_usd, Decimal(0)))).label("volume_usd"),
                func.count(func.distinct(JournalEntry.id)).label("entry_count"),
                func.array_agg(func.distinct(JournalEntry.entry_type)).label("entry_types"),
            )
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .where(Account.protocol.is_not(None))
        )

        for key, val in f.items():
            stmt = self._apply_filter(stmt, key, val)

        stmt = stmt.group_by(Account.protocol).order_by(func.sum(func.abs(func.coalesce(JournalSplit.value_usd, Decimal(0)))).desc()).limit(limit)
        result = await self._session.execute(stmt)

        return [
            {
                "protocol": row.protocol,
                "volume_usd": row.volume_usd or Decimal(0),
                "entry_count": row.entry_count,
                "entry_types": row.entry_types or [],
            }
            for row in result.all()
        ]

    # ── 5. Composition Snapshot ──────────────────────────────────────

    async def get_composition_snapshot(self, **filters: Any) -> list[dict[str, Any]]:
        """Current balances per account grouped by type/subtype/symbol/protocol."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        stmt = (
            select(
                Account.account_type,
                Account.subtype,
                Account.symbol,
                Account.protocol,
                func.sum(JournalSplit.quantity).label("total_quantity"),
                func.coalesce(func.sum(JournalSplit.value_usd), Decimal(0)).label("total_value_usd"),
                func.coalesce(func.sum(JournalSplit.value_vnd), Decimal(0)).label("total_value_vnd"),
            )
            .select_from(JournalSplit)
            .join(JournalEntry, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
        )

        for key, val in f.items():
            stmt = self._apply_filter(stmt, key, val)

        stmt = (
            stmt.group_by(Account.account_type, Account.subtype, Account.symbol, Account.protocol)
            .having(func.sum(JournalSplit.quantity) != 0)
            .order_by(Account.account_type, Account.subtype, Account.symbol)
        )
        result = await self._session.execute(stmt)

        return [
            {
                "account_type": row.account_type,
                "subtype": row.subtype,
                "symbol": row.symbol,
                "protocol": row.protocol,
                "total_quantity": row.total_quantity,
                "total_value_usd": row.total_value_usd or Decimal(0),
                "total_value_vnd": row.total_value_vnd or Decimal(0),
            }
            for row in result.all()
        ]

    # ── 6. Activity Heatmap ──────────────────────────────────────────

    async def get_activity_heatmap(
        self, days: int = 365, **filters: Any
    ) -> list[dict[str, Any]]:
        """Daily activity counts and USD volume for the last N days."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        cutoff = datetime.utcnow() - timedelta(days=days)
        day_col = func.date_trunc("day", JournalEntry.timestamp).label("day")

        stmt = (
            select(
                day_col,
                func.count(func.distinct(JournalEntry.id)).label("entry_count"),
                func.coalesce(func.sum(func.abs(func.coalesce(JournalSplit.value_usd, Decimal(0)))), Decimal(0)).label("volume_usd"),
            )
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .where(JournalEntry.timestamp >= cutoff)
        )

        for key, val in f.items():
            if key not in ("date_from", "date_to"):
                stmt = self._apply_filter(stmt, key, val)

        stmt = stmt.group_by(day_col).order_by(day_col)
        result = await self._session.execute(stmt)

        return [
            {
                "date": row.day.date().isoformat() if row.day else None,
                "entry_count": row.entry_count,
                "volume_usd": row.volume_usd or Decimal(0),
            }
            for row in result.all()
        ]

    # ── 7. Entry Type Breakdown ──────────────────────────────────────

    async def get_entry_type_breakdown(self, **filters: Any) -> list[dict[str, Any]]:
        """Count and volume grouped by journal entry_type."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        stmt = (
            select(
                JournalEntry.entry_type,
                func.count(func.distinct(JournalEntry.id)).label("entry_count"),
                func.coalesce(func.sum(func.abs(func.coalesce(JournalSplit.value_usd, Decimal(0)))), Decimal(0)).label("volume_usd"),
            )
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
        )

        for key, val in f.items():
            stmt = self._apply_filter(stmt, key, val)

        stmt = stmt.group_by(JournalEntry.entry_type).order_by(func.count(func.distinct(JournalEntry.id)).desc())
        result = await self._session.execute(stmt)

        return [
            {
                "entry_type": row.entry_type,
                "entry_count": row.entry_count,
                "volume_usd": row.volume_usd or Decimal(0),
            }
            for row in result.all()
        ]

    # ── 8. Income/Expense Series ─────────────────────────────────────

    async def get_income_expense_series(
        self, granularity: str = "month", **filters: Any
    ) -> list[dict[str, Any]]:
        """Income and expense amounts grouped by period."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        period = func.date_trunc(granularity, JournalEntry.timestamp).label("period")
        income_usd = func.coalesce(
            func.sum(case((Account.account_type == "INCOME", func.abs(func.coalesce(JournalSplit.value_usd, Decimal(0)))), else_=Decimal(0))),
            Decimal(0),
        ).label("income_usd")
        expense_usd = func.coalesce(
            func.sum(case((Account.account_type == "EXPENSE", func.abs(func.coalesce(JournalSplit.value_usd, Decimal(0)))), else_=Decimal(0))),
            Decimal(0),
        ).label("expense_usd")
        income_vnd = func.coalesce(
            func.sum(case((Account.account_type == "INCOME", func.abs(func.coalesce(JournalSplit.value_vnd, Decimal(0)))), else_=Decimal(0))),
            Decimal(0),
        ).label("income_vnd")
        expense_vnd = func.coalesce(
            func.sum(case((Account.account_type == "EXPENSE", func.abs(func.coalesce(JournalSplit.value_vnd, Decimal(0)))), else_=Decimal(0))),
            Decimal(0),
        ).label("expense_vnd")

        stmt = (
            select(period, income_usd, expense_usd, income_vnd, expense_vnd)
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .where(Account.account_type.in_(["INCOME", "EXPENSE"]))
        )

        for key, val in f.items():
            stmt = self._apply_filter(stmt, key, val)

        stmt = stmt.group_by(period).order_by(period)
        result = await self._session.execute(stmt)

        return [
            {
                "period": row.period.isoformat() if row.period else None,
                "income_usd": row.income_usd or Decimal(0),
                "expense_usd": row.expense_usd or Decimal(0),
                "income_vnd": row.income_vnd or Decimal(0),
                "expense_vnd": row.expense_vnd or Decimal(0),
                "net_usd": (row.income_usd or Decimal(0)) - (row.expense_usd or Decimal(0)),
                "net_vnd": (row.income_vnd or Decimal(0)) - (row.expense_vnd or Decimal(0)),
            }
            for row in result.all()
        ]

    # ── 9. Balance Over Time ─────────────────────────────────────────

    async def get_balance_over_time(
        self,
        granularity: str = "month",
        symbols: Optional[list[str]] = None,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        """Running cumulative balance per symbol per period."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        period = func.date_trunc(granularity, JournalEntry.timestamp).label("period")

        stmt = (
            select(
                period,
                Account.symbol,
                func.sum(JournalSplit.quantity).label("period_quantity"),
                func.coalesce(func.sum(JournalSplit.value_usd), Decimal(0)).label("period_value_usd"),
            )
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .where(Account.account_type == "ASSET")
            .where(Account.symbol.is_not(None))
        )

        if symbols:
            stmt = stmt.where(Account.symbol.in_(symbols))

        for key, val in f.items():
            stmt = self._apply_filter(stmt, key, val)

        stmt = stmt.group_by(period, Account.symbol).order_by(period, Account.symbol)
        result = await self._session.execute(stmt)

        # Build cumulative sums per symbol
        cumulative: dict[str, Decimal] = {}
        rows = []
        for row in result.all():
            sym = row.symbol
            cumulative[sym] = cumulative.get(sym, Decimal(0)) + (row.period_quantity or Decimal(0))
            rows.append({
                "period": row.period.isoformat() if row.period else None,
                "symbol": sym,
                "period_change": row.period_quantity or Decimal(0),
                "period_value_usd": row.period_value_usd or Decimal(0),
                "cumulative_quantity": cumulative[sym],
            })

        return rows

    # ── 10. Flow by Wallet ───────────────────────────────────────────

    async def get_flow_by_wallet(self, **filters: Any) -> list[dict[str, Any]]:
        """Inflow/outflow/net per wallet from ASSET splits."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        stmt = (
            select(
                Wallet.id.label("wallet_id"),
                Wallet.label.label("wallet_label"),
                func.coalesce(Wallet.chain, func.coalesce(Wallet.wallet_type, "unknown")).label("chain"),
                func.coalesce(
                    func.sum(case((JournalSplit.quantity > 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
                ).label("inflow_usd"),
                func.coalesce(
                    func.sum(case((JournalSplit.quantity < 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
                ).label("outflow_usd"),
            )
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .where(Account.account_type == "ASSET")
        )

        for key, val in f.items():
            stmt = self._apply_filter(stmt, key, val)

        stmt = stmt.group_by(Wallet.id, Wallet.label, Wallet.chain, Wallet.wallet_type)
        result = await self._session.execute(stmt)

        return [
            {
                "wallet_id": str(row.wallet_id),
                "wallet_label": row.wallet_label,
                "chain": row.chain,
                "inflow_usd": row.inflow_usd or Decimal(0),
                "outflow_usd": row.outflow_usd or Decimal(0),
                "net_usd": (row.inflow_usd or Decimal(0)) + (row.outflow_usd or Decimal(0)),
            }
            for row in result.all()
        ]

    # ── 11. Flow by Chain ────────────────────────────────────────────

    async def get_flow_by_chain(self, **filters: Any) -> list[dict[str, Any]]:
        """Inflow/outflow/net per chain from ASSET splits."""
        f = self._extract_filters(filters)
        entity_id = f.pop("entity_id")

        chain_col = func.coalesce(Wallet.chain, func.coalesce(Wallet.wallet_type, "unknown")).label("chain")

        stmt = (
            select(
                chain_col,
                func.coalesce(
                    func.sum(case((JournalSplit.quantity > 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
                ).label("inflow_usd"),
                func.coalesce(
                    func.sum(case((JournalSplit.quantity < 0, JournalSplit.value_usd), else_=Decimal(0))), Decimal(0)
                ).label("outflow_usd"),
                func.count(func.distinct(JournalEntry.id)).label("entry_count"),
            )
            .select_from(JournalEntry)
            .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .where(Account.account_type == "ASSET")
        )

        for key, val in f.items():
            stmt = self._apply_filter(stmt, key, val)

        stmt = stmt.group_by(chain_col).order_by(chain_col)
        result = await self._session.execute(stmt)

        return [
            {
                "chain": row.chain,
                "inflow_usd": row.inflow_usd or Decimal(0),
                "outflow_usd": row.outflow_usd or Decimal(0),
                "net_usd": (row.inflow_usd or Decimal(0)) + (row.outflow_usd or Decimal(0)),
                "entry_count": row.entry_count,
            }
            for row in result.all()
        ]

    # ── Helper ───────────────────────────────────────────────────────

    @staticmethod
    def _apply_filter(stmt, key: str, val: Any):
        """Apply a single filter to a statement."""
        filter_map = {
            "date_from": lambda s, v: s.where(JournalEntry.timestamp >= v),
            "date_to": lambda s, v: s.where(JournalEntry.timestamp <= v),
            "wallet_id": lambda s, v: s.where(Wallet.id == v),
            "chain": lambda s, v: s.where(Wallet.chain == v),
            "symbol": lambda s, v: s.where(Account.symbol == v),
            "entry_type": lambda s, v: s.where(JournalEntry.entry_type == v),
            "account_type": lambda s, v: s.where(Account.account_type == v),
            "protocol": lambda s, v: s.where(Account.protocol == v),
            "account_subtype": lambda s, v: s.where(Account.subtype == v),
        }
        if key in filter_map:
            return filter_map[key](stmt, val)
        return stmt
