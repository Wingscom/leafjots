"""EVM Transaction Loader — fetches TXs from Etherscan and stores them."""

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.transaction import Transaction
from cryptotax.db.models.wallet import OnChainWallet
from cryptotax.db.repos.transaction_repo import TransactionRepo
from cryptotax.domain.enums import TxStatus, WalletSyncStatus
from cryptotax.infra.blockchain.base import ChainTxLoader
from cryptotax.infra.blockchain.evm.etherscan_client import EtherscanClient

logger = logging.getLogger(__name__)

# Stay 50 blocks behind chain tip to avoid reorgs
REORG_SAFETY_MARGIN = 50

# PostgreSQL BIGINT max — ETH values above this (~9.2 ETH in wei) are stored as NULL
_BIGINT_MAX = 9_223_372_036_854_775_807


def _safe_wei(raw_value) -> int | None:
    """Parse wei value, returning None if zero or exceeds BIGINT range."""
    v = int(raw_value or 0)
    if v == 0 or v > _BIGINT_MAX:
        return None
    return v


class EVMTxLoader(ChainTxLoader):
    def __init__(self, session: AsyncSession, etherscan: EtherscanClient) -> None:
        self._session = session
        self._repo = TransactionRepo(session)
        self._etherscan = etherscan

    async def load_wallet(self, wallet: OnChainWallet) -> int:
        """Load new transactions for a wallet. Returns count of new TXs inserted."""
        wallet.sync_status = WalletSyncStatus.SYNCING.value
        await self._session.flush()

        try:
            count = await self._do_load(wallet)
            wallet.sync_status = WalletSyncStatus.SYNCED.value
            wallet.last_synced_at = datetime.now(UTC)
            await self._session.flush()
            logger.info("Loaded %d new TXs for wallet %s on %s", count, wallet.address, wallet.chain)
            return count
        except Exception:
            wallet.sync_status = WalletSyncStatus.ERROR.value
            await self._session.flush()
            logger.exception("Failed to load TXs for wallet %s on %s", wallet.address, wallet.chain)
            raise

    async def _do_load(self, wallet: OnChainWallet) -> int:
        assert wallet.address is not None
        assert wallet.chain is not None

        # Determine block range
        from_block = (wallet.last_block_loaded or 0)
        tip = await self._etherscan.get_latest_block()
        to_block = max(tip - REORG_SAFETY_MARGIN, from_block)

        if from_block >= to_block:
            logger.info("No new blocks for wallet %s (from=%d, tip=%d)", wallet.address, from_block, tip)
            return 0

        # Fetch from Etherscan
        raw_txs = await self._etherscan.get_transactions(wallet.address, from_block, to_block)

        if not raw_txs:
            wallet.last_block_loaded = to_block
            return 0

        # Dedup against existing
        existing_hashes = await self._repo.get_existing_hashes(wallet.id)
        new_txs = [tx for tx in raw_txs if tx.get("hash") not in existing_hashes]

        if not new_txs:
            wallet.last_block_loaded = to_block
            return 0

        # Fetch ERC20 token transfers for the same block range
        token_txs = await self._etherscan.get_erc20_transfers(wallet.address, from_block, to_block)
        token_by_hash: dict[str, list[dict]] = defaultdict(list)
        for ttx in token_txs:
            token_by_hash[ttx.get("hash", "").lower()].append(ttx)

        # Fetch internal transactions (needed for Gnosis Safe multisig, contract interactions)
        internal_txs = await self._etherscan.get_internal_transactions(wallet.address, from_block, to_block)
        internal_by_hash: dict[str, list[dict]] = defaultdict(list)
        for itx in internal_txs:
            internal_by_hash[itx.get("hash", "").lower()].append(itx)

        # Build Transaction objects (enriched with token_transfers)
        tx_objects = []
        max_block = from_block
        for raw in new_txs:
            block_num = int(raw.get("blockNumber", 0))
            max_block = max(max_block, block_num)
            tx_hash = raw["hash"]
            raw["token_transfers"] = token_by_hash.get(tx_hash.lower(), [])
            raw["internal_transfers"] = internal_by_hash.get(tx_hash.lower(), [])
            tx_objects.append(Transaction(
                wallet_id=wallet.id,
                chain=wallet.chain,
                tx_hash=tx_hash,
                block_number=block_num,
                timestamp=int(raw.get("timeStamp", 0)) or None,
                from_addr=raw.get("from", "").lower() or None,
                to_addr=raw.get("to", "").lower() or None,
                value_wei=_safe_wei(raw.get("value", 0)),
                gas_used=int(raw.get("gasUsed", 0)) or None,
                status=TxStatus.LOADED.value,
                tx_data=json.dumps(raw),
            ))

        await self._repo.bulk_insert(tx_objects)
        wallet.last_block_loaded = to_block

        return len(tx_objects)
