from enum import Enum


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class GainsMode(str, Enum):
    """FIFO lot matching mode. Vietnam requires GLOBAL_FIFO."""

    GLOBAL_FIFO = "GLOBAL_FIFO"
    PER_WALLET = "PER_WALLET"


class TaxExemptionReason(str, Enum):
    """Why a transfer is tax-exempt under Vietnam law."""

    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    SELF_TRANSFER = "SELF_TRANSFER"
    GAS_FEE = "GAS_FEE"
