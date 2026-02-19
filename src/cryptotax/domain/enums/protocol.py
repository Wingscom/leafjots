from enum import Enum


class Protocol(str, Enum):
    """DeFi protocols with specific parser support."""

    UNKNOWN = "unknown"
    GENERIC = "generic"
    AAVE_V3 = "aave_v3"
    UNISWAP_V3 = "uniswap_v3"
    PANCAKESWAP = "pancakeswap"
    CURVE = "curve"
    MORPHO = "morpho"
    LIDO = "lido"
    PENDLE = "pendle"
