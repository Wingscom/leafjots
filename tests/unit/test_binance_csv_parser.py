"""Tests for BinanceCsvParser -- Binance Transaction History CSV parsing."""

import io
import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cryptotax.api.deps import get_db
from cryptotax.api.main import app
from cryptotax.db.models.csv_import import CsvImport, CsvImportRow
from cryptotax.db.models.entity import Entity
from cryptotax.db.models.journal import JournalEntry, JournalSplit
from cryptotax.db.models.wallet import CEXWallet
from cryptotax.db.repos.csv_import_repo import CsvImportRepo
from cryptotax.db.session import Base
from cryptotax.parser.cex.binance_csv import BinanceCsvParser
import cryptotax.db.models  # noqa: F401 -- register all models for metadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture()
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture()
async def entity(session):
    ent = Entity(name="TestEntity", base_currency="VND")
    session.add(ent)
    await session.flush()
    return ent


@pytest.fixture()
async def cex_wallet(session, entity):
    wallet = CEXWallet(
        entity_id=entity.id,
        exchange="binance",
        label="Test Binance Wallet",
        wallet_type="cex",
    )
    session.add(wallet)
    await session.flush()
    return wallet


async def _create_import_with_rows(
    session, entity_id: uuid.UUID, rows_data: list[dict]
) -> CsvImport:
    """Helper: create CsvImport + CsvImportRow records directly."""
    repo = CsvImportRepo(session)
    return await repo.create_import(
        entity_id=entity_id,
        exchange="binance",
        filename="test.csv",
        rows_data=rows_data,
    )


# ---------------------------------------------------------------------------
# Test: Spot Buy (Transaction Buy / Spend / Fee)
# ---------------------------------------------------------------------------


class TestSpotBuy:
    async def test_spot_buy_produces_swap_entry(self, session, entity, cex_wallet):
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-02 08:41:54",
                "account": "Spot",
                "operation": "Transaction Buy",
                "coin": "BTC",
                "change": "0.00008000",
            },
            {
                "utc_time": "2025-12-02 08:41:54",
                "account": "Spot",
                "operation": "Transaction Spend",
                "coin": "USDT",
                "change": "-6.92245840",
            },
            {
                "utc_time": "2025-12-02 08:41:54",
                "account": "Spot",
                "operation": "Transaction Fee",
                "coin": "BTC",
                "change": "-8E-8",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.total == 3
        assert stats.parsed == 3
        assert stats.errors == 0

        # One journal entry created
        result = await session.execute(
            select(JournalEntry).where(JournalEntry.entity_id == entity.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 1
        assert entries[0].entry_type == "SWAP"

        # 4 splits: BTC +, USDT -, BTC fee -, BTC expense +
        result = await session.execute(
            select(JournalSplit).where(JournalSplit.journal_entry_id == entries[0].id)
        )
        splits = list(result.scalars().all())
        assert len(splits) == 4

        # All rows should be marked parsed with journal_entry_id
        for row in csv_import.rows:
            await session.refresh(row)
            assert row.status == "parsed"
            assert row.journal_entry_id == entries[0].id


# ---------------------------------------------------------------------------
# Test: Spot Sell (Transaction Sold / Revenue / Fee)
# ---------------------------------------------------------------------------


class TestSpotSell:
    async def test_spot_sell_produces_swap_entry(self, session, entity, cex_wallet):
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-02 09:00:00",
                "account": "Spot",
                "operation": "Transaction Sold",
                "coin": "XRP",
                "change": "-2.90000000",
            },
            {
                "utc_time": "2025-12-02 09:00:00",
                "account": "Spot",
                "operation": "Transaction Revenue",
                "coin": "USDT",
                "change": "5.42358000",
            },
            {
                "utc_time": "2025-12-02 09:00:00",
                "account": "Spot",
                "operation": "Transaction Fee",
                "coin": "USDT",
                "change": "-0.00542358",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 3
        assert stats.errors == 0

        result = await session.execute(
            select(JournalEntry).where(JournalEntry.entity_id == entity.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 1
        assert entries[0].entry_type == "SWAP"

        # 4 splits: XRP -, USDT +, USDT fee -, USDT expense +
        result = await session.execute(
            select(JournalSplit).where(JournalSplit.journal_entry_id == entries[0].id)
        )
        splits = list(result.scalars().all())
        assert len(splits) == 4


# ---------------------------------------------------------------------------
# Test: Binance Convert
# ---------------------------------------------------------------------------


class TestConvert:
    async def test_convert_produces_swap_entry(self, session, entity, cex_wallet):
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-02 10:00:00",
                "account": "Spot",
                "operation": "Binance Convert",
                "coin": "BTC",
                "change": "-0.00001000",
            },
            {
                "utc_time": "2025-12-02 10:00:00",
                "account": "Spot",
                "operation": "Binance Convert",
                "coin": "ETH",
                "change": "0.00029406",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 2
        assert stats.errors == 0

        result = await session.execute(
            select(JournalEntry).where(JournalEntry.entity_id == entity.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 1
        assert entries[0].entry_type == "SWAP"

        # 2 splits: BTC -, ETH +
        result = await session.execute(
            select(JournalSplit).where(JournalSplit.journal_entry_id == entries[0].id)
        )
        splits = list(result.scalars().all())
        assert len(splits) == 2


# ---------------------------------------------------------------------------
# Test: Deposit
# ---------------------------------------------------------------------------


class TestDeposit:
    async def test_deposit_produces_balanced_entry(self, session, entity, cex_wallet):
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-02 11:00:00",
                "account": "Spot",
                "operation": "Deposit",
                "coin": "USDT",
                "change": "29.90000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        assert stats.errors == 0

        result = await session.execute(
            select(JournalEntry).where(JournalEntry.entity_id == entity.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 1
        assert entries[0].entry_type == "DEPOSIT"

        # 2 splits: cex_asset +29.9, external_transfer -29.9
        result = await session.execute(
            select(JournalSplit).where(JournalSplit.journal_entry_id == entries[0].id)
        )
        splits = list(result.scalars().all())
        assert len(splits) == 2

        quantities = sorted([s.quantity for s in splits])
        # SQLite Numeric can lose precision, so compare with tolerance
        assert abs(quantities[0] - Decimal("-29.9")) < Decimal("0.001")
        assert abs(quantities[1] - Decimal("29.9")) < Decimal("0.001")


# ---------------------------------------------------------------------------
# Test: Withdraw
# ---------------------------------------------------------------------------


class TestWithdraw:
    async def test_withdraw_produces_balanced_entry(self, session, entity, cex_wallet):
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-02 12:00:00",
                "account": "Spot",
                "operation": "Withdraw",
                "coin": "ETH",
                "change": "-0.00146957",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        assert stats.errors == 0

        result = await session.execute(
            select(JournalEntry).where(JournalEntry.entity_id == entity.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 1
        assert entries[0].entry_type == "WITHDRAWAL"

        # 2 splits: cex_asset -0.00146957, external_transfer +0.00146957
        result = await session.execute(
            select(JournalSplit).where(JournalSplit.journal_entry_id == entries[0].id)
        )
        splits = list(result.scalars().all())
        assert len(splits) == 2

        quantities = sorted([s.quantity for s in splits])
        assert abs(quantities[0] - Decimal("-0.00146957")) < Decimal("0.00001")
        assert abs(quantities[1] - Decimal("0.00146957")) < Decimal("0.00001")


# ---------------------------------------------------------------------------
# Test: P2P Trading
# ---------------------------------------------------------------------------


class TestP2P:
    async def test_p2p_produces_deposit_entry(self, session, entity, cex_wallet):
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-02 13:00:00",
                "account": "Funding",
                "operation": "P2P Trading",
                "coin": "USDT",
                "change": "7.18000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        assert stats.errors == 0

        result = await session.execute(
            select(JournalEntry).where(JournalEntry.entity_id == entity.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 1
        assert entries[0].entry_type == "DEPOSIT"


# ---------------------------------------------------------------------------
# Test: Internal Transfer
# ---------------------------------------------------------------------------


class TestInternalTransfer:
    async def test_internal_transfer_sums_to_zero(self, session, entity, cex_wallet):
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-02 14:00:00",
                "account": "Spot",
                "operation": "Transfer Between Main and Funding Wallet",
                "coin": "USDT",
                "change": "-6.93476480",
            },
            {
                "utc_time": "2025-12-02 14:00:00",
                "account": "Funding",
                "operation": "Transfer Between Main and Funding Wallet",
                "coin": "USDT",
                "change": "6.93476480",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 2
        assert stats.errors == 0

        result = await session.execute(
            select(JournalEntry).where(JournalEntry.entity_id == entity.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 1
        assert entries[0].entry_type == "TRANSFER"

        # 2 splits that sum to zero
        result = await session.execute(
            select(JournalSplit).where(JournalSplit.journal_entry_id == entries[0].id)
        )
        splits = list(result.scalars().all())
        assert len(splits) == 2

        total = sum(s.quantity for s in splits)
        assert total == Decimal("0")


# ---------------------------------------------------------------------------
# Test: Mixed timestamp groups
# ---------------------------------------------------------------------------


class TestMixedTimestamp:
    async def test_mixed_timestamp_creates_multiple_entries(self, session, entity, cex_wallet):
        """A buy + internal transfer at the same timestamp produce 2 entries."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            # Spot buy
            {
                "utc_time": "2025-12-02 08:45:30",
                "account": "Spot",
                "operation": "Transaction Buy",
                "coin": "BTC",
                "change": "0.001",
            },
            {
                "utc_time": "2025-12-02 08:45:30",
                "account": "Spot",
                "operation": "Transaction Spend",
                "coin": "USDT",
                "change": "-35.50",
            },
            {
                "utc_time": "2025-12-02 08:45:30",
                "account": "Spot",
                "operation": "Transaction Fee",
                "coin": "BTC",
                "change": "-0.0000075",
            },
            # Internal transfer at same time
            {
                "utc_time": "2025-12-02 08:45:30",
                "account": "Spot",
                "operation": "Transfer Between Main and Funding Wallet",
                "coin": "USDT",
                "change": "-2.00",
            },
            {
                "utc_time": "2025-12-02 08:45:30",
                "account": "Funding",
                "operation": "Transfer Between Main and Funding Wallet",
                "coin": "USDT",
                "change": "2.00",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 5
        assert stats.errors == 0

        result = await session.execute(
            select(JournalEntry).where(JournalEntry.entity_id == entity.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 2

        entry_types = sorted([e.entry_type for e in entries])
        assert entry_types == ["SWAP", "TRANSFER"]


# ---------------------------------------------------------------------------
# Test: Unknown operation
# ---------------------------------------------------------------------------


class TestUnknownOperation:
    async def test_unknown_operation_marked_skipped(self, session, entity, cex_wallet):
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-02 15:00:00",
                "account": "Spot",
                "operation": "Some Future Operation",
                "coin": "BTC",
                "change": "0.001",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.skipped == 1
        assert stats.parsed == 0
        assert stats.errors == 0

        # Row should have skipped status and a message
        await session.refresh(csv_import.rows[0])
        assert csv_import.rows[0].status == "skipped"
        assert "not handled" in csv_import.rows[0].error_message


# ---------------------------------------------------------------------------
# Test: Error recording on bad data
# ---------------------------------------------------------------------------


class TestErrorRecording:
    async def test_error_row_records_message(self, session, entity, cex_wallet):
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-02 16:00:00",
                "account": "Spot",
                "operation": "Deposit",
                "coin": "ETH",
                "change": "not-a-number",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.errors == 1
        assert stats.parsed == 0

        await session.refresh(csv_import.rows[0])
        assert csv_import.rows[0].status == "error"
        assert csv_import.rows[0].error_message is not None


# ---------------------------------------------------------------------------
# Test: Parse API endpoint
# ---------------------------------------------------------------------------

VALID_CSV = (
    '"User_ID","UTC_Time","Account","Operation","Coin","Change","Remark"\n'
    '"123456","2025-12-02 08:41:54","Spot","Transaction Buy","BTC","0.001",""\n'
    '"123456","2025-12-02 08:41:54","Spot","Transaction Spend","USDT","-35.50",""\n'
    '"123456","2025-12-02 08:41:54","Spot","Transaction Fee","BTC","-0.0000075",""\n'
)


@pytest.fixture()
async def client(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestParseEndpoint:
    async def test_parse_api_endpoint(self, client):
        """POST /api/imports/{id}/parse returns parse stats."""
        # Create entity
        res = await client.post("/api/entities", json={"name": "APITestEntity"})
        assert res.status_code == 201
        entity_id = res.json()["id"]

        # Upload CSV
        upload_res = await client.post(
            "/api/imports/upload",
            data={"entity_id": entity_id, "exchange": "binance"},
            files={"file": ("test.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")},
        )
        assert upload_res.status_code == 200
        import_id = upload_res.json()["import_id"]

        # Parse
        parse_res = await client.post(f"/api/imports/{import_id}/parse")
        assert parse_res.status_code == 200
        data = parse_res.json()
        assert data["total"] == 3
        assert data["parsed"] == 3
        assert data["errors"] == 0
        assert data["skipped"] == 0
        assert data["import_id"] == import_id

    async def test_parse_not_found(self, client):
        res = await client.post(f"/api/imports/{uuid.uuid4()}/parse")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Test: CEX wallet auto-creation
# ---------------------------------------------------------------------------


class TestCexWalletAutoCreation:
    async def test_cex_wallet_auto_created(self, client):
        """Parsing creates a CEXWallet if one doesn't exist for entity+exchange."""
        res = await client.post("/api/entities", json={"name": "WalletTestEntity"})
        assert res.status_code == 201
        entity_id = res.json()["id"]

        # Upload CSV
        upload_res = await client.post(
            "/api/imports/upload",
            data={"entity_id": entity_id, "exchange": "binance"},
            files={"file": ("test.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")},
        )
        import_id = upload_res.json()["import_id"]

        # Parse -- should auto-create wallet
        parse_res = await client.post(f"/api/imports/{import_id}/parse")
        assert parse_res.status_code == 200

        # Verify wallet exists via wallets API
        wallets_res = await client.get(f"/api/wallets?entity_id={entity_id}")
        assert wallets_res.status_code == 200
        wallets = wallets_res.json()["wallets"]
        # Check that at least one wallet was created
        cex_wallets = [w for w in wallets if w.get("wallet_type") == "cex"]
        assert len(cex_wallets) >= 1
        assert cex_wallets[0]["exchange"] == "binance"

    async def test_cex_wallet_reused_on_second_parse(self, client):
        """A second parse reuses the existing CEXWallet."""
        res = await client.post("/api/entities", json={"name": "ReuseWalletEntity"})
        assert res.status_code == 201
        entity_id = res.json()["id"]

        # Upload + parse first CSV
        upload1 = await client.post(
            "/api/imports/upload",
            data={"entity_id": entity_id, "exchange": "binance"},
            files={"file": ("first.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")},
        )
        await client.post(f"/api/imports/{upload1.json()['import_id']}/parse")

        # Upload + parse second CSV
        upload2 = await client.post(
            "/api/imports/upload",
            data={"entity_id": entity_id, "exchange": "binance"},
            files={"file": ("second.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")},
        )
        await client.post(f"/api/imports/{upload2.json()['import_id']}/parse")

        # Should still be only 1 CEX wallet
        wallets_res = await client.get(f"/api/wallets?entity_id={entity_id}")
        cex_wallets = [w for w in wallets_res.json()["wallets"] if w.get("wallet_type") == "cex"]
        assert len(cex_wallets) == 1
