import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import build_bookkeeper, get_db, resolve_entity
from cryptotax.api.schemas.parse import ParseStatsResponse, ParseTestRequest, ParseTestResponse, ParseWalletResponse, ParsedSplitResponse
from cryptotax.db.models.entity import Entity
from cryptotax.db.models.transaction import Transaction
from cryptotax.db.repos.transaction_repo import TransactionRepo
from cryptotax.db.repos.wallet_repo import WalletRepo
from cryptotax.domain.enums import TxStatus

router = APIRouter(prefix="/api/parse", tags=["parser"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/test", response_model=ParseTestResponse)
async def parse_test(body: ParseTestRequest, db: DbDep, entity: Entity = Depends(resolve_entity)) -> ParseTestResponse:
    """Parse a single transaction by hash (dry-run or real persist)."""
    tx_repo = TransactionRepo(db)
    tx = await tx_repo.get_by_hash(body.tx_hash)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    wallet_repo = WalletRepo(db)
    wallet = await wallet_repo.get_by_id(tx.wallet_id)
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found for this transaction")

    bookkeeper = build_bookkeeper(db)
    entry = await bookkeeper.process_transaction(tx, wallet, entity.id)
    await db.commit()

    if entry is None:
        return ParseTestResponse(
            tx_hash=body.tx_hash,
            parser_name="none",
            entry_type="ERROR",
            splits=[],
            balanced=False,
            warnings=["Failed to parse transaction — check /errors for details"],
        )

    # entry.splits already loaded via refresh in bookkeeper
    splits = []
    for split in entry.splits:
        # Load account for display
        from cryptotax.db.models.account import Account
        result = await db.execute(select(Account).where(Account.id == split.account_id))
        account = result.scalar_one_or_none()
        splits.append(ParsedSplitResponse(
            account_label=account.label if account else "unknown",
            account_type=account.account_type if account else "unknown",
            symbol=account.symbol if account else "unknown",
            quantity=split.quantity,
        ))

    return ParseTestResponse(
        tx_hash=body.tx_hash,
        parser_name=entry.description or "unknown",
        entry_type=entry.entry_type,
        splits=splits,
        balanced=True,
        warnings=[],
    )


@router.post("/wallet/{wallet_id}", response_model=ParseWalletResponse)
async def parse_wallet(wallet_id: uuid.UUID, db: DbDep, entity: Entity = Depends(resolve_entity)) -> ParseWalletResponse:
    """Parse all LOADED transactions for a wallet."""
    wallet_repo = WalletRepo(db)
    wallet = await wallet_repo.get_by_id(wallet_id)
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    bookkeeper = build_bookkeeper(db)
    stats = await bookkeeper.process_wallet(wallet, entity.id)
    await db.commit()

    return ParseWalletResponse(**stats)


@router.get("/stats", response_model=ParseStatsResponse)
async def parse_stats(
    db: DbDep,
    entity_id: Optional[uuid.UUID] = Query(None, description="Entity ID to scope stats (all entities if omitted)"),
) -> ParseStatsResponse:
    """Get parsing statistics across all transactions, optionally scoped by entity."""
    from cryptotax.db.models.wallet import Wallet

    base = select(Transaction.status, func.count()).group_by(Transaction.status)
    if entity_id is not None:
        base = base.join(Wallet, Transaction.wallet_id == Wallet.id).where(Wallet.entity_id == entity_id)

    result = await db.execute(base)
    counts = dict(result.all())

    total = sum(counts.values())
    parsed = counts.get(TxStatus.PARSED.value, 0)
    errors = counts.get(TxStatus.ERROR.value, 0)
    unknown = counts.get(TxStatus.LOADED.value, 0)

    return ParseStatsResponse(total=total, parsed=parsed, errors=errors, unknown=unknown)
