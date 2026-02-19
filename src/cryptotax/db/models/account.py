import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cryptotax.db.session import Base, TimestampMixin, UUIDPrimaryKey


class Account(UUIDPrimaryKey, TimestampMixin, Base):
    """Account using single-table inheritance (8 subtypes)."""

    __tablename__ = "accounts"

    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"))
    account_type: Mapped[str] = mapped_column(String(20))
    subtype: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    token_address: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    protocol: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    balance_type: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    label: Mapped[Optional[str]] = mapped_column(String(255), default=None)

    __mapper_args__ = {
        "polymorphic_on": "subtype",
        "polymorphic_identity": "account",
    }


class NativeAsset(Account):
    __mapper_args__ = {"polymorphic_identity": "native_asset"}


class ERC20Token(Account):
    __mapper_args__ = {"polymorphic_identity": "erc20_token"}


class ProtocolAsset(Account):
    __mapper_args__ = {"polymorphic_identity": "protocol_asset"}


class ProtocolDebt(Account):
    __mapper_args__ = {"polymorphic_identity": "protocol_debt"}


class WalletIncome(Account):
    __mapper_args__ = {"polymorphic_identity": "wallet_income"}


class WalletExpense(Account):
    __mapper_args__ = {"polymorphic_identity": "wallet_expense"}


class ExternalTransfer(Account):
    __mapper_args__ = {"polymorphic_identity": "external_transfer"}


class CexAsset(Account):
    __mapper_args__ = {"polymorphic_identity": "cex_asset"}


class ManualEntry(Account):
    __mapper_args__ = {"polymorphic_identity": "manual_entry"}
