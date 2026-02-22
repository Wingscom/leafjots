import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db, resolve_entity
from cryptotax.api.schemas.accounts import AccountHistory, AccountHistorySplit, AccountList, AccountResponse
from cryptotax.db.models.entity import Entity
from cryptotax.db.repos.account_repo import AccountRepo
from cryptotax.db.repos.journal_repo import JournalRepo

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=AccountList)
async def list_accounts(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    account_type: Optional[str] = Query(None),
    subtype: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    protocol: Optional[str] = Query(None),
    wallet_id: Optional[uuid.UUID] = Query(None),
) -> AccountList:
    account_repo = AccountRepo(db)
    accounts = await account_repo.get_all_for_entity(
        entity.id,
        account_type=account_type,
        subtype=subtype,
        symbol=symbol,
        protocol=protocol,
        wallet_id=wallet_id,
    )
    balances = await account_repo.get_balances_for_entity(entity.id)
    balances_usd_vnd = await account_repo.get_balances_usd_vnd_for_entity(entity.id)

    return AccountList(
        accounts=[
            AccountResponse(
                id=a.id,
                wallet_id=a.wallet_id,
                account_type=a.account_type,
                subtype=a.subtype,
                symbol=a.symbol,
                protocol=a.protocol,
                balance_type=a.balance_type,
                label=a.label,
                current_balance=balances.get(a.id, 0),
                balance_usd=balances_usd_vnd.get(a.id, (0, 0))[0],
                balance_vnd=balances_usd_vnd.get(a.id, (0, 0))[1],
            )
            for a in accounts
        ]
    )


@router.get("/{account_id}/history", response_model=AccountHistory)
async def get_account_history(
    account_id: uuid.UUID,
    db: DbDep,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AccountHistory:
    account_repo = AccountRepo(db)
    account = await account_repo.get_by_id(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    journal_repo = JournalRepo(db)
    splits, total = await journal_repo.get_splits_for_account(
        account_id, date_from=date_from, date_to=date_to, limit=limit, offset=offset
    )

    return AccountHistory(
        splits=[AccountHistorySplit(
            id=s.id,
            journal_entry_id=s.journal_entry_id,
            quantity=s.quantity,
            value_usd=s.value_usd,
            value_vnd=s.value_vnd,
            created_at=str(s.created_at),
        ) for s in splits],
        total=total,
        limit=limit,
        offset=offset,
    )
