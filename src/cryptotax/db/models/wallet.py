import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cryptotax.db.session import Base, TimestampMixin, UUIDPrimaryKey
from cryptotax.domain.enums import WalletSyncStatus


class Wallet(UUIDPrimaryKey, TimestampMixin, Base):
    """Base wallet using single-table inheritance."""

    __tablename__ = "wallets"

    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    label: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    wallet_type: Mapped[str] = mapped_column(String(50))
    sync_status: Mapped[str] = mapped_column(String(20), default=WalletSyncStatus.IDLE.value)

    entity: Mapped["Entity"] = relationship(back_populates="wallets")  # noqa: F821

    __mapper_args__ = {
        "polymorphic_on": "wallet_type",
        "polymorphic_identity": "wallet",
        "with_polymorphic": "*",
    }


class OnChainWallet(Wallet):
    """EVM or Solana on-chain wallet."""

    chain: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    address: Mapped[Optional[str]] = mapped_column(String(255), default=None, index=True)
    last_block_loaded: Mapped[Optional[int]] = mapped_column(BigInteger, default=None)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)

    __mapper_args__ = {
        "polymorphic_identity": "onchain",
    }


class CEXWallet(Wallet):
    """Centralized exchange wallet (e.g. Binance)."""

    exchange: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    api_secret_encrypted: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    last_trade_id: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None, use_existing_column=True)

    __mapper_args__ = {
        "polymorphic_identity": "cex",
    }
