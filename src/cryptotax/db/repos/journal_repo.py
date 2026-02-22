import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.account import Account
from cryptotax.db.models.journal import JournalEntry, JournalSplit
from cryptotax.db.models.wallet import Wallet


class JournalRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entry_id: uuid.UUID) -> Optional[JournalEntry]:
        result = await self._session.execute(
            select(JournalEntry).where(JournalEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list_for_entity(
        self,
        entity_id: uuid.UUID,
        entry_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbol: Optional[str] = None,
        account_type: Optional[str] = None,
        wallet_id: Optional[uuid.UUID] = None,
        protocol: Optional[str] = None,
        account_subtype: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[JournalEntry], int]:
        needs_split_join = any(v is not None for v in (symbol, account_type, wallet_id, protocol, account_subtype))

        if needs_split_join:
            # Join through splits -> accounts -> wallets for advanced filtering
            base = (
                select(JournalEntry)
                .distinct()
                .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
                .join(Account, JournalSplit.account_id == Account.id)
                .join(Wallet, Account.wallet_id == Wallet.id)
                .where(JournalEntry.entity_id == entity_id)
            )
            count_q = (
                select(func.count(func.distinct(JournalEntry.id)))
                .select_from(JournalEntry)
                .join(JournalSplit, JournalSplit.journal_entry_id == JournalEntry.id)
                .join(Account, JournalSplit.account_id == Account.id)
                .join(Wallet, Account.wallet_id == Wallet.id)
                .where(JournalEntry.entity_id == entity_id)
            )
        else:
            base = select(JournalEntry).where(JournalEntry.entity_id == entity_id)
            count_q = select(func.count()).select_from(JournalEntry).where(JournalEntry.entity_id == entity_id)

        if entry_type:
            base = base.where(JournalEntry.entry_type == entry_type)
            count_q = count_q.where(JournalEntry.entry_type == entry_type)
        if date_from is not None:
            base = base.where(JournalEntry.timestamp >= date_from)
            count_q = count_q.where(JournalEntry.timestamp >= date_from)
        if date_to is not None:
            base = base.where(JournalEntry.timestamp <= date_to)
            count_q = count_q.where(JournalEntry.timestamp <= date_to)
        if symbol is not None:
            base = base.where(Account.symbol == symbol)
            count_q = count_q.where(Account.symbol == symbol)
        if account_type is not None:
            base = base.where(Account.account_type == account_type)
            count_q = count_q.where(Account.account_type == account_type)
        if wallet_id is not None:
            base = base.where(Wallet.id == wallet_id)
            count_q = count_q.where(Wallet.id == wallet_id)
        if protocol is not None:
            base = base.where(Account.protocol == protocol)
            count_q = count_q.where(Account.protocol == protocol)
        if account_subtype is not None:
            base = base.where(Account.subtype == account_subtype)
            count_q = count_q.where(Account.subtype == account_subtype)

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        result = await self._session.execute(
            base.order_by(JournalEntry.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def get_for_transaction(self, tx_id: int) -> Optional[JournalEntry]:
        result = await self._session.execute(
            select(JournalEntry).where(JournalEntry.transaction_id == tx_id)
        )
        return result.scalar_one_or_none()

    async def delete_for_transaction(self, tx_id: int) -> int:
        """Delete journal entry + cascade splits for a transaction. Returns count deleted."""
        entry = await self.get_for_transaction(tx_id)
        if entry is None:
            return 0
        await self._session.delete(entry)
        await self._session.flush()
        return 1

    async def list_unbalanced(self, entity_id: uuid.UUID) -> list[JournalEntry]:
        """Find entries where splits don't sum to zero in USD or VND."""
        # Get all entries for entity, check balance in Python
        # (Aggregate query for this is complex; acceptable for moderate volumes)
        result = await self._session.execute(
            select(JournalEntry).where(JournalEntry.entity_id == entity_id)
        )
        entries = result.scalars().all()
        unbalanced = []
        for entry in entries:
            try:
                entry.validate_balanced()
            except Exception:
                unbalanced.append(entry)
        return unbalanced

    async def count_by_entry_type(self, entity_id: uuid.UUID) -> dict[str, int]:
        """Count journal entries grouped by entry_type."""
        result = await self._session.execute(
            select(JournalEntry.entry_type, func.count())
            .where(JournalEntry.entity_id == entity_id)
            .group_by(JournalEntry.entry_type)
        )
        return dict(result.all())

    async def get_splits_for_account(
        self,
        account_id: uuid.UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[JournalSplit], int]:
        needs_entry_join = date_from is not None or date_to is not None

        if needs_entry_join:
            base = (
                select(JournalSplit)
                .join(JournalEntry, JournalSplit.journal_entry_id == JournalEntry.id)
                .where(JournalSplit.account_id == account_id)
            )
            count_q = (
                select(func.count())
                .select_from(JournalSplit)
                .join(JournalEntry, JournalSplit.journal_entry_id == JournalEntry.id)
                .where(JournalSplit.account_id == account_id)
            )
            if date_from is not None:
                base = base.where(JournalEntry.timestamp >= date_from)
                count_q = count_q.where(JournalEntry.timestamp >= date_from)
            if date_to is not None:
                base = base.where(JournalEntry.timestamp <= date_to)
                count_q = count_q.where(JournalEntry.timestamp <= date_to)
        else:
            base = select(JournalSplit).where(JournalSplit.account_id == account_id)
            count_q = select(func.count()).select_from(JournalSplit).where(JournalSplit.account_id == account_id)

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        result = await self._session.execute(
            base.order_by(JournalSplit.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total
