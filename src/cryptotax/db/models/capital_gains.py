"""Capital gains persistence — ClosedLotRecord and OpenLotRecord."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from cryptotax.db.session import Base, TimestampMixin, UUIDPrimaryKey


class ClosedLotRecord(UUIDPrimaryKey, TimestampMixin, Base):
    """Persisted FIFO-matched realized gain/loss."""

    __tablename__ = "closed_lots"

    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    symbol: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    cost_basis_usd: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    proceeds_usd: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    gain_usd: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    holding_days: Mapped[int] = mapped_column(BigInteger, default=0)
    buy_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"), default=None)
    sell_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"), default=None)
    buy_timestamp: Mapped[Optional[datetime]] = mapped_column(default=None)
    sell_timestamp: Mapped[Optional[datetime]] = mapped_column(default=None)


class OpenLotRecord(UUIDPrimaryKey, TimestampMixin, Base):
    """Persisted open (unrealized) position from FIFO calculation."""

    __tablename__ = "open_lots"

    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    symbol: Mapped[str] = mapped_column(String(50))
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    cost_basis_per_unit_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    buy_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"), default=None)
    buy_timestamp: Mapped[Optional[datetime]] = mapped_column(default=None)
