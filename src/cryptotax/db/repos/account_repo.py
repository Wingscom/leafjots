import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.account import Account
from cryptotax.db.models.journal import JournalSplit
from cryptotax.db.models.wallet import Wallet


class AccountRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_for_entity(
        self,
        entity_id: uuid.UUID,
        account_type: Optional[str] = None,
    ) -> list[Account]:
        base = (
            select(Account)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
        )
        if account_type:
            base = base.where(Account.account_type == account_type)
        result = await self._session.execute(base.order_by(Account.account_type, Account.label))
        return list(result.scalars().all())

    async def get_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
        result = await self._session.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_by_label(self, label: str) -> Optional[Account]:
        result = await self._session.execute(
            select(Account).where(Account.label == label)
        )
        return result.scalar_one_or_none()

    async def get_balance(self, account_id: uuid.UUID) -> Decimal:
        result = await self._session.execute(
            select(func.coalesce(func.sum(JournalSplit.quantity), 0))
            .where(JournalSplit.account_id == account_id)
        )
        return result.scalar_one()

    async def get_balances_for_entity(self, entity_id: uuid.UUID) -> dict[uuid.UUID, Decimal]:
        """Get current balance for all accounts of an entity."""
        result = await self._session.execute(
            select(JournalSplit.account_id, func.sum(JournalSplit.quantity))
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .group_by(JournalSplit.account_id)
        )
        return {row[0]: row[1] for row in result.all()}
