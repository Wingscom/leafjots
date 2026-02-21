"""TaxableTransferRecord — persisted taxable transfers from Vietnam 0.1% tax calculation."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from cryptotax.db.session import Base, TimestampMixin, UUIDPrimaryKey


class TaxableTransferRecord(UUIDPrimaryKey, TimestampMixin, Base):
    """Persisted taxable transfer from Vietnam 0.1% transfer tax calculation."""

    __tablename__ = "taxable_transfers"

    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("journal_entries.id"))
    symbol: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    value_usd: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    value_vnd: Mapped[Decimal] = mapped_column(Numeric(24, 0))
    tax_amount_vnd: Mapped[Decimal] = mapped_column(Numeric(24, 0))
    exemption_reason: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    timestamp: Mapped[datetime]

    __table_args__ = (
        Index("ix_taxable_transfers_entity_id", "entity_id"),
        Index("ix_taxable_transfers_timestamp", "timestamp"),
        Index("ix_taxable_transfers_symbol", "symbol"),
    )
