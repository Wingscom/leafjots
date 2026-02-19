"""BinanceLoader — fetch trades/deposits/withdrawals and store as Transactions."""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.transaction import Transaction
from cryptotax.db.models.wallet import CEXWallet
from cryptotax.db.repos.transaction_repo import TransactionRepo
from cryptotax.domain.enums import TxStatus, WalletSyncStatus
from cryptotax.infra.cex.binance_client import BinanceClient

logger = logging.getLogger(__name__)


class BinanceLoader:
    """Load Binance trades, deposits, and withdrawals into Transaction records."""

    def __init__(self, session: AsyncSession, client: BinanceClient) -> None:
        self._session = session
        self._client = client
        self._tx_repo = TransactionRepo(session)

    async def load_wallet(self, wallet: CEXWallet) -> int:
        """Fetch new data from Binance API and store as Transactions. Returns count."""
        wallet.sync_status = WalletSyncStatus.SYNCING.value
        await self._session.flush()

        try:
            existing_hashes = await self._tx_repo.get_existing_hashes(wallet.id)

            start_time = None
            if wallet.last_synced_at:
                start_time = int(wallet.last_synced_at.timestamp() * 1000)

            trades = await self._client.get_all_spot_trades(start_time=start_time)
            deposits = await self._client.get_deposits(start_time=start_time)
            withdrawals = await self._client.get_withdrawals(start_time=start_time)

            new_txs: list[Transaction] = []

            for trade in trades:
                tx = self._build_trade_tx(wallet, trade)
                if tx.tx_hash not in existing_hashes:
                    new_txs.append(tx)

            for dep in deposits:
                tx = self._build_deposit_tx(wallet, dep)
                if tx.tx_hash not in existing_hashes:
                    new_txs.append(tx)

            for wd in withdrawals:
                tx = self._build_withdrawal_tx(wallet, wd)
                if tx.tx_hash not in existing_hashes:
                    new_txs.append(tx)

            if new_txs:
                await self._tx_repo.bulk_insert(new_txs)

            wallet.sync_status = WalletSyncStatus.SYNCED.value
            wallet.last_synced_at = datetime.now(UTC)
            await self._session.flush()

            logger.info("Binance sync: %d new TXs for wallet %s", len(new_txs), wallet.id)
            return len(new_txs)

        except Exception:
            wallet.sync_status = WalletSyncStatus.ERROR.value
            await self._session.flush()
            raise

    def _build_trade_tx(self, wallet: CEXWallet, trade: dict) -> Transaction:
        trade_id = trade.get("id", trade.get("orderId", "unknown"))
        timestamp = int(trade.get("time", 0)) // 1000  # ms → s
        return Transaction(
            wallet_id=wallet.id,
            chain="binance",
            tx_hash=f"binance_trade_{trade_id}",
            timestamp=timestamp,
            from_addr=wallet.exchange,
            to_addr=wallet.exchange,
            status=TxStatus.LOADED.value,
            tx_data=json.dumps(trade),
        )

    def _build_deposit_tx(self, wallet: CEXWallet, deposit: dict) -> Transaction:
        dep_id = deposit.get("txId", deposit.get("id", "unknown"))
        timestamp = int(deposit.get("insertTime", 0)) // 1000
        return Transaction(
            wallet_id=wallet.id,
            chain="binance",
            tx_hash=f"binance_deposit_{dep_id}",
            timestamp=timestamp,
            from_addr="external",
            to_addr=wallet.exchange,
            status=TxStatus.LOADED.value,
            tx_data=json.dumps(deposit),
        )

    def _build_withdrawal_tx(self, wallet: CEXWallet, withdrawal: dict) -> Transaction:
        wd_id = withdrawal.get("id", "unknown")
        apply_time = withdrawal.get("applyTime", "")
        timestamp = 0
        if apply_time:
            try:
                timestamp = int(datetime.fromisoformat(apply_time.replace("Z", "+00:00")).timestamp())
            except (ValueError, TypeError):
                pass
        return Transaction(
            wallet_id=wallet.id,
            chain="binance",
            tx_hash=f"binance_withdraw_{wd_id}",
            timestamp=timestamp,
            from_addr=wallet.exchange,
            to_addr="external",
            status=TxStatus.LOADED.value,
            tx_data=json.dumps(withdrawal),
        )
