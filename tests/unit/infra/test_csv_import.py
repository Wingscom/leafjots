"""Tests for BinanceCSVImporter."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.entity import Entity
from cryptotax.db.models.wallet import CEXWallet
from cryptotax.infra.cex.csv_import import BinanceCSVImporter

SAMPLE_CSV = """\
Date(UTC),Pair,Side,Price,Executed,Amount,Fee,Fee Coin
2024-01-15 10:30:00,BTCUSDT,BUY,42000.00,0.5,21000.00,0.001,BTC
2024-01-16 14:00:00,ETHUSDT,SELL,2500.00,2.0,5000.00,5.00,USDT
"""

SAMPLE_CSV_ALT = """\
Date,Market,Type,Price,Amount,Total,Fee,Fee Currency
2024-01-15,BTCUSDT,BUY,42000.00,0.5,21000.00,0.001,BTC
"""


@pytest.fixture()
async def cex_wallet(session: AsyncSession):
    entity = Entity(name="csv_test")
    session.add(entity)
    await session.flush()

    wallet = CEXWallet(
        entity_id=entity.id,
        exchange="binance",
        label="CSV Test",
    )
    session.add(wallet)
    await session.flush()
    return wallet


class TestBinanceCSVImporter:
    async def test_import_standard_csv(self, session, cex_wallet):
        importer = BinanceCSVImporter(session)
        count = await importer.import_trades(cex_wallet, SAMPLE_CSV)
        assert count == 2

    async def test_import_alt_format(self, session, cex_wallet):
        importer = BinanceCSVImporter(session)
        count = await importer.import_trades(cex_wallet, SAMPLE_CSV_ALT)
        assert count == 1

    async def test_dedup_csv(self, session, cex_wallet):
        importer = BinanceCSVImporter(session)

        # First import
        count1 = await importer.import_trades(cex_wallet, SAMPLE_CSV)
        assert count1 == 2

        # Second import — same CSV should be deduped
        count2 = await importer.import_trades(cex_wallet, SAMPLE_CSV)
        assert count2 == 0

    async def test_empty_csv(self, session, cex_wallet):
        importer = BinanceCSVImporter(session)
        count = await importer.import_trades(cex_wallet, "Date(UTC),Pair,Side\n")
        assert count == 0

    async def test_malformed_rows_skipped(self, session, cex_wallet):
        csv_with_bad = """\
Date(UTC),Pair,Side,Price,Executed,Amount,Fee,Fee Coin
,,,,,,
2024-01-15 10:30:00,BTCUSDT,BUY,42000.00,0.5,21000.00,0.001,BTC
"""
        importer = BinanceCSVImporter(session)
        count = await importer.import_trades(cex_wallet, csv_with_bad)
        assert count == 1  # Only the valid row

    async def test_tx_fields(self, session, cex_wallet):
        """Verify Transaction record has correct CSV-specific fields."""
        importer = BinanceCSVImporter(session)
        await importer.import_trades(cex_wallet, SAMPLE_CSV)

        from sqlalchemy import select
        from cryptotax.db.models.transaction import Transaction

        result = await session.execute(
            select(Transaction).where(Transaction.wallet_id == cex_wallet.id)
        )
        txs = list(result.scalars().all())
        assert len(txs) == 2
        assert all(tx.chain == "binance" for tx in txs)
        assert all(tx.tx_hash.startswith("csv_binance_") for tx in txs)
