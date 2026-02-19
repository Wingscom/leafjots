from datetime import UTC, datetime
from decimal import Decimal

import pytest

from cryptotax.db.models import (
    Entity,
    ERC20Token,
    JournalEntry,
    JournalSplit,
    NativeAsset,
    OnChainWallet,
    ProtocolDebt,
    Transaction,
)
from cryptotax.domain.enums import AccountType, Chain, EntryType, TxStatus
from cryptotax.exceptions import BalanceError


class TestEntityModel:
    async def test_create_entity(self, session):
        entity = Entity(name="Alice", base_currency="VND")
        session.add(entity)
        await session.commit()
        await session.refresh(entity)

        assert entity.id is not None
        assert entity.name == "Alice"
        assert entity.base_currency == "VND"
        assert entity.deleted_at is None


class TestWalletSTI:
    async def test_create_onchain_wallet(self, session):
        entity = Entity(name="Bob", base_currency="VND")
        session.add(entity)
        await session.commit()

        wallet = OnChainWallet(
            entity_id=entity.id,
            label="Main ETH",
            chain=Chain.ETHEREUM,
            address="0x1234567890abcdef1234567890abcdef12345678",
        )
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)

        assert wallet.wallet_type == "onchain"
        assert wallet.chain == "ethereum"
        assert wallet.sync_status == "IDLE"
        assert wallet.last_block_loaded is None


class TestAccountSTI:
    async def test_native_asset_subtype(self, session):
        entity = Entity(name="Carol", base_currency="VND")
        session.add(entity)
        await session.commit()

        wallet = OnChainWallet(entity_id=entity.id, chain=Chain.ETHEREUM, address="0xabc")
        session.add(wallet)
        await session.commit()

        acct = NativeAsset(
            wallet_id=wallet.id,
            account_type=AccountType.ASSET,
            symbol="ETH",
        )
        session.add(acct)
        await session.commit()
        await session.refresh(acct)

        assert acct.subtype == "native_asset"
        assert acct.symbol == "ETH"
        assert acct.account_type == "ASSET"

    async def test_erc20_token_subtype(self, session):
        entity = Entity(name="Dave", base_currency="VND")
        session.add(entity)
        await session.commit()

        wallet = OnChainWallet(entity_id=entity.id, chain=Chain.ETHEREUM, address="0xdef")
        session.add(wallet)
        await session.commit()

        acct = ERC20Token(
            wallet_id=wallet.id,
            account_type=AccountType.ASSET,
            symbol="USDC",
            token_address="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        )
        session.add(acct)
        await session.commit()
        await session.refresh(acct)

        assert acct.subtype == "erc20_token"

    async def test_protocol_debt_subtype(self, session):
        entity = Entity(name="Eve", base_currency="VND")
        session.add(entity)
        await session.commit()

        wallet = OnChainWallet(entity_id=entity.id, chain=Chain.ETHEREUM, address="0x999")
        session.add(wallet)
        await session.commit()

        acct = ProtocolDebt(
            wallet_id=wallet.id,
            account_type=AccountType.LIABILITY,
            symbol="DAI",
            protocol="AAVE_V3",
        )
        session.add(acct)
        await session.commit()
        await session.refresh(acct)

        assert acct.subtype == "protocol_debt"
        assert acct.account_type == "LIABILITY"


class TestJournalDoubleEntry:
    """Every journal entry must sum to $0 — non-negotiable."""

    async def test_balanced_entry_passes(self, session):
        entity = Entity(name="Frank", base_currency="VND")
        session.add(entity)
        await session.commit()

        wallet = OnChainWallet(entity_id=entity.id, chain=Chain.ETHEREUM, address="0x111")
        session.add(wallet)
        await session.commit()

        asset_eth = NativeAsset(wallet_id=wallet.id, account_type=AccountType.ASSET, symbol="ETH")
        asset_usdc = ERC20Token(wallet_id=wallet.id, account_type=AccountType.ASSET, symbol="USDC")
        session.add_all([asset_eth, asset_usdc])
        await session.commit()

        entry = JournalEntry(
            entity_id=entity.id,
            entry_type=EntryType.SWAP,
            timestamp=datetime.now(UTC),
            description="Swap 1 ETH for 2500 USDC",
            splits=[
                JournalSplit(account_id=asset_eth.id, quantity=Decimal("-1"), value_usd=Decimal("-2500"), value_vnd=Decimal("-62500000")),
                JournalSplit(account_id=asset_usdc.id, quantity=Decimal("2500"), value_usd=Decimal("2500"), value_vnd=Decimal("62500000")),
            ],
        )
        session.add(entry)
        await session.commit()

        # Should not raise
        entry.validate_balanced()

    async def test_unbalanced_entry_raises(self, session):
        entity = Entity(name="Grace", base_currency="VND")
        session.add(entity)
        await session.commit()

        wallet = OnChainWallet(entity_id=entity.id, chain=Chain.ETHEREUM, address="0x222")
        session.add(wallet)
        await session.commit()

        acct = NativeAsset(wallet_id=wallet.id, account_type=AccountType.ASSET, symbol="ETH")
        session.add(acct)
        await session.commit()

        entry = JournalEntry(
            entity_id=entity.id,
            entry_type=EntryType.UNKNOWN,
            timestamp=datetime.now(UTC),
            splits=[
                JournalSplit(account_id=acct.id, quantity=Decimal("1"), value_usd=Decimal("100"), value_vnd=Decimal("2500000")),
            ],
        )

        with pytest.raises(BalanceError):
            entry.validate_balanced()


class TestTransactionModel:
    async def test_create_transaction(self, session):
        entity = Entity(name="Hank", base_currency="VND")
        session.add(entity)
        await session.commit()

        wallet = OnChainWallet(entity_id=entity.id, chain=Chain.ETHEREUM, address="0x333")
        session.add(wallet)
        await session.commit()

        tx = Transaction(
            wallet_id=wallet.id,
            chain=Chain.ETHEREUM,
            tx_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            block_number=12345678,
            status=TxStatus.LOADED,
        )
        session.add(tx)
        await session.commit()
        await session.refresh(tx)

        assert tx.id is not None
        assert tx.status == "LOADED"
        assert tx.entry_type is None
