import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db, resolve_entity
from cryptotax.api.schemas.journal import JournalEntryDetail, JournalEntryResponse, JournalList, JournalSplitResponse
from cryptotax.db.models.account import Account
from cryptotax.db.models.entity import Entity
from cryptotax.db.repos.journal_repo import JournalRepo

router = APIRouter(prefix="/api/journal", tags=["journal"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=JournalList)
async def list_journal(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    entry_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> JournalList:
    journal_repo = JournalRepo(db)
    entries, total = await journal_repo.list_for_entity(entity.id, entry_type=entry_type, limit=limit, offset=offset)

    return JournalList(
        entries=[JournalEntryResponse.model_validate(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/validation", response_model=list[JournalEntryResponse])
async def list_unbalanced(db: DbDep, entity: Entity = Depends(resolve_entity)) -> list[JournalEntryResponse]:
    journal_repo = JournalRepo(db)
    entries = await journal_repo.list_unbalanced(entity.id)
    return [JournalEntryResponse.model_validate(e) for e in entries]


@router.get("/{entry_id}", response_model=JournalEntryDetail)
async def get_journal_entry(entry_id: uuid.UUID, db: DbDep) -> JournalEntryDetail:
    journal_repo = JournalRepo(db)
    entry = await journal_repo.get_by_id(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    # Build splits with account info
    splits_response = []
    for split in entry.splits:
        result = await db.execute(select(Account).where(Account.id == split.account_id))
        account = result.scalar_one_or_none()
        splits_response.append(JournalSplitResponse(
            id=split.id,
            account_id=split.account_id,
            account_label=account.label if account else None,
            account_type=account.account_type if account else None,
            symbol=account.symbol if account else None,
            quantity=split.quantity,
            value_usd=split.value_usd,
            value_vnd=split.value_vnd,
        ))

    return JournalEntryDetail(
        id=entry.id,
        entity_id=entry.entity_id,
        transaction_id=entry.transaction_id,
        entry_type=entry.entry_type,
        description=entry.description,
        timestamp=entry.timestamp,
        created_at=entry.created_at,
        splits=splits_response,
    )
