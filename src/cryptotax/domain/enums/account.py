from enum import Enum


class AccountType(str, Enum):
    """Four fundamental account types for double-entry bookkeeping."""

    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
