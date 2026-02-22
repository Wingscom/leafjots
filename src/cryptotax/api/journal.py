import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import build_price_service, get_db, resolve_entity
from cryptotax.api.schemas.journal import JournalEntryDetail, JournalEntryResponse, JournalList, JournalSplitResponse
from cryptotax.db.models.account import Account
from cryptotax.db.models.entity import Entity
from cryptotax.db.models.journal import JournalEntry, JournalSplit
from cryptotax.db.models.wallet import Wallet
from cryptotax.db.repos.journal_repo import JournalRepo

router = APIRouter(prefix="/api/journal", tags=["journal"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=JournalList)
async def list_journal(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    entry_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    symbol: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    wallet_id: Optional[uuid.UUID] = Query(None),
    protocol: Optional[str] = Query(None),
    account_subtype: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> JournalList:
    journal_repo = JournalRepo(db)
    entries, total = await journal_repo.list_for_entity(
        entity.id,
        entry_type=entry_type,
        date_from=date_from,
        date_to=date_to,
        symbol=symbol,
        account_type=account_type,
        wallet_id=wallet_id,
        protocol=protocol,
        account_subtype=account_subtype,
        limit=limit,
        offset=offset,
    )

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


@router.post("/reprice")
async def reprice_splits(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
) -> dict:
    """Backfill value_usd/value_vnd for splits that have NULL prices.

    Fetches prices from CoinGecko for all splits where value_usd IS NULL.
    """
    price_service = build_price_service(db)

    # Find all splits with NULL value_usd for this entity
    stmt = (
        select(JournalSplit)
        .join(JournalEntry, JournalSplit.journal_entry_id == JournalEntry.id)
        .join(Account, JournalSplit.account_id == Account.id)
        .join(Wallet, Account.wallet_id == Wallet.id)
        .where(Wallet.entity_id == entity.id)
        .where(JournalSplit.value_usd.is_(None))
    )
    result = await db.execute(stmt)
    splits = result.scalars().all()

    if not splits:
        return {"updated": 0, "still_null": 0, "total_null_before": 0, "unmapped_symbols": []}

    total_before = len(splits)
    updated = 0
    unmapped: set[str] = set()

    # Batch: collect (split, account, entry) for pricing
    for split in splits:
        # Load account for symbol
        acc_result = await db.execute(select(Account).where(Account.id == split.account_id))
        account = acc_result.scalar_one_or_none()
        if not account or not account.symbol:
            continue

        # Load journal entry for timestamp
        entry_result = await db.execute(select(JournalEntry).where(JournalEntry.id == split.journal_entry_id))
        entry = entry_result.scalar_one_or_none()
        if not entry or not entry.timestamp:
            continue

        timestamp = int(entry.timestamp.timestamp()) if hasattr(entry.timestamp, 'timestamp') else int(entry.timestamp)

        value_usd, value_vnd = await price_service.price_split(account.symbol, split.quantity, timestamp)
        if value_usd is not None:
            split.value_usd = value_usd
            split.value_vnd = value_vnd
            updated += 1
        else:
            unmapped.add(account.symbol)

    await db.commit()

    return {
        "updated": updated,
        "still_null": total_before - updated,
        "total_null_before": total_before,
        "unmapped_symbols": sorted(unmapped),
    }
