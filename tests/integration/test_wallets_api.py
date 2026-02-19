import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cryptotax.api.deps import get_db
from cryptotax.api.main import app
from cryptotax.db.session import Base
import cryptotax.db.models  # noqa: F401


@pytest.fixture()
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestWalletsAPI:
    async def test_list_wallets_empty(self, client):
        res = await client.get("/api/wallets")
        assert res.status_code == 200
        data = res.json()
        assert data["wallets"] == []
        assert data["total"] == 0

    async def test_add_wallet(self, client):
        res = await client.post("/api/wallets", json={
            "chain": "ethereum",
            "address": "0xAbCdEf1234567890abcdef1234567890ABCDEF12",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["chain"] == "ethereum"
        assert data["address"] == "0xabcdef1234567890abcdef1234567890abcdef12"
        assert data["sync_status"] == "IDLE"
        assert data["last_synced_at"] is None
        assert "id" in data

    async def test_add_wallet_with_label(self, client):
        res = await client.post("/api/wallets", json={
            "chain": "base",
            "address": "0x1234",
            "label": "My Base Wallet",
        })
        assert res.status_code == 201
        assert res.json()["label"] == "My Base Wallet"

    async def test_add_wallet_dedup_409(self, client):
        payload = {"chain": "ethereum", "address": "0xdeadbeef"}
        await client.post("/api/wallets", json=payload)
        res = await client.post("/api/wallets", json=payload)
        assert res.status_code == 409

    async def test_add_wallet_dedup_case_insensitive(self, client):
        await client.post("/api/wallets", json={"chain": "ethereum", "address": "0xDeAdBeEf"})
        res = await client.post("/api/wallets", json={"chain": "ethereum", "address": "0xDEADBEEF"})
        assert res.status_code == 409

    async def test_list_wallets_after_add(self, client):
        await client.post("/api/wallets", json={"chain": "ethereum", "address": "0x1111"})
        await client.post("/api/wallets", json={"chain": "arbitrum", "address": "0x2222"})

        res = await client.get("/api/wallets")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["wallets"]) == 2

    async def test_delete_wallet(self, client):
        add_res = await client.post("/api/wallets", json={"chain": "ethereum", "address": "0xaaa"})
        wallet_id = add_res.json()["id"]

        del_res = await client.delete(f"/api/wallets/{wallet_id}")
        assert del_res.status_code == 204

        list_res = await client.get("/api/wallets")
        assert list_res.json()["total"] == 0

    async def test_delete_wallet_not_found(self, client):
        res = await client.delete(f"/api/wallets/{uuid.uuid4()}")
        assert res.status_code == 404

    async def test_get_wallet_status(self, client):
        add_res = await client.post("/api/wallets", json={"chain": "ethereum", "address": "0xbbb"})
        wallet_id = add_res.json()["id"]

        res = await client.get(f"/api/wallets/{wallet_id}/status")
        assert res.status_code == 200
        data = res.json()
        assert data["sync_status"] == "IDLE"
        assert data["last_synced_at"] is None

    async def test_trigger_sync_dispatches_celery(self, client):
        add_res = await client.post("/api/wallets", json={"chain": "ethereum", "address": "0xccc"})
        wallet_id = add_res.json()["id"]

        mock_task = MagicMock()
        with patch("cryptotax.workers.tasks.sync_wallet_task", mock_task):
            res = await client.post(f"/api/wallets/{wallet_id}/sync")
        assert res.status_code == 200
        assert res.json()["sync_status"] == "SYNCING"
        mock_task.delay.assert_called_once_with(wallet_id)

    async def test_invalid_chain_rejected(self, client):
        res = await client.post("/api/wallets", json={"chain": "invalid_chain", "address": "0x1234"})
        assert res.status_code == 422

    async def test_health_endpoint_still_works(self, client):
        res = await client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
