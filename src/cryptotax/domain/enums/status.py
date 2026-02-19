from enum import Enum


class TxStatus(str, Enum):
    """Transaction processing status."""

    LOADED = "LOADED"
    PARSED = "PARSED"
    ERROR = "ERROR"
    IGNORED = "IGNORED"


class WalletSyncStatus(str, Enum):
    """Wallet sync state."""

    IDLE = "IDLE"
    SYNCING = "SYNCING"
    SYNCED = "SYNCED"
    ERROR = "ERROR"
