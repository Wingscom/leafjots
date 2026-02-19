"""Tests for ReportDataCollector — data gathering from DB."""

from datetime import UTC, datetime
from decimal import Decimal

from cryptotax.db.models.account import NativeAsset, ERC20Token
from cryptotax.db.models.entity import Entity
from cryptotax.db.models.journal import JournalEntry, JournalSplit
from cryptotax.db.models.wallet import OnChainWallet
from cryptotax.report.data_collector import ReportDataCollector


async def _setup_data(session):
    """Create entity, wallet, accounts, and journal entries."""
    entity = Entity(name="test_report")
    session.add(entity)
    await session.flush()

    wallet = OnChainWallet(entity_id=entity.id, chain="ethereum", address="0xabc")
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

    # Buy 1 ETH for 2000 USDC
    buy_entry = JournalEntry(
        entity_id=entity.id,
        entry_type="SWAP",
        description="Buy ETH",
        timestamp=datetime(2025, 1, 15, tzinfo=UTC),
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

    # Sell 0.5 ETH for 1500 USDC
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


class TestReportDataCollector:
    async def test_collect_returns_report_data(self, session):
        entity = await _setup_data(session)

        collector = ReportDataCollector(session)
        data = await collector.collect(
            entity.id,
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 12, 31, tzinfo=UTC),
        )

        assert len(data.summary) > 0
        assert any("Entity" in str(row) for row in data.summary)

    async def test_journal_sheet_has_all_splits(self, session):
        entity = await _setup_data(session)

        collector = ReportDataCollector(session)
        data = await collector.collect(
            entity.id,
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 12, 31, tzinfo=UTC),
        )

        # 2 entries × 2 splits each = 4 journal rows
        assert len(data.journal) == 4

    async def test_realized_gains_populated(self, session):
        entity = await _setup_data(session)

        collector = ReportDataCollector(session)
        data = await collector.collect(
            entity.id,
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 12, 31, tzinfo=UTC),
        )

        # Selling 0.5 ETH should produce 1 closed lot
        assert len(data.realized_gains) > 0
        # First closed lot should be ETH
        assert data.realized_gains[0][0] == "ETH"

    async def test_open_lots_populated(self, session):
        entity = await _setup_data(session)

        collector = ReportDataCollector(session)
        data = await collector.collect(
            entity.id,
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 12, 31, tzinfo=UTC),
        )

        # 0.5 ETH remaining
        assert len(data.open_lots) > 0

    async def test_wallets_populated(self, session):
        entity = await _setup_data(session)

        collector = ReportDataCollector(session)
        data = await collector.collect(
            entity.id,
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 12, 31, tzinfo=UTC),
        )

        assert len(data.wallets) == 1
        assert data.wallets[0][0] == "ethereum"

    async def test_balance_sheet_has_entries(self, session):
        entity = await _setup_data(session)

        collector = ReportDataCollector(session)
        data = await collector.collect(
            entity.id,
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 12, 31, tzinfo=UTC),
        )

        assert len(data.balance_sheet_qty) > 0
        assert len(data.balance_sheet_usd) > 0
        assert len(data.balance_sheet_vnd) > 0

    async def test_settings_populated(self, session):
        entity = await _setup_data(session)

        collector = ReportDataCollector(session)
        data = await collector.collect(
            entity.id,
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 12, 31, tzinfo=UTC),
        )

        assert len(data.settings_data) > 0
        setting_keys = [row[0] for row in data.settings_data]
        assert "Entity" in setting_keys
        assert "FIFO Method" in setting_keys


class TestReportDataCollectorEmpty:
    async def test_empty_entity_returns_valid_data(self, session):
        entity = Entity(name="empty_entity")
        session.add(entity)
        await session.flush()
        await session.commit()

        collector = ReportDataCollector(session)
        data = await collector.collect(
            entity.id,
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 12, 31, tzinfo=UTC),
        )

        assert len(data.journal) == 0
        assert len(data.realized_gains) == 0
        assert len(data.open_lots) == 0
        assert len(data.summary) > 0  # Summary always has metadata
