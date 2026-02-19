from enum import Enum


class EntryType(str, Enum):
    """Classification of journal entries by DeFi operation type."""

    SWAP = "SWAP"
    TRANSFER = "TRANSFER"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BORROW = "BORROW"
    REPAY = "REPAY"
    LIQUIDATION = "LIQUIDATION"
    YIELD = "YIELD"
    GAS_FEE = "GAS_FEE"
    MINT = "MINT"
    BURN = "BURN"
    BRIDGE = "BRIDGE"
    APPROVAL = "APPROVAL"
    UNKNOWN = "UNKNOWN"
