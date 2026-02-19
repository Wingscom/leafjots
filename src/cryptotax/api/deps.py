from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    from cryptotax.accounting.bookkeeper import Bookkeeper

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cryptotax.container import Container
from cryptotax.db.models.entity import Entity
from cryptotax.db.repos.entity_repo import EntityRepo


@inject
async def get_db(
    session_factory: async_sessionmaker[AsyncSession] = Depends(Provide[Container.session_factory]),
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


async def resolve_entity(
    entity_id: uuid.UUID | None = Query(None, description="Entity ID (uses default if omitted)"),
    db: AsyncSession = Depends(get_db),
) -> Entity:
    """Resolve entity from optional query param, falling back to default entity."""
    repo = EntityRepo(db)
    if entity_id:
        entity = await repo.get_by_id(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity
    entity = await repo.get_or_create_default()
    return entity


def build_bookkeeper(db: AsyncSession) -> "Bookkeeper":
    """Create a Bookkeeper wired with PriceService + CoinGecko."""
    from cryptotax.accounting.bookkeeper import Bookkeeper
    from cryptotax.config import settings
    from cryptotax.infra.http.rate_limited_client import RateLimitedClient
    from cryptotax.infra.price.coingecko import CoinGeckoProvider
    from cryptotax.infra.price.service import PriceService
    from cryptotax.parser.registry import build_default_registry

    http_client = RateLimitedClient(rate_per_second=10.0, timeout=30.0)
    coingecko = CoinGeckoProvider(http_client, api_key=settings.coingecko_api_key)
    price_service = PriceService(db, coingecko)
    registry = build_default_registry()
    return Bookkeeper(db, registry, price_service=price_service)
