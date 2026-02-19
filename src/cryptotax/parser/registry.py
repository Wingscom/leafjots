"""ParserRegistry — chain+address → parser lookup with fallback chain."""

from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.generic.evm import GenericEVMParser
from cryptotax.parser.generic.swap import GenericSwapParser


class ParserRegistry:
    """Registry mapping (chain, contract_address) → specific parser.

    Falls back to: GenericSwapParser → GenericEVMParser.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, dict[str, BaseParser]] = {}
        self._chain_parsers: dict[str, list[BaseParser]] = {}
        self._fallback_chain: list[BaseParser] = [
            GenericSwapParser(),
            GenericEVMParser(),  # Always last
        ]

    def register(self, chain: str, address: str, parser: BaseParser) -> None:
        self._parsers.setdefault(chain, {})[address.lower()] = parser

    def register_chain_parsers(self, chain: str, parsers: list[BaseParser]) -> None:
        """Register parsers for an entire chain (e.g. CEX chains)."""
        self._chain_parsers[chain] = parsers

    def get(self, chain: str, address: str | None) -> list[BaseParser]:
        """Return ordered list: specific parser first, then chain parsers, then fallbacks."""
        # Chain-level parsers (e.g. CEX) — no fallback to generic EVM
        if chain in self._chain_parsers:
            chain_map = self._parsers.get(chain, {})
            if address and address.lower() in chain_map:
                return [chain_map[address.lower()]] + self._chain_parsers[chain]
            return list(self._chain_parsers[chain])

        chain_map = self._parsers.get(chain, {})
        if address and address.lower() in chain_map:
            return [chain_map[address.lower()]] + self._fallback_chain
        return list(self._fallback_chain)

    def register_protocol(self, chain: str, protocol_parsers: dict[str, BaseParser]) -> None:
        """Bulk-register parsers for a protocol's contract addresses."""
        for address, parser in protocol_parsers.items():
            self.register(chain, address, parser)


def build_default_registry() -> ParserRegistry:
    """Create a ParserRegistry with all protocol parsers registered."""
    from cryptotax.parser.defi.aave_v3 import AAVE_V3_POOL, AaveV3Parser
    from cryptotax.parser.defi.curve import CURVE_POOLS, CurvePoolParser
    from cryptotax.parser.defi.pancakeswap import PANCAKESWAP_ROUTERS, PancakeSwapParser
    from cryptotax.parser.defi.uniswap_v3 import (
        UNISWAP_V3_NFT_MANAGER,
        UNISWAP_V3_ROUTERS,
        UniswapV3Parser,
    )

    registry = ParserRegistry()

    # Aave V3
    aave_parser = AaveV3Parser()
    for chain, pool_addr in AAVE_V3_POOL.items():
        registry.register(chain, pool_addr, aave_parser)

    # Uniswap V3 — single parser handles both routers and NFT manager
    uni_parser = UniswapV3Parser()
    for chain, routers in UNISWAP_V3_ROUTERS.items():
        for addr in routers:
            registry.register(chain, addr, uni_parser)
    for chain, nft_addr in UNISWAP_V3_NFT_MANAGER.items():
        registry.register(chain, nft_addr, uni_parser)

    # Curve
    curve_parser = CurvePoolParser()
    for chain, pools in CURVE_POOLS.items():
        for addr in pools:
            registry.register(chain, addr, curve_parser)

    # PancakeSwap
    pancake_parser = PancakeSwapParser()
    for chain, routers in PANCAKESWAP_ROUTERS.items():
        for addr in routers:
            registry.register(chain, addr, pancake_parser)

    # Morpho Blue
    from cryptotax.parser.defi.morpho import METAMORPHO_VAULTS, MORPHO_BLUE, MetaMorphoVaultParser, MorphoBlueParser

    morpho_parser = MorphoBlueParser()
    for chain, pool_addr in MORPHO_BLUE.items():
        registry.register(chain, pool_addr, morpho_parser)

    metamorpho_parser = MetaMorphoVaultParser()
    for chain, vaults in METAMORPHO_VAULTS.items():
        for addr in vaults:
            registry.register(chain, addr, metamorpho_parser)

    # Lido
    from cryptotax.parser.defi.lido import LIDO_STETH, LIDO_WSTETH, LidoParser

    lido_parser = LidoParser()
    for chain, addr in LIDO_STETH.items():
        registry.register(chain, addr, lido_parser)
    for chain, addr in LIDO_WSTETH.items():
        registry.register(chain, addr, lido_parser)

    # Pendle
    from cryptotax.parser.defi.pendle import PENDLE_ROUTER, PENDLE_ROUTER_V4, PendleParser

    pendle_parser = PendleParser()
    for chain, addr in PENDLE_ROUTER.items():
        registry.register(chain, addr, pendle_parser)
    for chain, addr in PENDLE_ROUTER_V4.items():
        registry.register(chain, addr, pendle_parser)

    # Binance CEX
    from cryptotax.parser.cex.binance import BinanceDepositParser, BinanceTradeParser, BinanceWithdrawalParser

    registry.register_chain_parsers("binance", [
        BinanceTradeParser(),
        BinanceDepositParser(),
        BinanceWithdrawalParser(),
    ])

    return registry
