"""Integration tests for Tax API endpoints."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.api.main import app
from cryptotax.db.models.account import NativeAsset, ERC20Token
from cryptotax.db.models.entity import Entity
from cryptotax.db.models.journal import JournalEntry, JournalSplit
from cryptotax.db.models.wallet import OnChainWallet


async def _setup_journal_data(session: AsyncSession):
    """Create entity, wallet, accounts, and journal entries for a swap."""
    entity = Entity(name="test_tax")
    session.add(entity)
    await session.flush()

    wallet = OnChainWallet(entity_id=entity.id, chain="ethereum", address="0x1111")
    session.add(wallet)
    await session.flush()

    # Native ETH account
    eth_account = NativeAsset(
        wallet_id=wallet.id, account_type="ASSET", symbol="ETH", label="ETH"
    )
    usdc_account = ERC20Token(
        wallet_id=wallet.id, account_type="ASSET", symbol="USDC", label="USDC"
    )
    session.add_all([eth_account, usdc_account])
    await session.flush()

    # Journal entry 1: Buy 1 ETH (receive ETH, send USDC)
    buy_entry = JournalEntry(
        entity_id=entity.id,
        entry_type="SWAP",
        description="Buy ETH",
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
    )
    session.add(buy_entry)
    await session.flush()

    session.add_all([
        JournalSplit(
            journal_entry_id=buy_entry.id, account_id=eth_account.id,
            quantity=Decimal("1"), value_usd=Decimal("2000"), value_vnd=Decimal("50000000"),
        ),
        JournalSplit(
            journal_entry_id=buy_entry.id, account_id=usdc_account.id,
            quantity=Decimal("-2000"), value_usd=Decimal("-2000"), value_vnd=Decimal("-50000000"),
        ),
    ])

    # Journal entry 2: Sell 0.5 ETH at $3000 each
    sell_entry = JournalEntry(
        entity_id=entity.id,
        entry_type="SWAP",
        description="Sell ETH",
        timestamp=datetime(2025, 6, 1, tzinfo=UTC),
    )
    session.add(sell_entry)
    await session.flush()

    session.add_all([
        JournalSplit(
            journal_entry_id=sell_entry.id, account_id=eth_account.id,
            quantity=Decimal("-0.5"), value_usd=Decimal("-1500"), value_vnd=Decimal("-37500000"),
        ),
        JournalSplit(
            journal_entry_id=sell_entry.id, account_id=usdc_account.id,
            quantity=Decimal("1500"), value_usd=Decimal("1500"), value_vnd=Decimal("37500000"),
        ),
    ])

    await session.commit()
    return entity


@pytest.fixture()
async def tax_client(session):
    """Create test client with journal data."""
    entity = await _setup_journal_data(session)

    from cryptotax.api.deps import get_db
    app.dependency_overrides[get_db] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, entity
    app.dependency_overrides.clear()


class TestTaxCalculateAPI:
    async def test_calculate_returns_results(self, tax_client):
        client, entity = tax_client
        resp = await client.post("/api/tax/calculate", json={
            "entity_id": str(entity.id),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "closed_lots" in data
        assert "open_lots" in data
        assert "taxable_transfers" in data

    async def test_calculate_has_realized_gains(self, tax_client):
        client, entity = tax_client
        resp = await client.post("/api/tax/calculate", json={
            "entity_id": str(entity.id),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        data = resp.json()
        summary = data["summary"]

        # Should have closed lots from selling ETH
        assert summary["closed_lot_count"] > 0
        # Should have open lots (0.5 ETH remaining)
        assert summary["open_lot_count"] > 0

    async def test_calculate_default_entity(self, tax_client):
        client, _ = tax_client
        resp = await client.post("/api/tax/calculate", json={
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        assert resp.status_code == 200


class TestTaxReadEndpoints:
    async def test_realized_gains_empty(self, tax_client):
        client, _ = tax_client
        resp = await client.get("/api/tax/realized-gains")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_open_lots_empty(self, tax_client):
        client, _ = tax_client
        resp = await client.get("/api/tax/open-lots")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_realized_gains_after_calculate(self, tax_client):
        client, entity = tax_client
        # Run calculation first
        await client.post("/api/tax/calculate", json={
            "entity_id": str(entity.id),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        # Now query
        resp = await client.get("/api/tax/realized-gains")
        assert resp.status_code == 200
        gains = resp.json()
        assert len(gains) > 0
        assert "gain_usd" in gains[0]

    async def test_open_lots_after_calculate(self, tax_client):
        client, entity = tax_client
        await client.post("/api/tax/calculate", json={
            "entity_id": str(entity.id),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        resp = await client.get("/api/tax/open-lots")
        assert resp.status_code == 200
        lots = resp.json()
        assert len(lots) > 0
        assert "remaining_quantity" in lots[0]

    async def test_summary_empty(self, tax_client):
        client, _ = tax_client
        resp = await client.get("/api/tax/summary")
        assert resp.status_code == 200
        # Could be null or empty
