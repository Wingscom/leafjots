"""Tests for BinanceLoader — CEX transaction loading and storage."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.entity import Entity
from cryptotax.db.models.wallet import CEXWallet
from cryptotax.domain.enums import WalletSyncStatus
from cryptotax.infra.cex.binance_client import BinanceClient
from cryptotax.infra.cex.binance_loader import BinanceLoader


@pytest.fixture()
async def cex_wallet(session: AsyncSession):
    entity = Entity(name="cex_test")
    session.add(entity)
    await session.flush()

    wallet = CEXWallet(
        entity_id=entity.id,
        exchange="binance",
        api_key_encrypted="enc_key",
        api_secret_encrypted="enc_secret",
        label="Test Binance",
    )
    session.add(wallet)
    await session.flush()
    return wallet


class TestBinanceLoader:
    async def test_load_empty(self, session, cex_wallet):
        client = AsyncMock(spec=BinanceClient)
        client.get_all_spot_trades.return_value = []
        client.get_deposits.return_value = []
        client.get_withdrawals.return_value = []

        loader = BinanceLoader(session, client)
        count = await loader.load_wallet(cex_wallet)

        assert count == 0
        assert cex_wallet.sync_status == WalletSyncStatus.SYNCED.value

    async def test_load_with_trades(self, session, cex_wallet):
        client = AsyncMock(spec=BinanceClient)
        client.get_all_spot_trades.return_value = [
            {"id": 12345, "symbol": "BTCUSDT", "qty": "0.5", "quoteQty": "15000", "isBuyer": True, "time": 1700000000000},
        ]
        client.get_deposits.return_value = []
        client.get_withdrawals.return_value = []

        loader = BinanceLoader(session, client)
        count = await loader.load_wallet(cex_wallet)

        assert count == 1
        assert cex_wallet.sync_status == WalletSyncStatus.SYNCED.value

    async def test_load_with_deposits_and_withdrawals(self, session, cex_wallet):
        client = AsyncMock(spec=BinanceClient)
        client.get_all_spot_trades.return_value = []
        client.get_deposits.return_value = [
            {"txId": "dep1", "coin": "ETH", "amount": "1.0", "insertTime": 1700000000000},
        ]
        client.get_withdrawals.return_value = [
            {"id": "wd1", "coin": "BTC", "amount": "0.1", "transactionFee": "0.0005", "applyTime": "2024-01-01T00:00:00Z"},
        ]

        loader = BinanceLoader(session, client)
        count = await loader.load_wallet(cex_wallet)

        assert count == 2  # 1 deposit + 1 withdrawal

    async def test_dedup_existing(self, session, cex_wallet):
        client = AsyncMock(spec=BinanceClient)
        trade = {"id": 999, "symbol": "ETHUSDT", "qty": "1", "quoteQty": "2000", "isBuyer": False, "time": 1700000000000}
        client.get_all_spot_trades.return_value = [trade]
        client.get_deposits.return_value = []
        client.get_withdrawals.return_value = []

        loader = BinanceLoader(session, client)

        # First load
        count1 = await loader.load_wallet(cex_wallet)
        assert count1 == 1

        # Reset sync
        cex_wallet.sync_status = WalletSyncStatus.IDLE.value
        await session.flush()

        # Second load — same trade should be deduped
        count2 = await loader.load_wallet(cex_wallet)
        assert count2 == 0

    async def test_error_sets_status(self, session, cex_wallet):
        client = AsyncMock(spec=BinanceClient)
        client.get_all_spot_trades.side_effect = Exception("API down")

        loader = BinanceLoader(session, client)

        with pytest.raises(Exception, match="API down"):
            await loader.load_wallet(cex_wallet)

        assert cex_wallet.sync_status == WalletSyncStatus.ERROR.value

    async def test_trade_tx_fields(self, session, cex_wallet):
        """Verify Transaction record has correct CEX-specific fields."""
        client = AsyncMock(spec=BinanceClient)
        client.get_all_spot_trades.return_value = [
            {"id": 42, "symbol": "BTCUSDT", "qty": "0.1", "quoteQty": "3000", "isBuyer": True, "time": 1700000000000},
        ]
        client.get_deposits.return_value = []
        client.get_withdrawals.return_value = []

        loader = BinanceLoader(session, client)
        await loader.load_wallet(cex_wallet)

        from sqlalchemy import select
        from cryptotax.db.models.transaction import Transaction
        result = await session.execute(select(Transaction).where(Transaction.tx_hash == "binance_trade_42"))
        tx = result.scalar_one()

        assert tx.chain == "binance"
        assert tx.tx_hash == "binance_trade_42"
        assert tx.from_addr == "binance"
        assert tx.timestamp == 1700000000
