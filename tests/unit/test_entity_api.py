import uuid

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


class TestEntityCRUD:
    """Tests for POST/GET/PATCH/DELETE /api/entities."""

    async def test_create_entity(self, client):
        res = await client.post("/api/entities", json={
            "name": "My Company",
            "base_currency": "USD",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "My Company"
        assert data["base_currency"] == "USD"
        assert data["wallet_count"] == 0
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_entity_default_currency(self, client):
        res = await client.post("/api/entities", json={"name": "VN Entity"})
        assert res.status_code == 201
        assert res.json()["base_currency"] == "VND"

    async def test_list_entities(self, client):
        await client.post("/api/entities", json={"name": "Entity A"})
        await client.post("/api/entities", json={"name": "Entity B"})

        res = await client.get("/api/entities")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["entities"]) == 2
        # Ordered by name
        names = [e["name"] for e in data["entities"]]
        assert names == ["Entity A", "Entity B"]

    async def test_list_entities_with_wallet_count(self, client):
        # Create entity
        ent_res = await client.post("/api/entities", json={"name": "WalletOwner"})
        entity_id = ent_res.json()["id"]

        # Add wallets to this entity
        await client.post("/api/wallets", json={
            "chain": "ethereum",
            "address": "0x1111",
        }, params={"entity_id": entity_id})
        await client.post("/api/wallets", json={
            "chain": "ethereum",
            "address": "0x2222",
        }, params={"entity_id": entity_id})

        res = await client.get("/api/entities")
        data = res.json()
        entity = [e for e in data["entities"] if e["id"] == entity_id][0]
        assert entity["wallet_count"] == 2

    async def test_get_entity_by_id(self, client):
        create_res = await client.post("/api/entities", json={"name": "GetMe"})
        entity_id = create_res.json()["id"]

        res = await client.get(f"/api/entities/{entity_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "GetMe"

    async def test_get_entity_not_found(self, client):
        res = await client.get(f"/api/entities/{uuid.uuid4()}")
        assert res.status_code == 404

    async def test_update_entity(self, client):
        create_res = await client.post("/api/entities", json={"name": "OldName"})
        entity_id = create_res.json()["id"]

        res = await client.patch(f"/api/entities/{entity_id}", json={"name": "NewName"})
        assert res.status_code == 200
        assert res.json()["name"] == "NewName"

    async def test_update_entity_partial(self, client):
        create_res = await client.post("/api/entities", json={"name": "Keep", "base_currency": "USD"})
        entity_id = create_res.json()["id"]

        # Update only currency, name stays
        res = await client.patch(f"/api/entities/{entity_id}", json={"base_currency": "VND"})
        assert res.status_code == 200
        assert res.json()["name"] == "Keep"
        assert res.json()["base_currency"] == "VND"

    async def test_update_entity_not_found(self, client):
        res = await client.patch(f"/api/entities/{uuid.uuid4()}", json={"name": "X"})
        assert res.status_code == 404

    async def test_delete_entity(self, client):
        create_res = await client.post("/api/entities", json={"name": "ToDelete"})
        entity_id = create_res.json()["id"]

        del_res = await client.delete(f"/api/entities/{entity_id}")
        assert del_res.status_code == 204

        # Should not appear in list
        list_res = await client.get("/api/entities")
        ids = [e["id"] for e in list_res.json()["entities"]]
        assert entity_id not in ids

    async def test_delete_entity_not_found(self, client):
        res = await client.delete(f"/api/entities/{uuid.uuid4()}")
        assert res.status_code == 404


class TestEntityScoping:
    """Test that endpoints respect entity_id query param."""

    async def test_wallets_scoped_by_entity(self, client):
        # Create two entities
        e1 = (await client.post("/api/entities", json={"name": "E1"})).json()
        e2 = (await client.post("/api/entities", json={"name": "E2"})).json()

        # Add wallets to each
        await client.post("/api/wallets", json={
            "chain": "ethereum", "address": "0xaaaa",
        }, params={"entity_id": e1["id"]})
        await client.post("/api/wallets", json={
            "chain": "ethereum", "address": "0xbbbb",
        }, params={"entity_id": e2["id"]})

        # List wallets for E1
        res1 = await client.get("/api/wallets", params={"entity_id": e1["id"]})
        assert res1.status_code == 200
        assert res1.json()["total"] == 1
        assert res1.json()["wallets"][0]["address"] == "0xaaaa"

        # List wallets for E2
        res2 = await client.get("/api/wallets", params={"entity_id": e2["id"]})
        assert res2.status_code == 200
        assert res2.json()["total"] == 1
        assert res2.json()["wallets"][0]["address"] == "0xbbbb"

    async def test_accounts_scoped_by_entity(self, client):
        # With no wallets/accounts, should return empty
        e1 = (await client.post("/api/entities", json={"name": "AccE1"})).json()
        res = await client.get("/api/accounts", params={"entity_id": e1["id"]})
        assert res.status_code == 200
        assert res.json()["accounts"] == []

    async def test_journal_scoped_by_entity(self, client):
        e1 = (await client.post("/api/entities", json={"name": "JournE1"})).json()
        res = await client.get("/api/journal", params={"entity_id": e1["id"]})
        assert res.status_code == 200
        assert res.json()["entries"] == []
        assert res.json()["total"] == 0

    async def test_tax_realized_gains_scoped(self, client):
        e1 = (await client.post("/api/entities", json={"name": "TaxE1"})).json()
        res = await client.get("/api/tax/realized-gains", params={"entity_id": e1["id"]})
        assert res.status_code == 200
        assert res.json() == []

    async def test_tax_open_lots_scoped(self, client):
        e1 = (await client.post("/api/entities", json={"name": "TaxE2"})).json()
        res = await client.get("/api/tax/open-lots", params={"entity_id": e1["id"]})
        assert res.status_code == 200
        assert res.json() == []

    async def test_errors_scoped_by_entity(self, client):
        e1 = (await client.post("/api/entities", json={"name": "ErrE1"})).json()
        res = await client.get("/api/errors", params={"entity_id": e1["id"]})
        assert res.status_code == 200
        assert res.json()["errors"] == []
        assert res.json()["total"] == 0

    async def test_error_summary_scoped_by_entity(self, client):
        e1 = (await client.post("/api/entities", json={"name": "ErrSumE1"})).json()
        res = await client.get("/api/errors/summary", params={"entity_id": e1["id"]})
        assert res.status_code == 200
        assert res.json()["total"] == 0

    async def test_reports_scoped_by_entity(self, client):
        e1 = (await client.post("/api/entities", json={"name": "RepE1"})).json()
        res = await client.get("/api/reports", params={"entity_id": e1["id"]})
        assert res.status_code == 200
        assert res.json() == []

    async def test_transactions_scoped_by_entity(self, client):
        e1 = (await client.post("/api/entities", json={"name": "TxE1"})).json()
        res = await client.get("/api/transactions", params={"entity_id": e1["id"]})
        assert res.status_code == 200
        assert res.json()["transactions"] == []
        assert res.json()["total"] == 0


class TestBackwardCompatibility:
    """Test that omitting entity_id uses default entity (backward compatible)."""

    async def test_wallets_without_entity_id(self, client):
        # Add wallet without entity_id — should use default
        res = await client.post("/api/wallets", json={
            "chain": "ethereum",
            "address": "0xdefault1",
        })
        assert res.status_code == 201

        # List without entity_id — should see the wallet
        list_res = await client.get("/api/wallets")
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1

    async def test_journal_without_entity_id(self, client):
        res = await client.get("/api/journal")
        assert res.status_code == 200

    async def test_accounts_without_entity_id(self, client):
        res = await client.get("/api/accounts")
        assert res.status_code == 200

    async def test_transactions_without_entity_id(self, client):
        res = await client.get("/api/transactions")
        assert res.status_code == 200

    async def test_errors_without_entity_id(self, client):
        res = await client.get("/api/errors")
        assert res.status_code == 200

    async def test_tax_endpoints_without_entity_id(self, client):
        res1 = await client.get("/api/tax/realized-gains")
        assert res1.status_code == 200
        res2 = await client.get("/api/tax/open-lots")
        assert res2.status_code == 200

    async def test_reports_without_entity_id(self, client):
        res = await client.get("/api/reports")
        assert res.status_code == 200

    async def test_invalid_entity_id_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        res = await client.get("/api/wallets", params={"entity_id": fake_id})
        assert res.status_code == 404
        assert "Entity not found" in res.json()["detail"]
