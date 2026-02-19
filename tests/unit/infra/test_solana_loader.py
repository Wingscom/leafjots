"""Tests for SolanaTxLoader — Solana transaction loading and storage."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.entity import Entity
from cryptotax.db.models.wallet import OnChainWallet
from cryptotax.domain.enums import WalletSyncStatus
from cryptotax.infra.blockchain.solana.rpc_client import SolanaRPCClient
from cryptotax.infra.blockchain.solana.tx_loader import SolanaTxLoader


def _make_sig_info(sig: str, slot: int = 100, err=None):
    return {"signature": sig, "slot": slot, "blockTime": 1700000000, "err": err}


def _make_tx_data(fee: int = 5000, pre_bal=None, post_bal=None):
    if pre_bal is None:
        pre_bal = [1000000000, 500000000]
    if post_bal is None:
        post_bal = [994995000, 500005000]
    return {
        "transaction": {
            "message": {
                "accountKeys": [
                    {"pubkey": "SenderAddress11111111111111111111111111111111", "signer": True},
                    {"pubkey": "ReceiverAddr2222222222222222222222222222222222", "signer": False},
                ],
            },
        },
        "meta": {
            "fee": fee,
            "preBalances": pre_bal,
            "postBalances": post_bal,
            "preTokenBalances": [],
            "postTokenBalances": [],
        },
        "blockTime": 1700000000,
    }


@pytest.fixture()
async def solana_wallet(session: AsyncSession):
    entity = Entity(name="sol_test")
    session.add(entity)
    await session.flush()

    wallet = OnChainWallet(
        entity_id=entity.id,
        chain="solana",
        address="SenderAddress11111111111111111111111111111111",
    )
    session.add(wallet)
    await session.flush()
    return wallet


class TestSolanaTxLoader:
    async def test_load_empty_wallet(self, session, solana_wallet):
        rpc = AsyncMock(spec=SolanaRPCClient)
        rpc.get_signatures.return_value = []
        rpc.get_slot.return_value = 200000

        loader = SolanaTxLoader(session, rpc)
        count = await loader.load_wallet(solana_wallet)

        assert count == 0
        assert solana_wallet.sync_status == WalletSyncStatus.SYNCED.value
        assert solana_wallet.last_block_loaded == 200000

    async def test_load_with_transactions(self, session, solana_wallet):
        rpc = AsyncMock(spec=SolanaRPCClient)
        rpc.get_signatures.return_value = [
            _make_sig_info("3Fmbs8RuNkJLxe4V6xjKEYGqABqFnWrgWs1TmDYqyfMATz5Nqx2w", slot=150),
        ]
        rpc.get_transaction.return_value = _make_tx_data(fee=5000)

        loader = SolanaTxLoader(session, rpc)
        count = await loader.load_wallet(solana_wallet)

        assert count == 1
        assert solana_wallet.sync_status == WalletSyncStatus.SYNCED.value
        assert solana_wallet.last_block_loaded == 150

    async def test_skips_failed_transactions(self, session, solana_wallet):
        rpc = AsyncMock(spec=SolanaRPCClient)
        rpc.get_signatures.return_value = [
            _make_sig_info("failedSig", slot=100, err={"InstructionError": [0, "Custom"]}),
        ]

        loader = SolanaTxLoader(session, rpc)
        count = await loader.load_wallet(solana_wallet)

        assert count == 0  # Failed TX skipped

    async def test_dedup_existing(self, session, solana_wallet):
        rpc = AsyncMock(spec=SolanaRPCClient)
        sig = "3Fmbs8RuNkJLxe4V6xjKEYGqABqFnWrgWs1TmDYqyfMATz5Nqx2w"
        rpc.get_signatures.return_value = [_make_sig_info(sig, slot=150)]
        rpc.get_transaction.return_value = _make_tx_data()
        rpc.get_slot.return_value = 200

        loader = SolanaTxLoader(session, rpc)

        # First load
        count1 = await loader.load_wallet(solana_wallet)
        assert count1 == 1

        # Reset sync status for second load
        solana_wallet.sync_status = WalletSyncStatus.IDLE.value
        await session.flush()

        # Second load — same sig should be deduped (hits existing, returns empty)
        rpc.get_signatures.return_value = [_make_sig_info(sig, slot=150)]
        count2 = await loader.load_wallet(solana_wallet)
        assert count2 == 0

    async def test_sets_error_status_on_failure(self, session, solana_wallet):
        rpc = AsyncMock(spec=SolanaRPCClient)
        rpc.get_signatures.side_effect = Exception("RPC down")

        loader = SolanaTxLoader(session, rpc)

        with pytest.raises(Exception, match="RPC down"):
            await loader.load_wallet(solana_wallet)

        assert solana_wallet.sync_status == WalletSyncStatus.ERROR.value

    async def test_transaction_fields(self, session, solana_wallet):
        """Verify Transaction record has correct Solana-specific fields."""
        rpc = AsyncMock(spec=SolanaRPCClient)
        sig = "5wHu1qwD7q3jMfE2nXvRH3XZ6kP9sYqc8JzG4F7VaL2nbXjY6m"
        rpc.get_signatures.return_value = [_make_sig_info(sig, slot=300)]
        rpc.get_transaction.return_value = _make_tx_data(fee=5000)

        loader = SolanaTxLoader(session, rpc)
        await loader.load_wallet(solana_wallet)

        from sqlalchemy import select
        from cryptotax.db.models.transaction import Transaction
        result = await session.execute(select(Transaction).where(Transaction.tx_hash == sig))
        tx = result.scalar_one()

        assert tx.chain == "solana"
        assert tx.tx_hash == sig
        assert tx.block_number == 300
        assert tx.from_addr == "SenderAddress11111111111111111111111111111111"
        assert tx.gas_used == 5000
