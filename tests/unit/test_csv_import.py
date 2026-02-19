import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cryptotax.api.deps import get_db
from cryptotax.api.main import app
from cryptotax.db.models.csv_import import CsvImport, CsvImportRow
from cryptotax.db.repos.csv_import_repo import CsvImportRepo
from cryptotax.db.session import Base
import cryptotax.db.models  # noqa: F401


VALID_CSV = (
    '"User_ID","UTC_Time","Account","Operation","Coin","Change","Remark"\n'
    '"123456","2024-01-15 10:30:00","Spot","Transaction Buy","BTC","0.001",""\n'
    '"123456","2024-01-15 10:30:00","Spot","Transaction Spend","USDT","-35.50",""\n'
    '"123456","2024-01-15 10:30:00","Spot","Transaction Fee","BTC","-0.0000075",""\n'
)

MISSING_COLUMNS_CSV = (
    '"User_ID","UTC_Time","Account"\n'
    '"123456","2024-01-15 10:30:00","Spot"\n'
)


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


@pytest.fixture()
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _create_entity(client: AsyncClient) -> str:
    """Helper: create entity and return its ID."""
    res = await client.post("/api/entities", json={"name": "TestEntity"})
    assert res.status_code == 201
    return res.json()["id"]


class TestUploadEndpoint:
    """Tests for POST /api/imports/upload."""

    async def test_upload_valid_csv(self, client):
        entity_id = await _create_entity(client)

        res = await client.post(
            "/api/imports/upload",
            data={"entity_id": entity_id, "exchange": "binance"},
            files={"file": ("export.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["filename"] == "export.csv"
        assert data["row_count"] == 3
        assert data["status"] == "uploaded"
        assert "import_id" in data

    async def test_upload_missing_columns_returns_400(self, client):
        entity_id = await _create_entity(client)

        res = await client.post(
            "/api/imports/upload",
            data={"entity_id": entity_id, "exchange": "binance"},
            files={"file": ("bad.csv", io.BytesIO(MISSING_COLUMNS_CSV.encode()), "text/csv")},
        )
        assert res.status_code == 400
        assert "missing required columns" in res.json()["detail"].lower()

    async def test_upload_empty_csv_returns_400(self, client):
        entity_id = await _create_entity(client)
        empty_csv = '"User_ID","UTC_Time","Account","Operation","Coin","Change","Remark"\n'

        res = await client.post(
            "/api/imports/upload",
            data={"entity_id": entity_id, "exchange": "binance"},
            files={"file": ("empty.csv", io.BytesIO(empty_csv.encode()), "text/csv")},
        )
        assert res.status_code == 400
        assert "no data rows" in res.json()["detail"].lower()


class TestListEndpoint:
    """Tests for GET /api/imports."""

    async def test_list_imports_empty(self, client):
        entity_id = await _create_entity(client)

        res = await client.get("/api/imports", params={"entity_id": entity_id})
        assert res.status_code == 200
        data = res.json()
        assert data["imports"] == []
        assert data["total"] == 0

    async def test_list_imports_returns_only_entity_imports(self, client):
        e1 = await _create_entity(client)
        # Create second entity
        e2_res = await client.post("/api/entities", json={"name": "Entity2"})
        e2 = e2_res.json()["id"]

        # Upload to entity 1
        await client.post(
            "/api/imports/upload",
            data={"entity_id": e1, "exchange": "binance"},
            files={"file": ("e1.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")},
        )
        # Upload to entity 2
        await client.post(
            "/api/imports/upload",
            data={"entity_id": e2, "exchange": "binance"},
            files={"file": ("e2.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")},
        )

        # List for entity 1
        res = await client.get("/api/imports", params={"entity_id": e1})
        data = res.json()
        assert data["total"] == 1
        assert len(data["imports"]) == 1
        assert data["imports"][0]["filename"] == "e1.csv"

        # List for entity 2
        res2 = await client.get("/api/imports", params={"entity_id": e2})
        data2 = res2.json()
        assert data2["total"] == 1
        assert data2["imports"][0]["filename"] == "e2.csv"


class TestDetailEndpoint:
    """Tests for GET /api/imports/{import_id}."""

    async def test_get_import_detail(self, client):
        entity_id = await _create_entity(client)

        upload_res = await client.post(
            "/api/imports/upload",
            data={"entity_id": entity_id, "exchange": "binance"},
            files={"file": ("detail.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")},
        )
        import_id = upload_res.json()["import_id"]

        res = await client.get(f"/api/imports/{import_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["filename"] == "detail.csv"
        assert data["row_count"] == 3
        assert len(data["rows"]) == 3
        # Check first row fields
        row1 = data["rows"][0]
        assert row1["row_number"] == 1
        assert row1["operation"] == "Transaction Buy"
        assert row1["coin"] == "BTC"
        assert row1["change"] == "0.001"

    async def test_get_import_not_found(self, client):
        res = await client.get(f"/api/imports/{uuid.uuid4()}")
        assert res.status_code == 404


class TestCsvImportRepo:
    """Tests for CsvImportRepo methods."""

    async def test_create_import_stores_all_fields(self, session):
        from cryptotax.db.models.entity import Entity

        entity = Entity(name="RepoTest", base_currency="VND")
        session.add(entity)
        await session.flush()

        repo = CsvImportRepo(session)
        rows_data = [
            {
                "utc_time": "2024-01-15 10:30:00",
                "account": "Spot",
                "operation": "Transaction Buy",
                "coin": "BTC",
                "change": "0.001",
                "remark": "test remark",
            },
            {
                "utc_time": "2024-01-15 10:30:00",
                "account": "Spot",
                "operation": "Transaction Spend",
                "coin": "USDT",
                "change": "-35.50",
                "remark": None,
            },
        ]

        csv_import = await repo.create_import(
            entity_id=entity.id,
            exchange="binance",
            filename="test.csv",
            rows_data=rows_data,
        )

        assert csv_import.row_count == 2
        assert csv_import.exchange == "binance"
        assert csv_import.filename == "test.csv"
        assert csv_import.status == "uploaded"
        assert len(csv_import.rows) == 2

        # Verify row fields
        row1 = sorted(csv_import.rows, key=lambda r: r.row_number)[0]
        assert row1.row_number == 1
        assert row1.utc_time == "2024-01-15 10:30:00"
        assert row1.account == "Spot"
        assert row1.operation == "Transaction Buy"
        assert row1.coin == "BTC"
        assert row1.change == "0.001"
        assert row1.remark == "test remark"
        assert row1.status == "pending"

    async def test_list_for_entity_pagination(self, session):
        from cryptotax.db.models.entity import Entity

        entity = Entity(name="PagTest", base_currency="VND")
        session.add(entity)
        await session.flush()

        repo = CsvImportRepo(session)

        # Create 3 imports
        for i in range(3):
            await repo.create_import(
                entity_id=entity.id,
                exchange="binance",
                filename=f"file_{i}.csv",
                rows_data=[{"utc_time": "t", "account": "a", "operation": "o", "coin": "c", "change": "1"}],
            )

        # Get page 1 with limit 2
        imports, total = await repo.list_for_entity(entity.id, limit=2, offset=0)
        assert total == 3
        assert len(imports) == 2

        # Get page 2
        imports2, total2 = await repo.list_for_entity(entity.id, limit=2, offset=2)
        assert total2 == 3
        assert len(imports2) == 1
