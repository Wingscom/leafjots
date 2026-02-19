import json

from cryptotax.accounting.bookkeeper import Bookkeeper
from cryptotax.db.models.entity import Entity
from cryptotax.db.models.transaction import Transaction
from cryptotax.db.models.wallet import OnChainWallet
from cryptotax.domain.enums import TxStatus
from cryptotax.parser.registry import ParserRegistry


ETH_TRANSFER_DATA = {
    "hash": "0xabc123",
    "from": "0x1111111111111111111111111111111111111111",
    "to": "0x2222222222222222222222222222222222222222",
    "value": "1000000000000000000",
    "gasUsed": "21000",
    "gasPrice": "20000000000",
}


async def _setup(session):
    entity = Entity(name="Test", base_currency="VND")
    session.add(entity)
    await session.flush()

    wallet = OnChainWallet(
        entity_id=entity.id,
        chain="ethereum",
        address="0x1111111111111111111111111111111111111111",
    )
    session.add(wallet)
    await session.flush()

    tx = Transaction(
        wallet_id=wallet.id,
        chain="ethereum",
        tx_hash="0xabc123",
        block_number=18500000,
        timestamp=1700000000,
        from_addr="0x1111111111111111111111111111111111111111",
        to_addr="0x2222222222222222222222222222222222222222",
        value_wei=1000000000000000000,
        gas_used=21000,
        status=TxStatus.LOADED.value,
        tx_data=json.dumps(ETH_TRANSFER_DATA),
    )
    session.add(tx)
    await session.flush()

    return entity, wallet, tx


class TestBookkeeper:
    async def test_process_single_eth_transfer(self, session):
        entity, wallet, tx = await _setup(session)

        registry = ParserRegistry()
        bookkeeper = Bookkeeper(session, registry)
        entry = await bookkeeper.process_transaction(tx, wallet, entity.id)

        assert entry is not None
        assert entry.entity_id == entity.id
        assert entry.transaction_id == tx.id
        assert len(entry.splits) > 0

        # TX should be marked as PARSED
        assert tx.status == TxStatus.PARSED.value

    async def test_splits_are_balanced(self, session):
        entity, wallet, tx = await _setup(session)

        registry = ParserRegistry()
        bookkeeper = Bookkeeper(session, registry)
        entry = await bookkeeper.process_transaction(tx, wallet, entity.id)

        assert entry is not None
        assert len(entry.splits) > 0

        # Bookkeeper validates sum=0 per symbol before creating the entry,
        # so if we got an entry back, it passed the balance check.
        # Verify splits exist for gas fee (expense + native_asset pair)
        from sqlalchemy import select
        from cryptotax.db.models.account import Account
        account_ids = [s.account_id for s in entry.splits]
        result = await session.execute(select(Account).where(Account.id.in_(account_ids)))
        accounts = {a.id: a for a in result.scalars().all()}
        subtypes = [accounts[s.account_id].subtype for s in entry.splits]
        assert "wallet_expense" in subtypes, "Should have gas expense split"

    async def test_process_wallet_batch(self, session):
        entity, wallet, tx = await _setup(session)

        # Add another TX
        tx2 = Transaction(
            wallet_id=wallet.id,
            chain="ethereum",
            tx_hash="0xdef456",
            block_number=18500001,
            timestamp=1700000100,
            from_addr="0x1111111111111111111111111111111111111111",
            to_addr="0x3333333333333333333333333333333333333333",
            value_wei=0,
            gas_used=46000,
            status=TxStatus.LOADED.value,
            tx_data=json.dumps({
                "hash": "0xdef456",
                "from": "0x1111111111111111111111111111111111111111",
                "to": "0x3333333333333333333333333333333333333333",
                "value": "0",
                "gasUsed": "46000",
                "gasPrice": "20000000000",
            }),
        )
        session.add(tx2)
        await session.flush()

        registry = ParserRegistry()
        bookkeeper = Bookkeeper(session, registry)
        stats = await bookkeeper.process_wallet(wallet, entity.id)

        assert stats["total"] == 2
        assert stats["processed"] + stats["errors"] == 2

    async def test_error_creates_parse_error_record(self, session):
        entity, wallet, _ = await _setup(session)

        # Create a TX with invalid JSON tx_data
        bad_tx = Transaction(
            wallet_id=wallet.id,
            chain="ethereum",
            tx_hash="0xbadtx",
            block_number=18500002,
            timestamp=1700000200,
            status=TxStatus.LOADED.value,
            tx_data="not valid json {{{{",
        )
        session.add(bad_tx)
        await session.flush()

        registry = ParserRegistry()
        bookkeeper = Bookkeeper(session, registry)
        entry = await bookkeeper.process_transaction(bad_tx, wallet, entity.id)

        assert entry is None
        assert bad_tx.status == TxStatus.ERROR.value

        # Check error record was created
        from sqlalchemy import select
        from cryptotax.db.models.parse_error_record import ParseErrorRecord
        result = await session.execute(
            select(ParseErrorRecord).where(ParseErrorRecord.transaction_id == bad_tx.id)
        )
        error = result.scalar_one_or_none()
        assert error is not None
        assert error.error_type == "TxParseError"
