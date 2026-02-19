import json
import uuid
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.parse_error_record import ParseErrorRecord


class ParseErrorRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        transaction_id: Optional[int],
        wallet_id: Optional[uuid.UUID],
        error_type: str,
        message: str,
        stack_trace: Optional[str] = None,
    ) -> ParseErrorRecord:
        record = ParseErrorRecord(
            transaction_id=transaction_id,
            wallet_id=wallet_id,
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_errors(
        self,
        error_type: Optional[str] = None,
        resolved: Optional[bool] = None,
        entity_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[ParseErrorRecord, str | None, str | None]], int]:
        """Return (error, tx_hash, chain) tuples and total count."""
        from cryptotax.db.models.transaction import Transaction
        from cryptotax.db.models.wallet import Wallet

        base = (
            select(ParseErrorRecord, Transaction.tx_hash, Transaction.chain)
            .outerjoin(Transaction, ParseErrorRecord.transaction_id == Transaction.id)
        )
        count_q = select(func.count()).select_from(ParseErrorRecord)

        if entity_id is not None:
            base = base.join(Wallet, ParseErrorRecord.wallet_id == Wallet.id).where(Wallet.entity_id == entity_id)
            count_q = count_q.join(Wallet, ParseErrorRecord.wallet_id == Wallet.id).where(
                Wallet.entity_id == entity_id
            )

        if error_type:
            base = base.where(ParseErrorRecord.error_type == error_type)
            count_q = count_q.where(ParseErrorRecord.error_type == error_type)
        if resolved is not None:
            base = base.where(ParseErrorRecord.resolved == resolved)
            count_q = count_q.where(ParseErrorRecord.resolved == resolved)

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        result = await self._session.execute(
            base.order_by(ParseErrorRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.tuples().all()), total

    async def get_summary(self) -> dict[str, int]:
        result = await self._session.execute(
            select(ParseErrorRecord.error_type, func.count())
            .where(ParseErrorRecord.resolved == False)  # noqa: E712
            .group_by(ParseErrorRecord.error_type)
        )
        return dict(result.all())

    async def get_full_summary(self, entity_id: Optional[uuid.UUID] = None) -> dict:
        """Return summary with by_type, resolved, unresolved, total."""
        from cryptotax.db.models.wallet import Wallet

        # by_type (unresolved only)
        by_type_q = (
            select(ParseErrorRecord.error_type, func.count())
            .where(ParseErrorRecord.resolved == False)  # noqa: E712
            .group_by(ParseErrorRecord.error_type)
        )
        resolved_q = (
            select(func.count()).select_from(ParseErrorRecord)
            .where(ParseErrorRecord.resolved == True)  # noqa: E712
        )

        if entity_id is not None:
            by_type_q = by_type_q.join(Wallet, ParseErrorRecord.wallet_id == Wallet.id).where(
                Wallet.entity_id == entity_id
            )
            resolved_q = resolved_q.join(Wallet, ParseErrorRecord.wallet_id == Wallet.id).where(
                Wallet.entity_id == entity_id
            )

        by_type_result = await self._session.execute(by_type_q)
        by_type = dict(by_type_result.all())

        resolved_result = await self._session.execute(resolved_q)
        resolved = resolved_result.scalar_one()

        # unresolved count
        unresolved = sum(by_type.values())

        return {
            "total": resolved + unresolved,
            "by_type": by_type,
            "resolved": resolved,
            "unresolved": unresolved,
        }

    async def list_by_diagnostic_filter(
        self,
        contract_address: Optional[str] = None,
        function_selector: Optional[str] = None,
    ) -> list[ParseErrorRecord]:
        """List unresolved errors matching diagnostic criteria."""
        base = select(ParseErrorRecord).where(ParseErrorRecord.resolved == False)  # noqa: E712

        result = await self._session.execute(
            base.order_by(ParseErrorRecord.created_at.desc())
        )
        records = list(result.scalars().all())

        # Filter by diagnostic_data JSON fields
        if contract_address is None and function_selector is None:
            return records

        filtered = []
        for r in records:
            if not r.diagnostic_data:
                continue
            try:
                diag = json.loads(r.diagnostic_data)
            except (json.JSONDecodeError, TypeError):
                continue

            if contract_address and diag.get("contract_address", "").lower() != contract_address.lower():
                continue
            if function_selector and diag.get("function_selector", "").lower() != function_selector.lower():
                continue
            filtered.append(r)

        return filtered

    async def mark_resolved(self, error_id: uuid.UUID) -> Optional[ParseErrorRecord]:
        result = await self._session.execute(
            select(ParseErrorRecord).where(ParseErrorRecord.id == error_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.resolved = True
            await self._session.flush()
        return record

    async def delete_for_transaction(self, tx_id: int) -> int:
        result = await self._session.execute(
            delete(ParseErrorRecord).where(ParseErrorRecord.transaction_id == tx_id)
        )
        return result.rowcount
