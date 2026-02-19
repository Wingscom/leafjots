"""TaxEngine — orchestrates FIFO capital gains + Vietnam 0.1% transfer tax."""

import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cryptotax.accounting.fifo import fifo_match, trades_from_splits
from cryptotax.config import settings
from cryptotax.db.models.capital_gains import ClosedLotRecord, OpenLotRecord
from cryptotax.db.models.journal import JournalEntry
from cryptotax.db.models.account import Account
from cryptotax.domain.enums.tax import TaxExemptionReason
from cryptotax.domain.models.tax import TaxableTransfer, TaxSummary

# Vietnam tax: 0.1% per transfer, exempt if value_vnd > 20M
TAX_RATE = Decimal("0.001")
EXEMPTION_THRESHOLD_VND = Decimal("20000000")


class TaxEngine:
    """Calculate capital gains (FIFO) and Vietnam transfer tax."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def calculate(
        self,
        entity_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> TaxSummary:
        """Run full tax calculation for an entity in a date range."""
        # 1. Load journal entries + splits + accounts
        splits_data = await self._load_splits(entity_id, start, end)

        # 2. Group by symbol, build trades, run FIFO
        symbols = {s["symbol"] for s in splits_data if s["symbol"]}
        all_closed = []
        all_open = []

        for symbol in sorted(symbols):
            trades = trades_from_splits(splits_data, symbol)
            if not trades:
                continue
            closed, open_lots = fifo_match(trades)
            all_closed.extend(closed)
            all_open.extend(open_lots)

        # 3. Calculate 0.1% transfer tax
        vnd_rate = Decimal(str(settings.usd_vnd_rate))
        taxable_transfers = self._calculate_transfer_tax(splits_data, vnd_rate)

        # 4. Aggregate
        total_gain = sum((cl.gain_usd for cl in all_closed), Decimal(0))
        total_tax = sum((t.tax_amount_vnd for t in taxable_transfers if t.exemption_reason is None), Decimal(0))
        total_exempt = sum((t.value_vnd for t in taxable_transfers if t.exemption_reason is not None), Decimal(0))

        # 5. Persist (delete-then-insert for idempotency)
        await self._persist_results(entity_id, all_closed, all_open)

        return TaxSummary(
            period_start=start,
            period_end=end,
            total_realized_gain_usd=total_gain,
            total_transfer_tax_vnd=total_tax,
            total_exempt_vnd=total_exempt,
            closed_lots=all_closed,
            open_lots=all_open,
            taxable_transfers=taxable_transfers,
        )

    async def _load_splits(
        self,
        entity_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        """Load journal splits with account info for the date range."""
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
        entries = result.scalars().all()

        # Collect all account IDs, batch-load accounts
        all_account_ids = set()
        for entry in entries:
            for split in entry.splits:
                all_account_ids.add(split.account_id)

        accounts_map: dict[uuid.UUID, Account] = {}
        if all_account_ids:
            acc_result = await self._session.execute(
                select(Account).where(Account.id.in_(all_account_ids))
            )
            for acc in acc_result.scalars().all():
                accounts_map[acc.id] = acc

        # Build flat list of split dicts
        splits_data: list[dict] = []
        for entry in entries:
            for split in entry.splits:
                acc = accounts_map.get(split.account_id)
                splits_data.append({
                    "account_type": acc.account_type if acc else "UNKNOWN",
                    "account_subtype": acc.subtype if acc else "unknown",
                    "symbol": acc.symbol if acc else "UNKNOWN",
                    "quantity": split.quantity,
                    "value_usd": split.value_usd,
                    "value_vnd": split.value_vnd,
                    "timestamp": entry.timestamp,
                    "journal_entry_id": entry.id,
                    "description": entry.description or "",
                    "entry_type": entry.entry_type,
                })

        return splits_data

    def _calculate_transfer_tax(
        self,
        splits_data: list[dict],
        vnd_rate: Decimal,
    ) -> list[TaxableTransfer]:
        """Calculate 0.1% Vietnam tax on each outgoing transfer (SELL side).

        Exempt if individual transfer value > VND 20M.
        """
        transfers: list[TaxableTransfer] = []
        asset_subtypes = {"native_asset", "erc20_token", "protocol_asset"}

        # Group negative asset splits by journal entry
        by_entry: dict[uuid.UUID, list[dict]] = defaultdict(list)
        for s in splits_data:
            if s.get("account_subtype") in asset_subtypes and s["quantity"] < 0:
                by_entry[s["journal_entry_id"]].append(s)

        for entry_id, sell_splits in by_entry.items():
            for s in sell_splits:
                abs_qty = abs(s["quantity"])
                value_usd = abs(s["value_usd"]) if s["value_usd"] else Decimal(0)
                value_vnd = value_usd * vnd_rate

                tax_amount = value_vnd * TAX_RATE

                # Exemption: transfers > VND 20M are exempt
                exemption = None
                if value_vnd > EXEMPTION_THRESHOLD_VND:
                    exemption = TaxExemptionReason.BELOW_THRESHOLD

                # Gas fees are exempt
                if s.get("entry_type") == "GAS_FEE":
                    exemption = TaxExemptionReason.GAS_FEE

                transfers.append(TaxableTransfer(
                    timestamp=s["timestamp"],
                    symbol=s["symbol"],
                    quantity=abs_qty,
                    value_vnd=value_vnd,
                    tax_amount_vnd=tax_amount if exemption is None else Decimal(0),
                    exemption_reason=exemption,
                ))

        return transfers

    async def _persist_results(
        self,
        entity_id: uuid.UUID,
        closed_lots: list,
        open_lots: list,
    ) -> None:
        """Delete old results and insert new ones (idempotent)."""
        await self._session.execute(
            delete(ClosedLotRecord).where(ClosedLotRecord.entity_id == entity_id)
        )
        await self._session.execute(
            delete(OpenLotRecord).where(OpenLotRecord.entity_id == entity_id)
        )

        for cl in closed_lots:
            self._session.add(ClosedLotRecord(
                entity_id=entity_id,
                symbol=cl.symbol,
                quantity=cl.quantity,
                cost_basis_usd=cl.cost_basis_usd,
                proceeds_usd=cl.proceeds_usd,
                gain_usd=cl.gain_usd,
                holding_days=cl.holding_days,
                buy_entry_id=cl.buy_trade.journal_entry_id,
                sell_entry_id=cl.sell_trade.journal_entry_id,
                buy_timestamp=cl.buy_trade.timestamp,
                sell_timestamp=cl.sell_trade.timestamp,
            ))

        for ol in open_lots:
            self._session.add(OpenLotRecord(
                entity_id=entity_id,
                symbol=ol.symbol,
                remaining_quantity=ol.remaining_quantity,
                cost_basis_per_unit_usd=ol.cost_basis_per_unit_usd,
                buy_entry_id=ol.buy_trade.journal_entry_id,
                buy_timestamp=ol.buy_trade.timestamp,
            ))

        await self._session.flush()
