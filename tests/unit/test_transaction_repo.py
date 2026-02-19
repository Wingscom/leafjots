import uuid

from cryptotax.db.models.entity import Entity
from cryptotax.db.models.transaction import Transaction
from cryptotax.db.models.wallet import OnChainWallet
from cryptotax.db.repos.transaction_repo import TransactionRepo
from cryptotax.domain.enums import TxStatus


async def _create_wallet(session) -> OnChainWallet:
    entity = Entity(name="Test", base_currency="VND")
    session.add(entity)
    await session.flush()
    wallet = OnChainWallet(
        entity_id=entity.id, chain="ethereum", address="0xabc", label="test",
    )
    session.add(wallet)
    await session.flush()
    return wallet


def _make_tx(wallet_id: uuid.UUID, tx_hash: str, block: int = 100) -> Transaction:
    return Transaction(
        wallet_id=wallet_id,
        chain="ethereum",
        tx_hash=tx_hash,
        block_number=block,
        timestamp=1700000000,
        from_addr="0xaaa",
        to_addr="0xbbb",
        value_wei=1000000000000000000,
        gas_used=21000,
        status=TxStatus.LOADED.value,
    )


class TestTransactionRepo:
    async def test_bulk_insert(self, session):
        wallet = await _create_wallet(session)
        repo = TransactionRepo(session)

        txs = [_make_tx(wallet.id, f"0x{i:064x}", block=100 + i) for i in range(5)]
        await repo.bulk_insert(txs)

        all_txs, total = await repo.list_for_wallet(wallet.id)
        assert total == 5
        assert len(all_txs) == 5

    async def test_get_existing_hashes(self, session):
        wallet = await _create_wallet(session)
        repo = TransactionRepo(session)

        txs = [_make_tx(wallet.id, f"0xhash{i}") for i in range(3)]
        await repo.bulk_insert(txs)

        hashes = await repo.get_existing_hashes(wallet.id)
        assert hashes == {"0xhash0", "0xhash1", "0xhash2"}

    async def test_get_by_hash(self, session):
        wallet = await _create_wallet(session)
        repo = TransactionRepo(session)

        tx = _make_tx(wallet.id, "0xunique")
        await repo.bulk_insert([tx])

        found = await repo.get_by_hash("0xunique")
        assert found is not None
        assert found.tx_hash == "0xunique"
        assert found.from_addr == "0xaaa"
        assert found.to_addr == "0xbbb"
        assert found.value_wei == 1000000000000000000
        assert found.gas_used == 21000

    async def test_get_by_hash_not_found(self, session):
        repo = TransactionRepo(session)
        found = await repo.get_by_hash("0xnonexistent")
        assert found is None

    async def test_list_for_wallet_pagination(self, session):
        wallet = await _create_wallet(session)
        repo = TransactionRepo(session)

        txs = [_make_tx(wallet.id, f"0xp{i:064x}", block=100 + i) for i in range(10)]
        await repo.bulk_insert(txs)

        page1, total = await repo.list_for_wallet(wallet.id, limit=3, offset=0)
        assert total == 10
        assert len(page1) == 3

        page2, _ = await repo.list_for_wallet(wallet.id, limit=3, offset=3)
        assert len(page2) == 3

        # No overlap
        hashes1 = {tx.tx_hash for tx in page1}
        hashes2 = {tx.tx_hash for tx in page2}
        assert hashes1.isdisjoint(hashes2)

    async def test_list_for_wallet_status_filter(self, session):
        wallet = await _create_wallet(session)
        repo = TransactionRepo(session)

        tx1 = _make_tx(wallet.id, "0xloaded")
        tx2 = _make_tx(wallet.id, "0xparsed")
        tx2.status = TxStatus.PARSED.value
        await repo.bulk_insert([tx1, tx2])

        loaded, total_loaded = await repo.list_for_wallet(wallet.id, status=TxStatus.LOADED.value)
        assert total_loaded == 1
        assert loaded[0].tx_hash == "0xloaded"

        parsed, total_parsed = await repo.list_for_wallet(wallet.id, status=TxStatus.PARSED.value)
        assert total_parsed == 1
        assert parsed[0].tx_hash == "0xparsed"

    async def test_list_for_entity(self, session):
        entity = Entity(name="Multi", base_currency="VND")
        session.add(entity)
        await session.flush()

        w1 = OnChainWallet(entity_id=entity.id, chain="ethereum", address="0x111")
        w2 = OnChainWallet(entity_id=entity.id, chain="arbitrum", address="0x222")
        session.add_all([w1, w2])
        await session.flush()

        repo = TransactionRepo(session)
        txs = [
            _make_tx(w1.id, "0xeth1"),
            _make_tx(w1.id, "0xeth2"),
            _make_tx(w2.id, "0xarb1"),
        ]
        txs[2].chain = "arbitrum"
        await repo.bulk_insert(txs)

        all_txs, total = await repo.list_for_entity(entity.id)
        assert total == 3
        assert len(all_txs) == 3

    async def test_list_for_entity_chain_filter(self, session):
        entity = Entity(name="Filter", base_currency="VND")
        session.add(entity)
        await session.flush()

        w1 = OnChainWallet(entity_id=entity.id, chain="ethereum", address="0x333")
        w2 = OnChainWallet(entity_id=entity.id, chain="arbitrum", address="0x444")
        session.add_all([w1, w2])
        await session.flush()

        repo = TransactionRepo(session)
        txs = [
            _make_tx(w1.id, "0xf_eth"),
            _make_tx(w2.id, "0xf_arb"),
        ]
        txs[1].chain = "arbitrum"
        await repo.bulk_insert(txs)

        eth_txs, eth_total = await repo.list_for_entity(entity.id, chain="ethereum")
        assert eth_total == 1
        assert eth_txs[0].tx_hash == "0xf_eth"

    async def test_list_for_wallet_ordered_by_block_desc(self, session):
        wallet = await _create_wallet(session)
        repo = TransactionRepo(session)

        txs = [
            _make_tx(wallet.id, "0xblock100", block=100),
            _make_tx(wallet.id, "0xblock300", block=300),
            _make_tx(wallet.id, "0xblock200", block=200),
        ]
        await repo.bulk_insert(txs)

        result, _ = await repo.list_for_wallet(wallet.id)
        blocks = [tx.block_number for tx in result]
        assert blocks == [300, 200, 100]
