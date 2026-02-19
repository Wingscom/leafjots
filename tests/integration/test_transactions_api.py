from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cryptotax.api.deps import get_db
from cryptotax.api.main import app
from cryptotax.db.models.transaction import Transaction
from cryptotax.db.session import Base
from cryptotax.domain.enums import TxStatus
import cryptotax.db.models  # noqa: F401

import pytest


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
        yield ac, factory
    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _add_wallet(client) -> str:
    res = await client.post("/api/wallets", json={"chain": "ethereum", "address": "0xtest123"})
    return res.json()["id"]


async def _seed_txs(factory, wallet_id: str, count: int = 5) -> list[str]:
    import uuid

    async with factory() as session:
        hashes = []
        for i in range(count):
            tx_hash = f"0x{i:064x}"
            hashes.append(tx_hash)
            session.add(Transaction(
                wallet_id=uuid.UUID(wallet_id),
                chain="ethereum",
                tx_hash=tx_hash,
                block_number=1000 + i,
                timestamp=1700000000 + i,
                from_addr="0xaaaa",
                to_addr="0xbbbb",
                value_wei=10**18,
                gas_used=21000,
                status=TxStatus.LOADED.value,
                tx_data='{"test": true}',
            ))
        await session.commit()
    return hashes


class TestTransactionsAPI:
    async def test_list_empty(self, client):
        ac, _ = client
        res = await ac.get("/api/transactions")
        assert res.status_code == 200
        data = res.json()
        assert data["transactions"] == []
        assert data["total"] == 0

    async def test_list_with_data(self, client):
        ac, factory = client
        wallet_id = await _add_wallet(ac)
        await _seed_txs(factory, wallet_id, count=3)

        res = await ac.get("/api/transactions")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert len(data["transactions"]) == 3

    async def test_list_pagination(self, client):
        ac, factory = client
        wallet_id = await _add_wallet(ac)
        await _seed_txs(factory, wallet_id, count=10)

        res = await ac.get("/api/transactions?limit=3&offset=0")
        data = res.json()
        assert data["total"] == 10
        assert len(data["transactions"]) == 3
        assert data["limit"] == 3
        assert data["offset"] == 0

        res2 = await ac.get("/api/transactions?limit=3&offset=3")
        data2 = res2.json()
        assert len(data2["transactions"]) == 3

        # No overlap
        hashes1 = {tx["tx_hash"] for tx in data["transactions"]}
        hashes2 = {tx["tx_hash"] for tx in data2["transactions"]}
        assert hashes1.isdisjoint(hashes2)

    async def test_list_filter_by_wallet_id(self, client):
        ac, factory = client
        wallet_id = await _add_wallet(ac)
        await _seed_txs(factory, wallet_id, count=3)

        res = await ac.get(f"/api/transactions?wallet_id={wallet_id}")
        assert res.status_code == 200
        assert res.json()["total"] == 3

    async def test_list_filter_by_status(self, client):
        ac, factory = client
        wallet_id = await _add_wallet(ac)
        await _seed_txs(factory, wallet_id, count=3)

        res = await ac.get("/api/transactions?status=LOADED")
        assert res.json()["total"] == 3

        res2 = await ac.get("/api/transactions?status=PARSED")
        assert res2.json()["total"] == 0

    async def test_get_transaction_by_hash(self, client):
        ac, factory = client
        wallet_id = await _add_wallet(ac)
        hashes = await _seed_txs(factory, wallet_id, count=1)

        res = await ac.get(f"/api/transactions/{hashes[0]}")
        assert res.status_code == 200
        data = res.json()
        assert data["tx_hash"] == hashes[0]
        assert data["from_addr"] == "0xaaaa"
        assert data["to_addr"] == "0xbbbb"
        assert data["gas_used"] == 21000
        assert data["tx_data"] == '{"test": true}'

    async def test_get_transaction_not_found(self, client):
        ac, _ = client
        res = await ac.get("/api/transactions/0xnonexistent")
        assert res.status_code == 404

    async def test_transaction_response_fields(self, client):
        ac, factory = client
        wallet_id = await _add_wallet(ac)
        await _seed_txs(factory, wallet_id, count=1)

        res = await ac.get("/api/transactions")
        tx = res.json()["transactions"][0]
        # TransactionResponse should NOT include tx_data (only TransactionDetail does)
        assert "tx_data" not in tx
        assert "id" in tx
        assert "chain" in tx
        assert "timestamp" in tx
        assert "value_wei" in tx
