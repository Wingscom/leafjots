"""Integration test: build_default_registry selects protocol parser over generic."""

from cryptotax.parser.defi.aave_v3 import AAVE_V3_POOL
from cryptotax.parser.defi.curve import CURVE_POOLS
from cryptotax.parser.defi.uniswap_v3 import UNISWAP_V3_ROUTERS
from cryptotax.parser.registry import build_default_registry


class TestBuildDefaultRegistry:
    def test_aave_pool_gets_aave_parser_first(self):
        registry = build_default_registry()
        parsers = registry.get("ethereum", AAVE_V3_POOL["ethereum"])
        assert parsers[0].PARSER_NAME == "AaveV3Parser"

    def test_uniswap_router_gets_uniswap_parser_first(self):
        registry = build_default_registry()
        parsers = registry.get("ethereum", UNISWAP_V3_ROUTERS["ethereum"][0])
        assert parsers[0].PARSER_NAME == "UniswapV3Parser"

    def test_curve_pool_gets_curve_parser_first(self):
        registry = build_default_registry()
        parsers = registry.get("ethereum", CURVE_POOLS["ethereum"][0])
        assert parsers[0].PARSER_NAME == "CurvePoolParser"

    def test_unknown_address_gets_fallback_chain(self):
        registry = build_default_registry()
        parsers = registry.get("ethereum", "0xunknown")
        names = [p.PARSER_NAME for p in parsers]
        assert "GenericSwapParser" in names
        assert "GenericEVMParser" in names
        assert names[0] == "GenericSwapParser"

    def test_fallback_has_generic_evm_last(self):
        registry = build_default_registry()
        parsers = registry.get("ethereum", "0xunknown")
        assert parsers[-1].PARSER_NAME == "GenericEVMParser"

    def test_protocol_parser_plus_fallbacks(self):
        """Protocol parser is first, then fallback chain follows."""
        registry = build_default_registry()
        parsers = registry.get("ethereum", AAVE_V3_POOL["ethereum"])
        names = [p.PARSER_NAME for p in parsers]
        assert names[0] == "AaveV3Parser"
        assert "GenericSwapParser" in names
        assert "GenericEVMParser" in names
