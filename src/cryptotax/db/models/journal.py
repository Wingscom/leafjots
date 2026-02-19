import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cryptotax.db.session import Base, TimestampMixin, UUIDPrimaryKey
from cryptotax.exceptions import BalanceError


class JournalEntry(UUIDPrimaryKey, TimestampMixin, Base):
    """A journal entry grouping balanced splits. Sum of all splits must equal zero."""

    __tablename__ = "journal_entries"

    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    transaction_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("transactions.id"), default=None)
    entry_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    timestamp: Mapped[datetime]

    splits: Mapped[list["JournalSplit"]] = relationship(back_populates="journal_entry", lazy="selectin", cascade="all, delete-orphan")

    def validate_balanced(self) -> None:
        """Raise BalanceError if splits don't sum to zero (USD and VND)."""
        total_usd = sum((s.value_usd or Decimal(0)) for s in self.splits)
        total_vnd = sum((s.value_vnd or Decimal(0)) for s in self.splits)
        if total_usd != Decimal(0) or total_vnd != Decimal(0):
            raise BalanceError(f"Journal entry unbalanced: USD={total_usd}, VND={total_vnd}")


class JournalSplit(UUIDPrimaryKey, TimestampMixin, Base):
    """One leg of a journal entry. Positive=increase, Negative=decrease."""

    __tablename__ = "journal_splits"

    journal_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("journal_entries.id"))
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    value_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4), default=None)
    value_vnd: Mapped[Optional[Decimal]] = mapped_column(Numeric(24, 0), default=None)

    journal_entry: Mapped[JournalEntry] = relationship(back_populates="splits")
