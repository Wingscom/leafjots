"""Report metadata — tracks generated Excel reports."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cryptotax.db.session import Base, TimestampMixin, UUIDPrimaryKey


class ReportRecord(UUIDPrimaryKey, TimestampMixin, Base):
    """Metadata for a generated bangketoan.xlsx report."""

    __tablename__ = "reports"

    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
    period_start: Mapped[datetime]
    period_end: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(20), default="generating")  # generating / completed / failed
    filename: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    generated_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    error_message: Mapped[Optional[str]] = mapped_column(Text, default=None)
