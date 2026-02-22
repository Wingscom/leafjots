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
        subtype: Optional[str] = None,
        symbol: Optional[str] = None,
        protocol: Optional[str] = None,
        wallet_id: Optional[uuid.UUID] = None,
    ) -> list[Account]:
        base = (
            select(Account)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
        )
        if account_type:
            base = base.where(Account.account_type == account_type)
        if subtype is not None:
            base = base.where(Account.subtype == subtype)
        if symbol is not None:
            base = base.where(Account.symbol == symbol)
        if protocol is not None:
            base = base.where(Account.protocol == protocol)
        if wallet_id is not None:
            base = base.where(Account.wallet_id == wallet_id)
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

    async def get_balances_usd_vnd_for_entity(
        self, entity_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[Decimal, Decimal]]:
        """Get current USD and VND balances for all accounts of an entity.

        Returns a dict mapping account_id -> (balance_usd, balance_vnd).
        """
        result = await self._session.execute(
            select(
                JournalSplit.account_id,
                func.coalesce(func.sum(JournalSplit.value_usd), 0),
                func.coalesce(func.sum(JournalSplit.value_vnd), 0),
            )
            .join(Account, JournalSplit.account_id == Account.id)
            .join(Wallet, Account.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
            .group_by(JournalSplit.account_id)
        )
        return {row[0]: (row[1], row[2]) for row in result.all()}
