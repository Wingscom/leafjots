from enum import Enum


class BalanceType(str, Enum):
    """DeFi protocol position types."""

    SUPPLY = "supply"
    BORROW = "borrow"
    REWARD = "reward"
