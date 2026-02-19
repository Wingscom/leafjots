"""Tests for BinanceCsvParser Phase 10 -- extended operations:
Earn, Futures, Margin, Flexible Loan, Special Tokens, Cashback, Transfer Funds.
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cryptotax.db.models.csv_import import CsvImport
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
        filename="test_extended.csv",
        rows_data=rows_data,
    )


async def _get_entries(session, entity_id):
    result = await session.execute(
        select(JournalEntry).where(JournalEntry.entity_id == entity_id)
    )
    return list(result.scalars().all())


async def _get_splits(session, entry_id):
    result = await session.execute(
        select(JournalSplit).where(JournalSplit.journal_entry_id == entry_id)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Simple Earn tests
# ---------------------------------------------------------------------------


class TestEarnSubscription:
    async def test_earn_subscription_produces_deposit(self, session, entity, cex_wallet):
        """Flexible Subscription -2 USDT -> DEPOSIT with protocol_asset counterpart."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 01:00:00",
                "account": "Spot",
                "operation": "Simple Earn Flexible Subscription",
                "coin": "USDT",
                "change": "-2.00000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        assert stats.errors == 0
        assert stats.skipped == 0

        entries = await _get_entries(session, entity.id)
        assert len(entries) == 1
        assert entries[0].entry_type == "DEPOSIT"

        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestEarnRedemption:
    async def test_earn_redemption_produces_withdrawal(self, session, entity, cex_wallet):
        """Flexible Redemption +2 USDT -> WITHDRAWAL with protocol_asset counterpart."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 02:00:00",
                "account": "Spot",
                "operation": "Simple Earn Flexible Redemption",
                "coin": "USDT",
                "change": "2.00000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        assert stats.errors == 0

        entries = await _get_entries(session, entity.id)
        assert len(entries) == 1
        assert entries[0].entry_type == "WITHDRAWAL"

        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestEarnInterest:
    async def test_earn_interest_produces_income(self, session, entity, cex_wallet):
        """Flexible Interest +0.00027 USDT -> YIELD."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 03:00:00",
                "account": "Spot",
                "operation": "Simple Earn Flexible Interest",
                "coin": "USDT",
                "change": "0.00027397",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        assert stats.errors == 0

        entries = await _get_entries(session, entity.id)
        assert len(entries) == 1
        assert entries[0].entry_type == "YIELD"

        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestEarnLockedRewards:
    async def test_earn_locked_rewards_produces_income(self, session, entity, cex_wallet):
        """Locked Rewards +0.005 FLOW -> YIELD."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 04:00:00",
                "account": "Spot",
                "operation": "Simple Earn Locked Rewards",
                "coin": "FLOW",
                "change": "0.00500000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "YIELD"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


# ---------------------------------------------------------------------------
# Futures tests
# ---------------------------------------------------------------------------


class TestFuturesFee:
    async def test_futures_fee_produces_expense(self, session, entity, cex_wallet):
        """Fee -0.01 USDT -> GAS_FEE expense."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 05:00:00",
                "account": "USD\u24c2-Futures",
                "operation": "Fee",
                "coin": "USDT",
                "change": "-0.01000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "GAS_FEE"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestFundingFeeNegative:
    async def test_funding_fee_negative_produces_expense(self, session, entity, cex_wallet):
        """Funding Fee -0.001 USDT -> GAS_FEE expense."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 06:00:00",
                "account": "USD\u24c2-Futures",
                "operation": "Funding Fee",
                "coin": "USDT",
                "change": "-0.00100000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "GAS_FEE"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestFundingFeePositive:
    async def test_funding_fee_positive_produces_income(self, session, entity, cex_wallet):
        """Funding Fee +0.0007 USDT -> YIELD income."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 07:00:00",
                "account": "USD\u24c2-Futures",
                "operation": "Funding Fee",
                "coin": "USDT",
                "change": "0.00070000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "YIELD"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestRealizedPnLPositive:
    async def test_realized_pnl_positive_produces_income(self, session, entity, cex_wallet):
        """Realized Profit and Loss +0.83 USDT -> YIELD income."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 08:00:00",
                "account": "USD\u24c2-Futures",
                "operation": "Realized Profit and Loss",
                "coin": "USDT",
                "change": "0.83000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "YIELD"


class TestRealizedPnLNegative:
    async def test_realized_pnl_negative_produces_expense(self, session, entity, cex_wallet):
        """Realized Profit and Loss -1.25 USDT -> GAS_FEE expense."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 09:00:00",
                "account": "USD\u24c2-Futures",
                "operation": "Realized Profit and Loss",
                "coin": "USDT",
                "change": "-1.25000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "GAS_FEE"


# ---------------------------------------------------------------------------
# Margin tests
# ---------------------------------------------------------------------------


class TestMarginLoan:
    async def test_margin_loan_produces_borrow(self, session, entity, cex_wallet):
        """Isolated Margin Loan +3 USDT -> BORROW."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 10:00:00",
                "account": "Isolated Margin",
                "operation": "Isolated Margin Loan",
                "coin": "USDT",
                "change": "3.00000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "BORROW"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestForcedRepayment:
    async def test_forced_repayment_produces_repay(self, session, entity, cex_wallet):
        """Isolated Margin Liquidation - Forced Repayment -3 USDT -> REPAY."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 11:00:00",
                "account": "Isolated Margin",
                "operation": "Isolated Margin Liquidation - Forced Repayment",
                "coin": "USDT",
                "change": "-3.00000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "REPAY"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestLiquidationTakeover:
    async def test_liquidation_takeover(self, session, entity, cex_wallet):
        """Cross Margin Liquidation - Small Assets Takeover: 2 rows at same time."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 12:00:00",
                "account": "Cross Margin",
                "operation": "Cross Margin Liquidation - Small Assets Takeover",
                "coin": "WLD",
                "change": "-0.10000000",
            },
            {
                "utc_time": "2025-12-10 12:00:00",
                "account": "Cross Margin",
                "operation": "Cross Margin Liquidation - Small Assets Takeover",
                "coin": "USDT",
                "change": "0.05000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 2
        assert stats.errors == 0

        entries = await _get_entries(session, entity.id)
        # Each row dispatched separately -> 2 entries
        assert len(entries) == 2
        for e in entries:
            assert e.entry_type == "LIQUIDATION"


# ---------------------------------------------------------------------------
# Flexible Loan tests
# ---------------------------------------------------------------------------


class TestFlexibleLoanCollateral:
    async def test_flexible_loan_collateral(self, session, entity, cex_wallet):
        """Flexible Loan - Collateral Transfer -749 ANKR -> DEPOSIT to protocol."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 13:00:00",
                "account": "Spot",
                "operation": "Flexible Loan - Collateral Transfer",
                "coin": "ANKR",
                "change": "-749.00000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "DEPOSIT"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestFlexibleLoanLending:
    async def test_flexible_loan_lending(self, session, entity, cex_wallet):
        """Flexible Loan - Lending +2 USDT -> BORROW."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 14:00:00",
                "account": "Spot",
                "operation": "Flexible Loan - Lending",
                "coin": "USDT",
                "change": "2.00000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "BORROW"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestFlexibleLoanRepayment:
    async def test_flexible_loan_repayment(self, session, entity, cex_wallet):
        """Flexible Loan - Repayment -1.98 USDT -> REPAY."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 15:00:00",
                "account": "Spot",
                "operation": "Flexible Loan - Repayment",
                "coin": "USDT",
                "change": "-1.98000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "REPAY"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


# ---------------------------------------------------------------------------
# Special Token tests
# ---------------------------------------------------------------------------


class TestRWUSDSubscription:
    async def test_rwusd_subscription(self, session, entity, cex_wallet):
        """RWUSD Subscription: 2 rows (RWUSD +1, USDT -1) -> 2 SWAP entries."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 16:00:00",
                "account": "Spot",
                "operation": "RWUSD - Subscription",
                "coin": "RWUSD",
                "change": "1.00000000",
            },
            {
                "utc_time": "2025-12-10 16:00:00",
                "account": "Spot",
                "operation": "RWUSD - Subscription",
                "coin": "USDT",
                "change": "-1.00000000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 2
        assert stats.errors == 0

        entries = await _get_entries(session, entity.id)
        assert len(entries) == 2
        for e in entries:
            assert e.entry_type == "SWAP"


class TestRWUSDDistribution:
    async def test_rwusd_distribution(self, session, entity, cex_wallet):
        """RWUSD Distribution +0.0001 RWUSD -> YIELD income."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 17:00:00",
                "account": "Spot",
                "operation": "RWUSD - Distribution",
                "coin": "RWUSD",
                "change": "0.00010000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "YIELD"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestBFUSDDailyReward:
    async def test_bfusd_daily_reward(self, session, entity, cex_wallet):
        """BFUSD Daily Reward +0.0002 BFUSD -> YIELD income."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 18:00:00",
                "account": "Spot",
                "operation": "BFUSD Daily Reward",
                "coin": "BFUSD",
                "change": "0.00020000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "YIELD"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


class TestWBETHStaking:
    async def test_wbeth_staking(self, session, entity, cex_wallet):
        """WBETH2.0 Staking: 2 rows (ETH -0.00065, WBETH +0.0006) -> 2 SWAP entries."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 19:00:00",
                "account": "Spot",
                "operation": "WBETH2.0 - Staking",
                "coin": "ETH",
                "change": "-0.00065000",
            },
            {
                "utc_time": "2025-12-10 19:00:00",
                "account": "Spot",
                "operation": "WBETH2.0 - Staking",
                "coin": "WBETH",
                "change": "0.00060000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 2
        assert stats.errors == 0

        entries = await _get_entries(session, entity.id)
        assert len(entries) == 2
        for e in entries:
            assert e.entry_type == "SWAP"


# ---------------------------------------------------------------------------
# Cashback test
# ---------------------------------------------------------------------------


class TestCashback:
    async def test_cashback_produces_income(self, session, entity, cex_wallet):
        """Cashback Voucher +0.004 USDT -> YIELD income."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 20:00:00",
                "account": "Spot",
                "operation": "Cashback Voucher",
                "coin": "USDT",
                "change": "0.00400000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 1
        entries = await _get_entries(session, entity.id)
        assert entries[0].entry_type == "YIELD"
        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2


# ---------------------------------------------------------------------------
# Transfer Funds test
# ---------------------------------------------------------------------------


class TestTransferFunds:
    async def test_transfer_funds_pair(self, session, entity, cex_wallet):
        """Transfer Funds to Spot +0.245 USDT, Transfer Funds to Funding -0.245 USDT -> TRANSFER."""
        csv_import = await _create_import_with_rows(session, entity.id, [
            {
                "utc_time": "2025-12-10 21:00:00",
                "account": "Spot",
                "operation": "Transfer Funds to Spot",
                "coin": "USDT",
                "change": "0.24500000",
            },
            {
                "utc_time": "2025-12-10 21:00:00",
                "account": "Funding",
                "operation": "Transfer Funds to Funding Wallet",
                "coin": "USDT",
                "change": "-0.24500000",
            },
        ])

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.parsed == 2
        assert stats.errors == 0

        entries = await _get_entries(session, entity.id)
        assert len(entries) == 1
        assert entries[0].entry_type == "TRANSFER"

        splits = await _get_splits(session, entries[0].id)
        assert len(splits) == 2
        total = sum(s.quantity for s in splits)
        assert total == Decimal("0")


# ---------------------------------------------------------------------------
# Full coverage test
# ---------------------------------------------------------------------------


class TestFullCsvCoverage:
    async def test_full_csv_coverage(self, session, entity, cex_wallet):
        """Parse ALL operation types -- verify zero skipped rows."""
        all_rows = [
            # Core ops (Phase 9)
            {"utc_time": "2025-12-10 00:01:00", "account": "Spot", "operation": "Transaction Buy", "coin": "BTC", "change": "0.001"},
            {"utc_time": "2025-12-10 00:01:00", "account": "Spot", "operation": "Transaction Spend", "coin": "USDT", "change": "-35.50"},
            {"utc_time": "2025-12-10 00:01:00", "account": "Spot", "operation": "Transaction Fee", "coin": "BTC", "change": "-0.000001"},
            {"utc_time": "2025-12-10 00:02:00", "account": "Spot", "operation": "Binance Convert", "coin": "BTC", "change": "-0.0001"},
            {"utc_time": "2025-12-10 00:02:00", "account": "Spot", "operation": "Binance Convert", "coin": "ETH", "change": "0.003"},
            {"utc_time": "2025-12-10 00:03:00", "account": "Spot", "operation": "Deposit", "coin": "USDT", "change": "100"},
            {"utc_time": "2025-12-10 00:04:00", "account": "Spot", "operation": "Withdraw", "coin": "ETH", "change": "-0.05"},
            {"utc_time": "2025-12-10 00:05:00", "account": "Funding", "operation": "P2P Trading", "coin": "USDT", "change": "50"},
            {"utc_time": "2025-12-10 00:06:00", "account": "Spot", "operation": "Transfer Between Main and Funding Wallet", "coin": "USDT", "change": "-10"},
            {"utc_time": "2025-12-10 00:06:00", "account": "Funding", "operation": "Transfer Between Main and Funding Wallet", "coin": "USDT", "change": "10"},
            # Earn (Phase 10)
            {"utc_time": "2025-12-10 00:07:00", "account": "Spot", "operation": "Simple Earn Flexible Subscription", "coin": "USDT", "change": "-2"},
            {"utc_time": "2025-12-10 00:08:00", "account": "Spot", "operation": "Simple Earn Flexible Redemption", "coin": "USDT", "change": "2"},
            {"utc_time": "2025-12-10 00:09:00", "account": "Spot", "operation": "Simple Earn Locked Subscription", "coin": "FLOW", "change": "-10"},
            {"utc_time": "2025-12-10 00:10:00", "account": "Spot", "operation": "Simple Earn Flexible Interest", "coin": "USDT", "change": "0.00027"},
            {"utc_time": "2025-12-10 00:11:00", "account": "Spot", "operation": "Simple Earn Locked Rewards", "coin": "FLOW", "change": "0.005"},
            # Futures (Phase 10)
            {"utc_time": "2025-12-10 00:12:00", "account": "USD\u24c2-Futures", "operation": "Fee", "coin": "USDT", "change": "-0.01"},
            {"utc_time": "2025-12-10 00:13:00", "account": "USD\u24c2-Futures", "operation": "Funding Fee", "coin": "USDT", "change": "-0.001"},
            {"utc_time": "2025-12-10 00:14:00", "account": "USD\u24c2-Futures", "operation": "Funding Fee", "coin": "USDT", "change": "0.0007"},
            {"utc_time": "2025-12-10 00:15:00", "account": "USD\u24c2-Futures", "operation": "Realized Profit and Loss", "coin": "USDT", "change": "0.83"},
            {"utc_time": "2025-12-10 00:16:00", "account": "USD\u24c2-Futures", "operation": "Realized Profit and Loss", "coin": "USDT", "change": "-1.25"},
            # Margin (Phase 10)
            {"utc_time": "2025-12-10 00:17:00", "account": "Isolated Margin", "operation": "Isolated Margin Loan", "coin": "USDT", "change": "3"},
            {"utc_time": "2025-12-10 00:18:00", "account": "Isolated Margin", "operation": "Isolated Margin Liquidation - Forced Repayment", "coin": "USDT", "change": "-3"},
            {"utc_time": "2025-12-10 00:19:00", "account": "Cross Margin", "operation": "Cross Margin Liquidation - Small Assets Takeover", "coin": "WLD", "change": "-0.1"},
            # Loan (Phase 10)
            {"utc_time": "2025-12-10 00:20:00", "account": "Spot", "operation": "Flexible Loan - Collateral Transfer", "coin": "ANKR", "change": "-749"},
            {"utc_time": "2025-12-10 00:21:00", "account": "Spot", "operation": "Flexible Loan - Lending", "coin": "USDT", "change": "2"},
            {"utc_time": "2025-12-10 00:22:00", "account": "Spot", "operation": "Flexible Loan - Repayment", "coin": "USDT", "change": "-1.98"},
            # Special tokens (Phase 10)
            {"utc_time": "2025-12-10 00:23:00", "account": "Spot", "operation": "RWUSD - Subscription", "coin": "RWUSD", "change": "1"},
            {"utc_time": "2025-12-10 00:23:00", "account": "Spot", "operation": "RWUSD - Subscription", "coin": "USDT", "change": "-1"},
            {"utc_time": "2025-12-10 00:24:00", "account": "Spot", "operation": "RWUSD - Distribution", "coin": "RWUSD", "change": "0.0001"},
            {"utc_time": "2025-12-10 00:25:00", "account": "Spot", "operation": "RWUSD - Redemption", "coin": "RWUSD", "change": "-1"},
            {"utc_time": "2025-12-10 00:26:00", "account": "Spot", "operation": "BFUSD Subscription", "coin": "BFUSD", "change": "1"},
            {"utc_time": "2025-12-10 00:27:00", "account": "Spot", "operation": "BFUSD Daily Reward", "coin": "BFUSD", "change": "0.0002"},
            {"utc_time": "2025-12-10 00:28:00", "account": "Spot", "operation": "WBETH2.0 - Staking", "coin": "ETH", "change": "-0.00065"},
            {"utc_time": "2025-12-10 00:28:00", "account": "Spot", "operation": "WBETH2.0 - Staking", "coin": "WBETH", "change": "0.0006"},
            # Other (Phase 10)
            {"utc_time": "2025-12-10 00:29:00", "account": "Spot", "operation": "Cashback Voucher", "coin": "USDT", "change": "0.004"},
            {"utc_time": "2025-12-10 00:30:00", "account": "Spot", "operation": "Transfer Funds to Spot", "coin": "USDT", "change": "0.245"},
            {"utc_time": "2025-12-10 00:30:00", "account": "Funding", "operation": "Transfer Funds to Funding Wallet", "coin": "USDT", "change": "-0.245"},
            # Spot sell (for Transaction Sold/Revenue coverage)
            {"utc_time": "2025-12-10 00:31:00", "account": "Spot", "operation": "Transaction Sold", "coin": "XRP", "change": "-2.9"},
            {"utc_time": "2025-12-10 00:31:00", "account": "Spot", "operation": "Transaction Revenue", "coin": "USDT", "change": "5.42"},
        ]

        csv_import = await _create_import_with_rows(session, entity.id, all_rows)

        parser = BinanceCsvParser(session, entity.id, cex_wallet)
        stats = await parser.parse_import(csv_import)

        assert stats.skipped == 0, f"Skipped rows found: {stats.skipped}"
        assert stats.errors == 0, f"Error rows found: {stats.errors}"
        assert stats.parsed == len(all_rows)
