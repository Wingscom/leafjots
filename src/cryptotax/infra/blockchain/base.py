"""Abstract base for chain-specific transaction loaders."""

from abc import ABC, abstractmethod

from cryptotax.db.models.wallet import OnChainWallet


class ChainTxLoader(ABC):
    """Strategy interface for loading transactions from a specific chain."""

    @abstractmethod
    async def load_wallet(self, wallet: OnChainWallet) -> int:
        """Load new transactions for a wallet. Returns count of new TXs inserted."""
