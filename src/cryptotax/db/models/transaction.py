import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cryptotax.db.session import Base, TimestampMixin
from cryptotax.domain.enums import TxStatus


class Transaction(TimestampMixin, Base):
    """On-chain transaction. BigInt PK for high-volume append-only data."""

    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("wallet_id", "tx_hash", name="uq_wallet_tx_hash"),
        Index("ix_chain_block_number", "chain", "block_number"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True, autoincrement=True)
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"))
    chain: Mapped[str] = mapped_column(String(20))
    tx_hash: Mapped[str] = mapped_column(String(100), index=True)
    block_number: Mapped[Optional[int]] = mapped_column(BigInteger, default=None)
    timestamp: Mapped[Optional[int]] = mapped_column(BigInteger, default=None)
    from_addr: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    to_addr: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    value_wei: Mapped[Optional[int]] = mapped_column(BigInteger, default=None)
    gas_used: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    status: Mapped[str] = mapped_column(String(20), default=TxStatus.LOADED.value)
    tx_data: Mapped[Optional[str]] = mapped_column(Text, default=None)
    entry_type: Mapped[Optional[str]] = mapped_column(String(50), default=None)
