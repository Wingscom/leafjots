from datetime import datetime
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cryptotax.db.session import Base, TimestampMixin, UUIDPrimaryKey
from cryptotax.domain.enums import Currency


class Entity(UUIDPrimaryKey, TimestampMixin, Base):
    """A taxable entity (person or company) that owns wallets."""

    __tablename__ = "entities"

    name: Mapped[str] = mapped_column(String(255))
    base_currency: Mapped[str] = mapped_column(String(10), default=Currency.VND.value)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    wallets: Mapped[list["Wallet"]] = relationship(back_populates="entity", lazy="selectin")  # noqa: F821
