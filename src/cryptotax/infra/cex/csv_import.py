"""BinanceCSVImporter — import Binance trade history from CSV."""

import csv
import io
import json
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.transaction import Transaction
from cryptotax.db.models.wallet import CEXWallet
from cryptotax.db.repos.transaction_repo import TransactionRepo
from cryptotax.domain.enums import TxStatus

logger = logging.getLogger(__name__)


class BinanceCSVImporter:
    """Import Binance trade history CSV into Transaction records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tx_repo = TransactionRepo(session)

    async def import_trades(self, wallet: CEXWallet, csv_content: str) -> int:
        """Parse CSV and insert as Transactions. Returns count of new TXs."""
        existing_hashes = await self._tx_repo.get_existing_hashes(wallet.id)
        new_txs: list[Transaction] = []

        reader = csv.DictReader(io.StringIO(csv_content))
        for idx, row in enumerate(reader):
            tx = self._row_to_transaction(wallet, row, idx)
            if tx is not None and tx.tx_hash not in existing_hashes:
                new_txs.append(tx)

        if new_txs:
            await self._tx_repo.bulk_insert(new_txs)

        logger.info("CSV import: %d new TXs for wallet %s", len(new_txs), wallet.id)
        return len(new_txs)

    def _row_to_transaction(self, wallet: CEXWallet, row: dict, idx: int) -> Transaction | None:
        """Convert a CSV row to a Transaction record."""
        # Binance CSV format: Date(UTC), Pair, Side, Price, Executed, Amount, Fee
        date_str = row.get("Date(UTC)", row.get("Date", "")).strip()
        pair = row.get("Pair", row.get("Market", "")).strip()
        side = row.get("Side", row.get("Type", "")).strip()

        if not date_str or not pair:
            return None

        timestamp = 0
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                timestamp = int(datetime.strptime(date_str, fmt).timestamp())
                break
            except ValueError:
                continue

        tx_hash = f"csv_binance_{date_str}_{pair}_{idx}"

        tx_data = {
            "source": "csv",
            "side": side.upper(),
            "symbol": pair,
            "price": row.get("Price", "0"),
            "qty": row.get("Executed", row.get("Amount", "0")),
            "quoteQty": row.get("Amount", row.get("Total", "0")),
            "commission": row.get("Fee", "0"),
            "commissionAsset": row.get("Fee Coin", row.get("Fee Currency", "")),
        }

        return Transaction(
            wallet_id=wallet.id,
            chain="binance",
            tx_hash=tx_hash,
            timestamp=timestamp,
            from_addr=wallet.exchange,
            to_addr=wallet.exchange,
            status=TxStatus.LOADED.value,
            tx_data=json.dumps(tx_data),
        )
