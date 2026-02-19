"""ReportDataCollector — gathers all data needed for bangketoan.xlsx."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cryptotax.accounting.tax_engine import TaxEngine
from cryptotax.config import settings
from cryptotax.db.models.account import Account
from cryptotax.db.models.capital_gains import ClosedLotRecord, OpenLotRecord
from cryptotax.db.models.entity import Entity
from cryptotax.db.models.journal import JournalEntry
from cryptotax.db.models.wallet import OnChainWallet


@dataclass
class ReportData:
    """All data needed to write the bangketoan.xlsx report."""

    # Sheet data — each is a list of row tuples
    summary: list[tuple] = field(default_factory=list)
    balance_sheet_qty: list[tuple] = field(default_factory=list)
    balance_sheet_usd: list[tuple] = field(default_factory=list)
    balance_sheet_vnd: list[tuple] = field(default_factory=list)
    income_statement: list[tuple] = field(default_factory=list)
    flows_qty: list[tuple] = field(default_factory=list)
    flows_usd: list[tuple] = field(default_factory=list)
    realized_gains: list[tuple] = field(default_factory=list)
    open_lots: list[tuple] = field(default_factory=list)
    journal: list[tuple] = field(default_factory=list)
    tax_summary: list[tuple] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    wallets: list[tuple] = field(default_factory=list)
    settings_data: list[tuple] = field(default_factory=list)


class ReportDataCollector:
    """Collects all data from DB needed for report generation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def collect(
        self,
        entity_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> ReportData:
        """Gather all report data for the given entity and date range."""
        data = ReportData()
        vnd_rate = Decimal(str(settings.usd_vnd_rate))

        # Run tax calculation to get fresh results
        engine = TaxEngine(self._session)
        tax_result = await engine.calculate(entity_id, start, end)

        # Load all data in parallel-ish queries
        entries = await self._load_journal_entries(entity_id, start, end)
        accounts_map = await self._load_accounts_map(entries)
        closed_lots = await self._load_closed_lots(entity_id)
        open_lots = await self._load_open_lots(entity_id)
        wallets = await self._load_wallets(entity_id)
        entity = await self._load_entity(entity_id)

        # Build each sheet
        data.summary = self._build_summary(tax_result, entity, start, end, vnd_rate)
        data.balance_sheet_qty = self._build_balance_sheet(entries, accounts_map, "qty")
        data.balance_sheet_usd = self._build_balance_sheet(entries, accounts_map, "usd")
        data.balance_sheet_vnd = self._build_balance_sheet(entries, accounts_map, "vnd", vnd_rate)
        data.income_statement = self._build_income_statement(entries, accounts_map, vnd_rate)
        data.flows_qty = self._build_flows(entries, accounts_map, "qty")
        data.flows_usd = self._build_flows(entries, accounts_map, "usd")
        data.realized_gains = self._build_realized_gains(closed_lots)
        data.open_lots = self._build_open_lots(open_lots)
        data.journal = self._build_journal(entries, accounts_map)
        data.tax_summary = self._build_tax_summary(tax_result)
        data.warnings = self._build_warnings(entries)
        data.wallets = self._build_wallets(wallets)
        data.settings_data = self._build_settings(entity, start, end, vnd_rate)

        return data

    # ── DB Queries ──────────────────────────────────────────────

    async def _load_journal_entries(
        self, entity_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[JournalEntry]:
        result = await self._session.execute(
            select(JournalEntry)
            .where(
                JournalEntry.entity_id == entity_id,
                JournalEntry.timestamp >= start,
                JournalEntry.timestamp <= end,
            )
            .options(selectinload(JournalEntry.splits))
            .order_by(JournalEntry.timestamp.asc())
        )
        return list(result.scalars().all())

    async def _load_accounts_map(self, entries: list[JournalEntry]) -> dict[uuid.UUID, Account]:
        account_ids = set()
        for entry in entries:
            for split in entry.splits:
                account_ids.add(split.account_id)

        if not account_ids:
            return {}

        result = await self._session.execute(
            select(Account).where(Account.id.in_(account_ids))
        )
        return {acc.id: acc for acc in result.scalars().all()}

    async def _load_closed_lots(self, entity_id: uuid.UUID) -> list[ClosedLotRecord]:
        result = await self._session.execute(
            select(ClosedLotRecord)
            .where(ClosedLotRecord.entity_id == entity_id)
            .order_by(ClosedLotRecord.sell_timestamp.asc())
        )
        return list(result.scalars().all())

    async def _load_open_lots(self, entity_id: uuid.UUID) -> list[OpenLotRecord]:
        result = await self._session.execute(
            select(OpenLotRecord)
            .where(OpenLotRecord.entity_id == entity_id)
            .order_by(OpenLotRecord.buy_timestamp.asc())
        )
        return list(result.scalars().all())

    async def _load_wallets(self, entity_id: uuid.UUID) -> list[OnChainWallet]:
        result = await self._session.execute(
            select(OnChainWallet).where(OnChainWallet.entity_id == entity_id)
        )
        return list(result.scalars().all())

    async def _load_entity(self, entity_id: uuid.UUID) -> Entity | None:
        result = await self._session.execute(
            select(Entity).where(Entity.id == entity_id)
        )
        return result.scalar_one_or_none()

    # ── Sheet Builders ──────────────────────────────────────────

    def _build_summary(self, tax_result, entity, start, end, vnd_rate) -> list[tuple]:
        return [
            ("Entity", entity.name if entity else "Unknown"),
            ("Period Start", start.strftime("%Y-%m-%d")),
            ("Period End", end.strftime("%Y-%m-%d")),
            ("Base Currency", entity.base_currency if entity else "VND"),
            ("USD/VND Rate", float(vnd_rate)),
            ("FIFO Method", "GLOBAL_FIFO"),
            ("Total Realized Gain (USD)", float(tax_result.total_realized_gain_usd)),
            ("Total Realized Gain (VND)", float(tax_result.total_realized_gain_usd * vnd_rate)),
            ("Transfer Tax Due (VND)", float(tax_result.total_transfer_tax_vnd)),
            ("Exempt Amount (VND)", float(tax_result.total_exempt_vnd)),
            ("Closed Lots", len(tax_result.closed_lots)),
            ("Open Lots", len(tax_result.open_lots)),
            ("Taxable Transfers", len(tax_result.taxable_transfers)),
        ]

    def _build_balance_sheet(
        self, entries, accounts_map, mode: str, vnd_rate: Decimal | None = None
    ) -> list[tuple]:
        """Build balance sheet: aggregate by account."""
        balances: dict[uuid.UUID, Decimal] = defaultdict(Decimal)

        for entry in entries:
            for split in entry.splits:
                if mode == "qty":
                    balances[split.account_id] += split.quantity
                elif mode == "usd":
                    balances[split.account_id] += split.value_usd or Decimal(0)
                elif mode == "vnd":
                    usd_val = split.value_usd or Decimal(0)
                    balances[split.account_id] += usd_val * (vnd_rate or Decimal(1))

        rows = []
        for acc_id, balance in sorted(balances.items(), key=lambda x: x[0]):
            acc = accounts_map.get(acc_id)
            if acc and balance != Decimal(0):
                rows.append((
                    acc.account_type,
                    acc.subtype,
                    acc.symbol or "",
                    acc.label or "",
                    float(balance),
                ))
        # Sort by account_type, then symbol
        rows.sort(key=lambda r: (r[0], r[2]))
        return rows

    def _build_income_statement(self, entries, accounts_map, vnd_rate) -> list[tuple]:
        """Income + expense accounts only."""
        totals_usd: dict[uuid.UUID, Decimal] = defaultdict(Decimal)

        for entry in entries:
            for split in entry.splits:
                acc = accounts_map.get(split.account_id)
                if acc and acc.account_type in ("INCOME", "EXPENSE"):
                    totals_usd[split.account_id] += split.value_usd or Decimal(0)

        rows = []
        for acc_id, total in sorted(totals_usd.items(), key=lambda x: x[0]):
            acc = accounts_map.get(acc_id)
            if acc and total != Decimal(0):
                rows.append((
                    acc.account_type,
                    acc.symbol or "",
                    acc.label or "",
                    float(total),
                    float(total * vnd_rate),
                ))
        rows.sort(key=lambda r: (r[0], r[1]))
        return rows

    def _build_flows(self, entries, accounts_map, mode: str) -> list[tuple]:
        """Period flows: each split as a row."""
        rows = []
        for entry in entries:
            for split in entry.splits:
                acc = accounts_map.get(split.account_id)
                if mode == "qty":
                    rows.append((
                        entry.timestamp.strftime("%Y-%m-%d %H:%M"),
                        entry.entry_type,
                        entry.description or "",
                        acc.symbol if acc else "",
                        float(split.quantity),
                    ))
                elif mode == "usd":
                    rows.append((
                        entry.timestamp.strftime("%Y-%m-%d %H:%M"),
                        entry.entry_type,
                        entry.description or "",
                        acc.symbol if acc else "",
                        float(split.value_usd or 0),
                    ))
        return rows

    def _build_realized_gains(self, closed_lots: list[ClosedLotRecord]) -> list[tuple]:
        return [
            (
                cl.symbol,
                float(cl.quantity),
                float(cl.cost_basis_usd),
                float(cl.proceeds_usd),
                float(cl.gain_usd),
                cl.holding_days,
                cl.buy_timestamp.strftime("%Y-%m-%d") if cl.buy_timestamp else "",
                cl.sell_timestamp.strftime("%Y-%m-%d") if cl.sell_timestamp else "",
            )
            for cl in closed_lots
        ]

    def _build_open_lots(self, open_lots: list[OpenLotRecord]) -> list[tuple]:
        return [
            (
                ol.symbol,
                float(ol.remaining_quantity),
                float(ol.cost_basis_per_unit_usd),
                float(ol.remaining_quantity * ol.cost_basis_per_unit_usd),
                ol.buy_timestamp.strftime("%Y-%m-%d") if ol.buy_timestamp else "",
            )
            for ol in open_lots
        ]

    def _build_journal(self, entries, accounts_map) -> list[tuple]:
        rows = []
        for entry in entries:
            for split in entry.splits:
                acc = accounts_map.get(split.account_id)
                rows.append((
                    entry.timestamp.strftime("%Y-%m-%d %H:%M"),
                    entry.entry_type,
                    entry.description or "",
                    acc.account_type if acc else "",
                    acc.symbol if acc else "",
                    acc.label if acc else "",
                    float(split.quantity),
                    float(split.value_usd or 0),
                    float(split.value_vnd or 0),
                ))
        return rows

    def _build_tax_summary(self, tax_result) -> list[tuple]:
        return [
            (
                tt.timestamp.strftime("%Y-%m-%d %H:%M"),
                tt.symbol,
                float(tt.quantity),
                float(tt.value_vnd),
                float(tt.tax_amount_vnd),
                tt.exemption_reason.value if tt.exemption_reason else "TAXABLE",
            )
            for tt in tax_result.taxable_transfers
        ]

    def _build_warnings(self, entries) -> list[str]:
        warnings = []
        for entry in entries:
            has_null_price = any(s.value_usd is None for s in entry.splits)
            if has_null_price:
                warnings.append(f"Missing price: {entry.description or entry.entry_type} at {entry.timestamp}")

            # Check balance
            total = sum(s.quantity for s in entry.splits)
            if total != Decimal(0):
                warnings.append(f"Unbalanced qty: {entry.description or entry.entry_type} (delta={total})")
        return warnings

    def _build_wallets(self, wallets: list[OnChainWallet]) -> list[tuple]:
        return [
            (
                w.chain or "",
                w.address or "",
                w.label or "",
                w.sync_status,
            )
            for w in wallets
        ]

    def _build_settings(self, entity, start, end, vnd_rate) -> list[tuple]:
        return [
            ("Entity", entity.name if entity else "Unknown"),
            ("Period", f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"),
            ("FIFO Method", "GLOBAL_FIFO"),
            ("USD/VND Rate", str(vnd_rate)),
            ("Tax Rate", "0.1%"),
            ("Exemption Threshold", "VND 20,000,000"),
            ("Generated By", "LeafJots v0.1.0"),
        ]
