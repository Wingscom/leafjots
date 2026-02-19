import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.wallet import CEXWallet, OnChainWallet, Wallet
from cryptotax.domain.enums import Chain, Exchange, WalletSyncStatus


class WalletRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self, entity_id: uuid.UUID) -> list[Wallet]:
        """Return all wallets (on-chain + CEX) for an entity."""
        result = await self._session.execute(
            select(Wallet)
            .where(Wallet.entity_id == entity_id)
            .order_by(Wallet.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, wallet_id: uuid.UUID) -> Optional[Wallet]:
        result = await self._session.execute(
            select(Wallet).where(Wallet.id == wallet_id)
        )
        return result.scalar_one_or_none()

    async def get_by_chain_and_address(
        self, entity_id: uuid.UUID, chain: Chain, address: str
    ) -> Optional[OnChainWallet]:
        normalized = self._normalize_address(address, chain)
        result = await self._session.execute(
            select(OnChainWallet).where(
                OnChainWallet.entity_id == entity_id,
                OnChainWallet.chain == chain.value,
                OnChainWallet.address == normalized,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_exchange(
        self, entity_id: uuid.UUID, exchange: Exchange
    ) -> Optional[CEXWallet]:
        result = await self._session.execute(
            select(CEXWallet).where(
                CEXWallet.entity_id == entity_id,
                CEXWallet.exchange == exchange.value,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        entity_id: uuid.UUID,
        chain: Chain,
        address: str,
        label: Optional[str] = None,
    ) -> OnChainWallet:
        wallet = OnChainWallet(
            entity_id=entity_id,
            chain=chain.value,
            address=self._normalize_address(address, chain),
            label=label,
        )
        self._session.add(wallet)
        await self._session.flush()
        return wallet

    @staticmethod
    def _normalize_address(address: str, chain: Chain) -> str:
        """Normalize address: lowercase for EVM chains, preserve case for Solana."""
        if chain == Chain.SOLANA:
            return address  # Solana uses base58 (case-sensitive)
        return address.lower()  # EVM addresses are hex (case-insensitive)

    async def create_cex_wallet(
        self,
        entity_id: uuid.UUID,
        exchange: Exchange,
        api_key_encrypted: str = "",
        api_secret_encrypted: str = "",
        label: Optional[str] = None,
    ) -> CEXWallet:
        wallet = CEXWallet(
            entity_id=entity_id,
            exchange=exchange.value,
            api_key_encrypted=api_key_encrypted,
            api_secret_encrypted=api_secret_encrypted,
            label=label or f"{exchange.value} wallet",
        )
        self._session.add(wallet)
        await self._session.flush()
        return wallet

    async def delete(self, wallet: Wallet) -> None:
        await self._session.delete(wallet)
        await self._session.flush()

    async def update_sync_status(self, wallet: Wallet, status: WalletSyncStatus) -> Wallet:
        wallet.sync_status = status.value
        await self._session.flush()
        return wallet
