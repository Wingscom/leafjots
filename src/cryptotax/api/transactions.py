import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db, resolve_entity
from cryptotax.api.schemas.transactions import TransactionDetail, TransactionList, TransactionResponse
from cryptotax.db.models.entity import Entity
from cryptotax.db.repos.transaction_repo import TransactionRepo

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=TransactionList)
async def list_transactions(
    db: DbDep,
    entity: Entity = Depends(resolve_entity),
    wallet_id: Optional[uuid.UUID] = Query(None),
    chain: Optional[str] = Query(None),
    tx_status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> TransactionList:
    tx_repo = TransactionRepo(db)

    if wallet_id:
        txs, total = await tx_repo.list_for_wallet(wallet_id, status=tx_status, limit=limit, offset=offset)
    else:
        txs, total = await tx_repo.list_for_entity(entity.id, chain=chain, status=tx_status, limit=limit, offset=offset)

    return TransactionList(
        transactions=[TransactionResponse.model_validate(tx) for tx in txs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{tx_hash}", response_model=TransactionDetail)
async def get_transaction(tx_hash: str, db: DbDep) -> TransactionDetail:
    tx_repo = TransactionRepo(db)
    tx = await tx_repo.get_by_hash(tx_hash)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return TransactionDetail.model_validate(tx)
