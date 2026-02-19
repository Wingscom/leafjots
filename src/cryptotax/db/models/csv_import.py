import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cryptotax.db.session import Base, TimestampMixin, UUIDPrimaryKey


class CsvImport(UUIDPrimaryKey, TimestampMixin, Base):
    """Metadata for a CSV file upload."""
    __tablename__ = "csv_imports"

    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    exchange: Mapped[str] = mapped_column(String(50), default="binance")
    filename: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    parsed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    # status: uploaded -> parsing -> completed -> error

    rows: Mapped[list["CsvImportRow"]] = relationship(
        back_populates="csv_import", cascade="all, delete-orphan", lazy="selectin"
    )


class CsvImportRow(UUIDPrimaryKey, Base):
    """A single raw CSV row stored for audit trail and re-parsing."""
    __tablename__ = "csv_import_rows"

    import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("csv_imports.id"))
    row_number: Mapped[int] = mapped_column(Integer)
    # Raw CSV fields stored individually for easy querying
    utc_time: Mapped[str] = mapped_column(String(30))
    account: Mapped[str] = mapped_column(String(50))
    operation: Mapped[str] = mapped_column(String(100))
    coin: Mapped[str] = mapped_column(String(20))
    change: Mapped[str] = mapped_column(String(50))  # stored as string, parsed to Decimal by parser
    remark: Mapped[Optional[str]] = mapped_column(Text, default=None)
    # Parse result tracking
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # status: pending -> parsed -> error -> skipped
    error_message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("journal_entries.id"), default=None
    )

    csv_import: Mapped["CsvImport"] = relationship(back_populates="rows")
