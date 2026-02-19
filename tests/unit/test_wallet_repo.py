import uuid


from cryptotax.db.repos.entity_repo import EntityRepo
from cryptotax.db.repos.wallet_repo import WalletRepo
from cryptotax.domain.enums import Chain


class TestEntityRepo:
    async def test_get_or_create_default_creates_entity(self, session):
        repo = EntityRepo(session)
        entity = await repo.get_or_create_default()
        await session.commit()

        assert entity.id is not None
        assert entity.name == "Default"
        assert entity.base_currency == "VND"

    async def test_get_or_create_default_idempotent(self, session):
        repo = EntityRepo(session)
        e1 = await repo.get_or_create_default()
        await session.commit()
        e2 = await repo.get_or_create_default()

        assert e1.id == e2.id

    async def test_get_default_returns_none_when_empty(self, session):
        repo = EntityRepo(session)
        result = await repo.get_default()
        assert result is None


class TestWalletRepo:
    async def _make_entity(self, session):
        repo = EntityRepo(session)
        entity = await repo.get_or_create_default()
        await session.commit()
        return entity

    async def test_create_wallet(self, session):
        entity = await self._make_entity(session)
        repo = WalletRepo(session)

        wallet = await repo.create(entity_id=entity.id, chain=Chain.ETHEREUM, address="0xAbCdEf")
        await session.commit()

        assert wallet.id is not None
        assert wallet.chain == "ethereum"
        assert wallet.address == "0xabcdef"
        assert wallet.sync_status == "IDLE"
        assert wallet.last_synced_at is None

    async def test_address_normalized_to_lowercase(self, session):
        entity = await self._make_entity(session)
        repo = WalletRepo(session)

        wallet = await repo.create(entity_id=entity.id, chain=Chain.ETHEREUM, address="0xABCDEF")
        await session.commit()

        assert wallet.address == "0xabcdef"

    async def test_get_by_id(self, session):
        entity = await self._make_entity(session)
        repo = WalletRepo(session)

        created = await repo.create(entity_id=entity.id, chain=Chain.BASE, address="0x1111")
        await session.commit()

        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_by_id_not_found(self, session):
        repo = WalletRepo(session)
        result = await repo.get_by_id(uuid.uuid4())
        assert result is None

    async def test_dedup_by_chain_and_address(self, session):
        entity = await self._make_entity(session)
        repo = WalletRepo(session)

        await repo.create(entity_id=entity.id, chain=Chain.ETHEREUM, address="0xdeadbeef")
        await session.commit()

        duplicate = await repo.get_by_chain_and_address(entity.id, Chain.ETHEREUM, "0xdeadbeef")
        assert duplicate is not None

    async def test_dedup_case_insensitive(self, session):
        entity = await self._make_entity(session)
        repo = WalletRepo(session)

        await repo.create(entity_id=entity.id, chain=Chain.ETHEREUM, address="0xDeAdBeEf")
        await session.commit()

        result = await repo.get_by_chain_and_address(entity.id, Chain.ETHEREUM, "0xdeadbeef")
        assert result is not None

    async def test_different_chain_not_dedup(self, session):
        entity = await self._make_entity(session)
        repo = WalletRepo(session)

        await repo.create(entity_id=entity.id, chain=Chain.ETHEREUM, address="0xdeadbeef")
        await session.commit()

        result = await repo.get_by_chain_and_address(entity.id, Chain.ARBITRUM, "0xdeadbeef")
        assert result is None

    async def test_get_all_returns_list(self, session):
        entity = await self._make_entity(session)
        repo = WalletRepo(session)

        await repo.create(entity_id=entity.id, chain=Chain.ETHEREUM, address="0x0001")
        await repo.create(entity_id=entity.id, chain=Chain.ETHEREUM, address="0x0002")
        await repo.create(entity_id=entity.id, chain=Chain.ETHEREUM, address="0x0003")
        await session.commit()

        wallets = await repo.get_all(entity.id)
        assert len(wallets) == 3

    async def test_delete_wallet(self, session):
        entity = await self._make_entity(session)
        repo = WalletRepo(session)

        wallet = await repo.create(entity_id=entity.id, chain=Chain.ETHEREUM, address="0xdead")
        await session.commit()

        await repo.delete(wallet)
        await session.commit()

        result = await repo.get_by_id(wallet.id)
        assert result is None
