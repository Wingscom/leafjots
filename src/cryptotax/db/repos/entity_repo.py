import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.entity import Entity
from cryptotax.db.models.wallet import Wallet
from cryptotax.domain.enums import Currency

DEFAULT_ENTITY_NAME = "Default"


class EntityRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_default(self) -> Optional[Entity]:
        result = await self._session.execute(
            select(Entity).where(Entity.deleted_at.is_(None)).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create_default(self) -> Entity:
        entity = await self.get_default()
        if entity is None:
            entity = Entity(name=DEFAULT_ENTITY_NAME, base_currency=Currency.VND.value)
            self._session.add(entity)
            await self._session.flush()
        return entity

    async def get_by_id(self, entity_id: uuid.UUID) -> Optional[Entity]:
        result = await self._session.execute(
            select(Entity).where(Entity.id == entity_id, Entity.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Entity]:
        """List all non-deleted entities ordered by name."""
        result = await self._session.execute(
            select(Entity)
            .where(Entity.deleted_at.is_(None))
            .order_by(Entity.name)
        )
        return list(result.scalars().all())

    async def create(self, name: str, base_currency: str = "VND") -> Entity:
        """Create a new entity."""
        entity = Entity(name=name, base_currency=base_currency)
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity_id: uuid.UUID, **kwargs) -> Optional[Entity]:
        """Update entity fields. Only non-None values with matching attributes are set."""
        entity = await self.get_by_id(entity_id)
        if entity is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(entity, key):
                setattr(entity, key, value)
        await self._session.flush()
        return entity

    async def soft_delete(self, entity_id: uuid.UUID) -> bool:
        """Soft-delete an entity by setting deleted_at."""
        entity = await self.get_by_id(entity_id)
        if entity is None:
            return False
        entity.deleted_at = datetime.now(timezone.utc)
        await self._session.flush()
        return True

    async def count_wallets(self, entity_id: uuid.UUID) -> int:
        """Count wallets belonging to an entity."""
        result = await self._session.execute(
            select(func.count(Wallet.id)).where(Wallet.entity_id == entity_id)
        )
        return result.scalar() or 0
