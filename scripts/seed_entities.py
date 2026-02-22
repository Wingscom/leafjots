"""Seed real global DeFi entities into the database.

Usage:
    PYTHONPATH=src python scripts/seed_entities.py

Idempotent: safe to run multiple times. Skips entities/wallets that already exist.
Adds 2 real global DeFi entities (USD base) with public Ethereum wallets.

After seeding, trigger TX loading via:
    PYTHONPATH=src python scripts/e2e_test.py
  or via dashboard: POST /api/wallets/{id}/sync
"""

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(name)s - %(message)s")
logger = logging.getLogger("seed_entities")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Entity definitions — real public Ethereum addresses with DeFi history
# ---------------------------------------------------------------------------
ENTITIES = [
    {
        # Well-known DeFi power user: Aave deposits, Uniswap V3 swaps, Curve LPs
        # Active personal wallet with diverse protocol interactions
        "name": "DeFi Power User Alpha",
        "base_currency": "USD",
        "wallets": [
            {
                "chain": "ethereum",
                # Tetranode — prolific DeFi user, Aave/Curve/Uniswap regular
                "address": "0x9c5083dd4838e120dbeac44c052179692aa5dac5",
                "label": "Alpha: Tetranode (Aave/Curve/Uni V3)",
            },
            {
                "chain": "ethereum",
                # DCFGod — well-known on-chain DeFi researcher/trader
                "address": "0x4a18a50a8328b42773268b4b436254ccf9e4a2dc",
                "label": "Alpha: DCFGod (DeFi trader)",
            },
        ],
    },
    {
        # Another well-known DeFi participant — multi-protocol user
        "name": "DeFi Power User Beta",
        "base_currency": "USD",
        "wallets": [
            {
                "chain": "ethereum",
                # Lido whale staker + Aave user, moderate TX volume
                "address": "0x7f367cc41522ce07553e823bf3be79a889debe1b",
                "label": "Beta: Lido/Aave Whale Staker",
            },
            {
                "chain": "ethereum",
                # Active Uniswap V3 LP + Curve farmer
                "address": "0x5f65f7b609678448494de4c87521cdf6cef1e932",
                "label": "Beta: Uniswap V3 LP / Curve Farmer",
            },
        ],
    },
]


def separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


async def main() -> None:
    from cryptotax.config import settings
    from cryptotax.db.session import build_engine, build_session_factory

    separator("Seed: Real Global DeFi Entities")
    print(f"Database: {settings.db_host}:{settings.db_port}/{settings.db_name}\n")

    engine = build_engine(settings.database_url, echo=False)
    session_factory = build_session_factory(engine)

    async with session_factory() as session:
        try:
            await seed(session)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Seeding failed")
            sys.exit(1)

    await engine.dispose()
    separator("Seeding Complete")


async def seed(session) -> None:
    from sqlalchemy import select

    from cryptotax.db.models.entity import Entity
    from cryptotax.db.repos.entity_repo import EntityRepo
    from cryptotax.db.repos.wallet_repo import WalletRepo
    from cryptotax.domain.enums import Chain

    entity_repo = EntityRepo(session)
    wallet_repo = WalletRepo(session)

    total_entities_created = 0
    total_wallets_created = 0
    total_wallets_skipped = 0

    for spec in ENTITIES:
        # --- get or create entity by name ---
        result = await session.execute(
            select(Entity).where(Entity.name == spec["name"], Entity.deleted_at.is_(None))
        )
        entity = result.scalar_one_or_none()

        if entity is None:
            entity = await entity_repo.create(name=spec["name"], base_currency=spec["base_currency"])
            status = "created"
            total_entities_created += 1
        else:
            status = "existing"

        print(f"Entity: {entity.name} ({entity.base_currency})  [{status}]  id={entity.id}")

        # --- get or create wallets ---
        for w in spec["wallets"]:
            chain = Chain(w["chain"])
            existing = await wallet_repo.get_by_chain_and_address(entity.id, chain, w["address"])

            if existing is None:
                wallet = await wallet_repo.create(
                    entity_id=entity.id,
                    chain=chain,
                    address=w["address"],
                    label=w["label"],
                )
                wstatus = "created"
                total_wallets_created += 1
            else:
                wallet = existing
                wstatus = "skipped"
                total_wallets_skipped += 1

            print(f"  [{wstatus:7s}] {wallet.label:<40s}  {w['address']}")

        print()

    print(
        f"Done. {total_entities_created} entities created, "
        f"{total_wallets_created} wallets created, "
        f"{total_wallets_skipped} wallets skipped."
    )


if __name__ == "__main__":
    asyncio.run(main())
