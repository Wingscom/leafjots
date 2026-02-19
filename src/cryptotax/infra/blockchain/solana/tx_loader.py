"""Solana Transaction Loader — fetches TXs via RPC and stores them."""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.transaction import Transaction
from cryptotax.db.models.wallet import OnChainWallet
from cryptotax.db.repos.transaction_repo import TransactionRepo
from cryptotax.domain.enums import TxStatus, WalletSyncStatus
from cryptotax.infra.blockchain.base import ChainTxLoader
from cryptotax.infra.blockchain.solana.rpc_client import SolanaRPCClient

logger = logging.getLogger(__name__)


class SolanaTxLoader(ChainTxLoader):
    """Loads Solana transactions using signature-based pagination."""

    def __init__(self, session: AsyncSession, rpc: SolanaRPCClient) -> None:
        self._session = session
        self._repo = TransactionRepo(session)
        self._rpc = rpc

    async def load_wallet(self, wallet: OnChainWallet) -> int:
        """Load new transactions for a Solana wallet. Returns count of new TXs inserted."""
        wallet.sync_status = WalletSyncStatus.SYNCING.value
        await self._session.flush()

        try:
            count = await self._do_load(wallet)
            wallet.sync_status = WalletSyncStatus.SYNCED.value
            wallet.last_synced_at = datetime.now(UTC)
            await self._session.flush()
            logger.info("Loaded %d new TXs for Solana wallet %s", count, wallet.address)
            return count
        except Exception:
            wallet.sync_status = WalletSyncStatus.ERROR.value
            await self._session.flush()
            logger.exception("Failed to load TXs for Solana wallet %s", wallet.address)
            raise

    async def _do_load(self, wallet: OnChainWallet) -> int:
        assert wallet.address is not None

        # Get existing hashes for dedup
        existing_hashes = await self._repo.get_existing_hashes(wallet.id)

        # Fetch signatures (newest-first) using cursor pagination
        all_sigs = await self._fetch_all_signatures(wallet.address, existing_hashes)

        if not all_sigs:
            # Update slot even if no new TXs
            current_slot = await self._rpc.get_slot()
            wallet.last_block_loaded = current_slot
            return 0

        # Process in chronological order (oldest first)
        all_sigs.reverse()

        tx_objects = []
        max_slot = wallet.last_block_loaded or 0

        for sig_info in all_sigs:
            signature = sig_info["signature"]
            slot = sig_info.get("slot", 0)
            max_slot = max(max_slot, slot)

            # Skip failed transactions
            if sig_info.get("err") is not None:
                continue

            # Fetch full transaction data
            tx_data = await self._rpc.get_transaction(signature)
            if tx_data is None:
                continue

            tx_obj = self._build_transaction(wallet, signature, slot, sig_info, tx_data)
            tx_objects.append(tx_obj)

        if tx_objects:
            await self._repo.bulk_insert(tx_objects)

        wallet.last_block_loaded = max_slot
        return len(tx_objects)

    async def _fetch_all_signatures(
        self, address: str, existing_hashes: set[str]
    ) -> list[dict]:
        """Fetch signatures until we hit an existing one or run out."""
        all_sigs: list[dict] = []
        before: str | None = None

        while True:
            batch = await self._rpc.get_signatures(address, before=before, limit=1000)
            if not batch:
                break

            new_sigs = []
            hit_existing = False
            for sig_info in batch:
                if sig_info["signature"] in existing_hashes:
                    hit_existing = True
                    break
                new_sigs.append(sig_info)

            all_sigs.extend(new_sigs)

            if hit_existing or len(batch) < 1000:
                break

            # Use last signature as cursor for next page
            before = batch[-1]["signature"]

        return all_sigs

    def _build_transaction(
        self,
        wallet: OnChainWallet,
        signature: str,
        slot: int,
        sig_info: dict,
        tx_data: dict,
    ) -> Transaction:
        """Build a Transaction record from Solana RPC data."""
        block_time = sig_info.get("blockTime") or tx_data.get("blockTime")
        meta = tx_data.get("meta", {}) or {}
        transaction = tx_data.get("transaction", {}) or {}
        message = transaction.get("message", {}) or {}
        account_keys = message.get("accountKeys", [])

        # First signer is the fee payer
        from_addr = None
        if account_keys:
            first_key = account_keys[0]
            if isinstance(first_key, dict):
                from_addr = first_key.get("pubkey")
            else:
                from_addr = str(first_key)

        # to_addr: first non-signer or first program invoked
        to_addr = None
        if len(account_keys) > 1:
            second_key = account_keys[1]
            if isinstance(second_key, dict):
                to_addr = second_key.get("pubkey")
            else:
                to_addr = str(second_key)

        # Native SOL value transferred (sum of balance changes for wallet)
        value_lamports = 0
        pre_balances = meta.get("preBalances", [])
        post_balances = meta.get("postBalances", [])
        if pre_balances and post_balances and account_keys:
            for i, key in enumerate(account_keys):
                pubkey = key.get("pubkey") if isinstance(key, dict) else str(key)
                if pubkey == wallet.address and i < len(pre_balances) and i < len(post_balances):
                    value_lamports = abs(post_balances[i] - pre_balances[i])
                    break

        gas_used = meta.get("fee", 0)

        return Transaction(
            wallet_id=wallet.id,
            chain="solana",
            tx_hash=signature,
            block_number=slot,
            timestamp=block_time,
            from_addr=from_addr,
            to_addr=to_addr,
            value_wei=value_lamports or None,
            gas_used=gas_used or None,
            status=TxStatus.LOADED.value,
            tx_data=json.dumps(tx_data),
        )
