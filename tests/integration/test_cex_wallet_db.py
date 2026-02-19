"""Integration tests for CEXWallet STI + coexistence with OnChainWallet."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.entity import Entity
from cryptotax.db.models.wallet import CEXWallet, OnChainWallet, Wallet


@pytest.fixture()
async def entity(session: AsyncSession):
    e = Entity(name="cex_db_test")
    session.add(e)
    await session.flush()
    return e


class TestCEXWalletSTI:
    async def test_create_cex_wallet(self, session, entity):
        wallet = CEXWallet(
            entity_id=entity.id,
            exchange="binance",
            api_key_encrypted="enc_k",
            api_secret_encrypted="enc_s",
            label="My Binance",
        )
        session.add(wallet)
        await session.flush()

        assert wallet.id is not None
        assert wallet.wallet_type == "cex"
        assert wallet.exchange == "binance"

    async def test_query_cex_wallet_by_type(self, session, entity):
        wallet = CEXWallet(
            entity_id=entity.id,
            exchange="binance",
            label="Test",
        )
        session.add(wallet)
        await session.flush()

        result = await session.execute(
            select(CEXWallet).where(CEXWallet.entity_id == entity.id)
        )
        found = result.scalar_one()
        assert found.exchange == "binance"
        assert found.wallet_type == "cex"

    async def test_cex_and_onchain_coexist(self, session, entity):
        onchain = OnChainWallet(
            entity_id=entity.id,
            chain="ethereum",
            address="0x1234567890abcdef1234567890abcdef12345678",
        )
        cex = CEXWallet(
            entity_id=entity.id,
            exchange="binance",
            label="Binance",
        )
        session.add_all([onchain, cex])
        await session.flush()

        # Query base Wallet — both returned
        result = await session.execute(
            select(Wallet).where(Wallet.entity_id == entity.id)
        )
        wallets = list(result.scalars().all())
        assert len(wallets) == 2

        types = {w.wallet_type for w in wallets}
        assert "onchain" in types
        assert "cex" in types

    async def test_cex_wallet_polymorphic_identity(self, session, entity):
        cex = CEXWallet(
            entity_id=entity.id,
            exchange="binance",
        )
        session.add(cex)
        await session.flush()

        # Query via base class
        result = await session.execute(
            select(Wallet).where(Wallet.id == cex.id)
        )
        wallet = result.scalar_one()
        assert isinstance(wallet, CEXWallet)

    async def test_cex_wallet_fields(self, session, entity):
        cex = CEXWallet(
            entity_id=entity.id,
            exchange="binance",
            api_key_encrypted="encrypted_api_key_value",
            api_secret_encrypted="encrypted_api_secret_value",
            last_trade_id="trade_12345",
            label="Full CEX",
        )
        session.add(cex)
        await session.flush()

        result = await session.execute(
            select(CEXWallet).where(CEXWallet.id == cex.id)
        )
        found = result.scalar_one()
        assert found.api_key_encrypted == "encrypted_api_key_value"
        assert found.api_secret_encrypted == "encrypted_api_secret_value"
        assert found.last_trade_id == "trade_12345"
        assert found.sync_status == "IDLE"

    async def test_wallet_repo_returns_both_types(self, session, entity):
        """WalletRepo.get_all() returns both OnChainWallet and CEXWallet."""
        from cryptotax.db.repos.wallet_repo import WalletRepo

        onchain = OnChainWallet(entity_id=entity.id, chain="polygon", address="0xabc")
        cex = CEXWallet(entity_id=entity.id, exchange="binance")
        session.add_all([onchain, cex])
        await session.flush()

        repo = WalletRepo(session)
        wallets = await repo.get_all(entity.id)
        assert len(wallets) == 2
        types = {w.wallet_type for w in wallets}
        assert types == {"onchain", "cex"}
