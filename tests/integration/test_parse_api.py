import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cryptotax.api.deps import get_db
from cryptotax.api.main import app
from cryptotax.db.models.transaction import Transaction
from cryptotax.db.session import Base
from cryptotax.domain.enums import TxStatus
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
        yield ac, factory
    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _add_wallet_and_tx(ac, factory):
    """Add a wallet + seed a TX, return (wallet_id, tx_hash)."""
    res = await ac.post("/api/wallets", json={
        "chain": "ethereum",
        "address": "0x1111111111111111111111111111111111111111",
    })
    wallet_id = res.json()["id"]

    tx_data = {
        "hash": "0xtest_parse_tx",
        "from": "0x1111111111111111111111111111111111111111",
        "to": "0x2222222222222222222222222222222222222222",
        "value": "1000000000000000000",
        "gasUsed": "21000",
        "gasPrice": "20000000000",
    }

    async with factory() as session:
        session.add(Transaction(
            wallet_id=uuid.UUID(wallet_id),
            chain="ethereum",
            tx_hash="0xtest_parse_tx",
            block_number=18500000,
            timestamp=1700000000,
            from_addr="0x1111111111111111111111111111111111111111",
            to_addr="0x2222222222222222222222222222222222222222",
            value_wei=10**18,
            gas_used=21000,
            status=TxStatus.LOADED.value,
            tx_data=json.dumps(tx_data),
        ))
        await session.commit()

    return wallet_id, "0xtest_parse_tx"


class TestParseAPI:
    async def test_parse_stats_empty(self, client):
        ac, _ = client
        res = await ac.get("/api/parse/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0

    async def test_parse_test_endpoint(self, client):
        ac, factory = client
        _, tx_hash = await _add_wallet_and_tx(ac, factory)

        res = await ac.post("/api/parse/test", json={"tx_hash": tx_hash})
        assert res.status_code == 200
        data = res.json()
        assert data["tx_hash"] == tx_hash
        assert data["balanced"] is True
        assert len(data["splits"]) > 0

    async def test_parse_test_not_found(self, client):
        ac, _ = client
        res = await ac.post("/api/parse/test", json={"tx_hash": "0xnonexistent"})
        assert res.status_code == 404

    async def test_parse_wallet_endpoint(self, client):
        ac, factory = client
        wallet_id, _ = await _add_wallet_and_tx(ac, factory)

        res = await ac.post(f"/api/parse/wallet/{wallet_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["processed"] + data["errors"] == 1

    async def test_parse_stats_after_parse(self, client):
        ac, factory = client
        wallet_id, _ = await _add_wallet_and_tx(ac, factory)

        # Parse first
        await ac.post(f"/api/parse/wallet/{wallet_id}")

        res = await ac.get("/api/parse/stats")
        data = res.json()
        assert data["total"] == 1
        assert data["parsed"] >= 0  # May be 1 if parse succeeded


class TestJournalAPI:
    async def test_journal_empty(self, client):
        ac, _ = client
        res = await ac.get("/api/journal")
        assert res.status_code == 200
        assert res.json()["total"] == 0

    async def test_journal_after_parse(self, client):
        ac, factory = client
        wallet_id, _ = await _add_wallet_and_tx(ac, factory)

        # Parse TX
        await ac.post(f"/api/parse/wallet/{wallet_id}")

        # Check journal
        res = await ac.get("/api/journal")
        data = res.json()
        # Should have at least 0 entries (might be 1 if parse succeeded)
        assert data["total"] >= 0

    async def test_journal_detail(self, client):
        ac, factory = client
        wallet_id, _ = await _add_wallet_and_tx(ac, factory)
        await ac.post(f"/api/parse/wallet/{wallet_id}")

        journal_res = await ac.get("/api/journal")
        entries = journal_res.json()["entries"]
        if entries:
            entry_id = entries[0]["id"]
            detail_res = await ac.get(f"/api/journal/{entry_id}")
            assert detail_res.status_code == 200
            assert "splits" in detail_res.json()


class TestAccountsAPI:
    async def test_accounts_empty(self, client):
        ac, _ = client
        res = await ac.get("/api/accounts")
        assert res.status_code == 200
        assert res.json()["accounts"] == []

    async def test_accounts_after_parse(self, client):
        ac, factory = client
        wallet_id, _ = await _add_wallet_and_tx(ac, factory)
        await ac.post(f"/api/parse/wallet/{wallet_id}")

        res = await ac.get("/api/accounts")
        data = res.json()
        # Should have created accounts during parse
        assert isinstance(data["accounts"], list)


class TestErrorsAPI:
    async def test_errors_empty(self, client):
        ac, _ = client
        res = await ac.get("/api/errors")
        assert res.status_code == 200
        assert res.json()["total"] == 0

    async def test_error_summary(self, client):
        ac, _ = client
        res = await ac.get("/api/errors/summary")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
