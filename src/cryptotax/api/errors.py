import json
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db, resolve_entity
from cryptotax.api.schemas.errors import ErrorSummaryResponse, ParseErrorResponse
from cryptotax.db.models.entity import Entity
from cryptotax.db.repos.parse_error_repo import ParseErrorRepo

router = APIRouter(prefix="/api/errors", tags=["errors"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _to_response(e, tx_hash: str | None = None, chain: str | None = None) -> ParseErrorResponse:
    """Convert a ParseErrorRecord to response, deserializing diagnostic_data JSON."""
    diag = None
    if e.diagnostic_data:
        try:
            diag = json.loads(e.diagnostic_data)
        except (json.JSONDecodeError, TypeError):
            pass

    return ParseErrorResponse(
        id=e.id,
        transaction_id=e.transaction_id,
        wallet_id=e.wallet_id,
        tx_hash=tx_hash,
        chain=chain,
        error_type=e.error_type,
        message=e.message,
        stack_trace=e.stack_trace,
        resolved=e.resolved,
        created_at=e.created_at,
        diagnostic_data=diag,
    )


@router.get("")
async def list_errors(
    db: DbDep,
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter errors by entity"),
    error_type: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    contract_address: Optional[str] = Query(None),
    function_selector: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    repo = ParseErrorRepo(db)
    rows, total = await repo.list_errors(
        error_type=error_type, resolved=resolved, entity_id=entity_id, limit=limit, offset=offset,
    )
    return {
        "errors": [_to_response(e, tx_hash, chain).model_dump(mode="json") for e, tx_hash, chain in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/summary", response_model=ErrorSummaryResponse)
async def error_summary(
    db: DbDep,
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter summary by entity"),
) -> ErrorSummaryResponse:
    repo = ParseErrorRepo(db)
    summary = await repo.get_full_summary(entity_id=entity_id)
    return ErrorSummaryResponse(**summary)


@router.post("/retry-group")
async def retry_error_group(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    contract_address: Optional[str] = Query(None),
    function_selector: Optional[str] = Query(None),
) -> dict:
    """Bulk re-parse all error TXs matching a contract/function filter."""
    from cryptotax.api.deps import build_bookkeeper
    from cryptotax.db.repos.journal_repo import JournalRepo
    from cryptotax.db.repos.transaction_repo import TransactionRepo
    from cryptotax.db.repos.wallet_repo import WalletRepo
    from cryptotax.domain.enums import TxStatus

    repo = ParseErrorRepo(db)
    errors = await repo.list_by_diagnostic_filter(
        contract_address=contract_address,
        function_selector=function_selector,
    )

    if not errors:
        return {"retried": 0, "success": 0, "failed": 0}

    tx_repo = TransactionRepo(db)
    wallet_repo = WalletRepo(db)
    journal_repo = JournalRepo(db)
    bookkeeper = build_bookkeeper(db)

    success = 0
    failed = 0
    for error_record in errors:
        if error_record.transaction_id is None:
            continue
        tx = await tx_repo.get_by_id(error_record.transaction_id)
        if tx is None:
            continue
        wallet = await wallet_repo.get_by_id(tx.wallet_id)
        if wallet is None:
            continue

        await journal_repo.delete_for_transaction(tx.id)
        await repo.delete_for_transaction(tx.id)
        tx.status = TxStatus.LOADED.value

        entry = await bookkeeper.process_transaction(tx, wallet, entity.id)
        if entry:
            success += 1
        else:
            failed += 1

    await db.commit()
    return {"retried": success + failed, "success": success, "failed": failed}


@router.post("/{error_id}/retry")
async def retry_error(error_id: uuid.UUID, db: DbDep, entity: Entity = Depends(resolve_entity)) -> dict:
    """Re-parse the transaction associated with this error."""
    from cryptotax.api.deps import build_bookkeeper
    from cryptotax.db.models.parse_error_record import ParseErrorRecord
    from cryptotax.db.repos.journal_repo import JournalRepo
    from cryptotax.db.repos.transaction_repo import TransactionRepo
    from cryptotax.db.repos.wallet_repo import WalletRepo
    from cryptotax.domain.enums import TxStatus
    from sqlalchemy import select

    stmt = select(ParseErrorRecord).where(ParseErrorRecord.id == error_id)
    result = await db.execute(stmt)
    error_record = result.scalar_one_or_none()
    if error_record is None:
        raise HTTPException(status_code=404, detail="Error record not found")

    if error_record.transaction_id is None:
        raise HTTPException(status_code=400, detail="No transaction associated with this error")

    tx_repo = TransactionRepo(db)
    tx = await tx_repo.get_by_id(error_record.transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    wallet_repo = WalletRepo(db)
    wallet = await wallet_repo.get_by_id(tx.wallet_id)
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    journal_repo = JournalRepo(db)
    await journal_repo.delete_for_transaction(tx.id)
    error_repo = ParseErrorRepo(db)
    await error_repo.delete_for_transaction(tx.id)
    tx.status = TxStatus.LOADED.value

    bookkeeper = build_bookkeeper(db)
    entry = await bookkeeper.process_transaction(tx, wallet, entity.id)
    await db.commit()

    return {"status": "ok" if entry else "error", "entry_type": entry.entry_type if entry else None}


@router.post("/{error_id}/ignore")
async def ignore_error(error_id: uuid.UUID, db: DbDep) -> dict:
    """Mark error as resolved and TX as IGNORED."""
    from cryptotax.db.models.parse_error_record import ParseErrorRecord
    from cryptotax.db.models.transaction import Transaction
    from cryptotax.domain.enums import TxStatus
    from sqlalchemy import select

    result = await db.execute(select(ParseErrorRecord).where(ParseErrorRecord.id == error_id))
    error_record = result.scalar_one_or_none()
    if error_record is None:
        raise HTTPException(status_code=404, detail="Error record not found")

    error_record.resolved = True

    if error_record.transaction_id is not None:
        tx_result = await db.execute(select(Transaction).where(Transaction.id == error_record.transaction_id))
        tx = tx_result.scalar_one_or_none()
        if tx:
            tx.status = TxStatus.IGNORED.value

    await db.commit()
    return {"status": "ok"}
