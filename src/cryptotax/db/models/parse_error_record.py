import uuid
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cryptotax.db.session import Base, TimestampMixin, UUIDPrimaryKey


class ParseErrorRecord(UUIDPrimaryKey, TimestampMixin, Base):
    """Tracks parsing errors for the Error Dashboard."""

    __tablename__ = "parse_error_records"

    transaction_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("transactions.id"), default=None)
    wallet_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("wallets.id"), default=None)
    error_type: Mapped[str] = mapped_column(String(50))
    message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, default=None)
    resolved: Mapped[bool] = mapped_column(default=False)
    diagnostic_data: Mapped[Optional[str]] = mapped_column(Text, default=None)  # JSON diagnostic payload
