from enum import Enum


class Chain(str, Enum):
    """Supported blockchain networks. Values lowercase to match RPC/API conventions."""

    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    POLYGON = "polygon"
    BASE = "base"
    BSC = "bsc"
    AVALANCHE = "avalanche"
    SOLANA = "solana"
