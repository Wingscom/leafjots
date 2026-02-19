import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db, resolve_entity
from cryptotax.api.schemas.wallets import CEXWalletCreate, WalletCreate, WalletList, WalletResponse, WalletStatusResponse
from cryptotax.db.models.entity import Entity
from cryptotax.db.repos.wallet_repo import WalletRepo

router = APIRouter(prefix="/api/wallets", tags=["wallets"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def add_wallet(body: WalletCreate, db: DbDep, entity: Entity = Depends(resolve_entity)) -> WalletResponse:
    wallet_repo = WalletRepo(db)

    existing = await wallet_repo.get_by_chain_and_address(entity.id, body.chain, body.address)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Wallet {body.chain}:{body.address} already exists")

    wallet = await wallet_repo.create(entity_id=entity.id, chain=body.chain, address=body.address, label=body.label)
    await db.commit()
    await db.refresh(wallet)
    return WalletResponse.model_validate(wallet)


@router.post("/cex", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def add_cex_wallet(body: CEXWalletCreate, db: DbDep, entity: Entity = Depends(resolve_entity)) -> WalletResponse:
    """Add a CEX wallet (e.g. Binance) with encrypted API credentials."""
    from cryptotax.config import settings
    from cryptotax.infra.cex.crypto import encrypt_value

    wallet_repo = WalletRepo(db)

    existing = await wallet_repo.get_by_exchange(entity.id, body.exchange)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{body.exchange.value} wallet already exists")

    api_key_enc = encrypt_value(body.api_key, settings.encryption_key) if body.api_key else ""
    api_secret_enc = encrypt_value(body.api_secret, settings.encryption_key) if body.api_secret else ""

    wallet = await wallet_repo.create_cex_wallet(
        entity_id=entity.id,
        exchange=body.exchange,
        api_key_encrypted=api_key_enc,
        api_secret_encrypted=api_secret_enc,
        label=body.label,
    )
    await db.commit()
    await db.refresh(wallet)
    return WalletResponse.model_validate(wallet)


@router.get("", response_model=WalletList)
async def list_wallets(db: DbDep, entity: Entity = Depends(resolve_entity)) -> WalletList:
    wallet_repo = WalletRepo(db)

    wallets = await wallet_repo.get_all(entity.id)
    return WalletList(wallets=[WalletResponse.model_validate(w) for w in wallets], total=len(wallets))


@router.delete("/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_wallet(wallet_id: uuid.UUID, db: DbDep) -> None:
    wallet_repo = WalletRepo(db)
    wallet = await wallet_repo.get_by_id(wallet_id)
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    await wallet_repo.delete(wallet)
    await db.commit()


@router.post("/{wallet_id}/sync", response_model=WalletResponse)
async def trigger_sync(wallet_id: uuid.UUID, db: DbDep) -> WalletResponse:
    """Enqueue a Celery task to sync wallet transactions."""
    from cryptotax.workers.tasks import sync_wallet_task

    wallet_repo = WalletRepo(db)
    wallet = await wallet_repo.get_by_id(wallet_id)
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    if wallet.sync_status == "SYNCING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Wallet is already syncing")

    wallet.sync_status = "SYNCING"
    await db.commit()
    await db.refresh(wallet)

    sync_wallet_task.delay(str(wallet_id))

    return WalletResponse.model_validate(wallet)


@router.post("/{wallet_id}/import-csv", response_model=dict)
async def import_csv(wallet_id: uuid.UUID, file: UploadFile, db: DbDep) -> dict:
    """Upload a Binance CSV file to import trades."""
    from cryptotax.db.models.wallet import CEXWallet
    from cryptotax.infra.cex.csv_import import BinanceCSVImporter

    wallet_repo = WalletRepo(db)
    wallet = await wallet_repo.get_by_id(wallet_id)
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    if not isinstance(wallet, CEXWallet):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV import only for CEX wallets")

    content = (await file.read()).decode("utf-8")
    importer = BinanceCSVImporter(db)
    count = await importer.import_trades(wallet, content)
    await db.commit()
    return {"imported": count}


@router.get("/{wallet_id}/status", response_model=WalletStatusResponse)
async def get_wallet_status(wallet_id: uuid.UUID, db: DbDep) -> WalletStatusResponse:
    """Returns current sync status."""
    wallet_repo = WalletRepo(db)
    wallet = await wallet_repo.get_by_id(wallet_id)
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return WalletStatusResponse.model_validate(wallet)
