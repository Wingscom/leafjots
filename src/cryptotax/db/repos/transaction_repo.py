import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.transaction import Transaction


class TransactionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_existing_hashes(self, wallet_id: uuid.UUID) -> set[str]:
        result = await self._session.execute(
            select(Transaction.tx_hash).where(Transaction.wallet_id == wallet_id)
        )
        return set(result.scalars().all())

    async def bulk_insert(self, txs: list[Transaction]) -> None:
        self._session.add_all(txs)
        await self._session.flush()

    async def get_by_hash(self, tx_hash: str) -> Optional[Transaction]:
        result = await self._session.execute(
            select(Transaction).where(Transaction.tx_hash == tx_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, tx_id: int) -> Optional[Transaction]:
        result = await self._session.execute(
            select(Transaction).where(Transaction.id == tx_id)
        )
        return result.scalar_one_or_none()

    async def list_for_wallet(
        self,
        wallet_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        base = select(Transaction).where(Transaction.wallet_id == wallet_id)
        count_q = select(func.count()).select_from(Transaction).where(Transaction.wallet_id == wallet_id)

        if status:
            base = base.where(Transaction.status == status)
            count_q = count_q.where(Transaction.status == status)

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        result = await self._session.execute(
            base.order_by(Transaction.block_number.desc().nullslast(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def list_for_entity(
        self,
        entity_id: uuid.UUID,
        chain: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        from cryptotax.db.models.wallet import Wallet

        base = select(Transaction).join(Wallet, Transaction.wallet_id == Wallet.id).where(Wallet.entity_id == entity_id)
        count_q = (
            select(func.count())
            .select_from(Transaction)
            .join(Wallet, Transaction.wallet_id == Wallet.id)
            .where(Wallet.entity_id == entity_id)
        )

        if chain:
            base = base.where(Transaction.chain == chain)
            count_q = count_q.where(Transaction.chain == chain)
        if status:
            base = base.where(Transaction.status == status)
            count_q = count_q.where(Transaction.status == status)

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        result = await self._session.execute(
            base.order_by(Transaction.block_number.desc().nullslast(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total
