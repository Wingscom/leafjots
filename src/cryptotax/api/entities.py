import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.deps import get_db
from cryptotax.api.schemas.entities import (
    EntityCreateRequest,
    EntityListResponse,
    EntityResponse,
    EntityUpdateRequest,
)
from cryptotax.db.repos.entity_repo import EntityRepo

router = APIRouter(prefix="/api/entities", tags=["entities"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=EntityListResponse)
async def list_entities(db: DbDep) -> EntityListResponse:
    """List all non-deleted entities with wallet counts."""
    repo = EntityRepo(db)
    entities = await repo.list_all()
    items = []
    for e in entities:
        wc = await repo.count_wallets(e.id)
        items.append(EntityResponse(
            id=e.id,
            name=e.name,
            base_currency=e.base_currency,
            wallet_count=wc,
            created_at=e.created_at,
            updated_at=e.updated_at,
        ))
    return EntityListResponse(entities=items, total=len(items))


@router.post("", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(body: EntityCreateRequest, db: DbDep) -> EntityResponse:
    """Create a new entity."""
    repo = EntityRepo(db)
    entity = await repo.create(name=body.name, base_currency=body.base_currency)
    await db.commit()
    await db.refresh(entity)
    return EntityResponse(
        id=entity.id,
        name=entity.name,
        base_currency=entity.base_currency,
        wallet_count=0,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: uuid.UUID, db: DbDep) -> EntityResponse:
    """Get a single entity by ID."""
    repo = EntityRepo(db)
    entity = await repo.get_by_id(entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    wc = await repo.count_wallets(entity.id)
    return EntityResponse(
        id=entity.id,
        name=entity.name,
        base_currency=entity.base_currency,
        wallet_count=wc,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.patch("/{entity_id}", response_model=EntityResponse)
async def update_entity(entity_id: uuid.UUID, body: EntityUpdateRequest, db: DbDep) -> EntityResponse:
    """Update entity name and/or base_currency."""
    repo = EntityRepo(db)
    entity = await repo.update(entity_id, name=body.name, base_currency=body.base_currency)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    await db.commit()
    await db.refresh(entity)
    wc = await repo.count_wallets(entity.id)
    return EntityResponse(
        id=entity.id,
        name=entity.name,
        base_currency=entity.base_currency,
        wallet_count=wc,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity(entity_id: uuid.UUID, db: DbDep) -> None:
    """Soft-delete an entity."""
    repo = EntityRepo(db)
    deleted = await repo.soft_delete(entity_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    await db.commit()
