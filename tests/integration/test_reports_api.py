"""Integration tests for Reports API endpoints."""

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


async def _setup_report_data(session: AsyncSession):
    """Create entity, wallet, accounts, and journal entries for report tests."""
    entity = Entity(name="test_report")
    session.add(entity)
    await session.flush()

    wallet = OnChainWallet(entity_id=entity.id, chain="ethereum", address="0x1111")
    session.add(wallet)
    await session.flush()

    eth_account = NativeAsset(
        wallet_id=wallet.id, account_type="ASSET", symbol="ETH", label="ETH"
    )
    usdc_account = ERC20Token(
        wallet_id=wallet.id, account_type="ASSET", symbol="USDC", label="USDC"
    )
    session.add_all([eth_account, usdc_account])
    await session.flush()

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

    await session.commit()
    return entity


@pytest.fixture()
async def report_client(session):
    """Create test client with journal data."""
    entity = await _setup_report_data(session)

    from cryptotax.api.deps import get_db
    app.dependency_overrides[get_db] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, entity
    app.dependency_overrides.clear()


class TestReportsGenerateAPI:
    async def test_generate_returns_completed(self, report_client):
        client, entity = report_client
        resp = await client.post("/api/reports/generate", json={
            "entity_id": str(entity.id),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["filename"] is not None
        assert "bangketoan" in data["filename"]

    async def test_generate_default_entity(self, report_client):
        client, _ = report_client
        resp = await client.post("/api/reports/generate", json={
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        assert resp.status_code == 200


class TestReportsListAPI:
    async def test_list_empty(self, report_client):
        client, _ = report_client
        resp = await client.get("/api/reports")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_after_generate(self, report_client):
        client, entity = report_client
        # Generate first
        await client.post("/api/reports/generate", json={
            "entity_id": str(entity.id),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        # List
        resp = await client.get("/api/reports")
        assert resp.status_code == 200
        reports = resp.json()
        assert len(reports) == 1


class TestReportsStatusAPI:
    async def test_status_after_generate(self, report_client):
        client, entity = report_client
        gen_resp = await client.post("/api/reports/generate", json={
            "entity_id": str(entity.id),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        report_id = gen_resp.json()["id"]

        resp = await client.get(f"/api/reports/{report_id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    async def test_status_not_found(self, report_client):
        client, _ = report_client
        resp = await client.get("/api/reports/00000000-0000-0000-0000-000000000000/status")
        assert resp.status_code == 404


class TestReportsDownloadAPI:
    async def test_download_returns_xlsx(self, report_client):
        client, entity = report_client
        gen_resp = await client.post("/api/reports/generate", json={
            "entity_id": str(entity.id),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        report_id = gen_resp.json()["id"]

        resp = await client.get(f"/api/reports/{report_id}/download")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        assert len(resp.content) > 0

    async def test_download_not_found(self, report_client):
        client, _ = report_client
        resp = await client.get("/api/reports/00000000-0000-0000-0000-000000000000/download")
        assert resp.status_code == 404
