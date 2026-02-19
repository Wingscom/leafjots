"""Curve Pool Parser — swaps (exchange) and liquidity operations.

Uses net-flow analysis for all operation types, with protocol attribution.
"""

from decimal import Decimal

from cryptotax.domain.enums import EntryType
from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.gas import make_gas_splits, native_symbol
from cryptotax.parser.utils.types import ParsedSplit, ParseResult

# Function selectors
EXCHANGE = "0x3df02124"              # exchange(int128,int128,uint256,uint256)
EXCHANGE_UNDERLYING = "0xa6417ed6"   # exchange_underlying(int128,int128,uint256,uint256)
ADD_LIQUIDITY_2 = "0x0b4c7e4d"      # add_liquidity(uint256[2],uint256)
ADD_LIQUIDITY_3 = "0x4515cef3"      # add_liquidity(uint256[3],uint256)
ADD_LIQUIDITY_4 = "0x029b2f34"      # add_liquidity(uint256[4],uint256)
REMOVE_LIQUIDITY = "0xecb586a5"     # remove_liquidity(uint256,uint256[3])
REMOVE_ONE_COIN = "0x1a4d01d2"      # remove_liquidity_one_coin(uint256,int128,uint256)

SWAP_SELECTORS = {EXCHANGE, EXCHANGE_UNDERLYING}
ADD_SELECTORS = {ADD_LIQUIDITY_2, ADD_LIQUIDITY_3, ADD_LIQUIDITY_4}
REMOVE_SELECTORS = {REMOVE_LIQUIDITY, REMOVE_ONE_COIN}

# Top Curve pools per chain (expandable)
CURVE_POOLS: dict[str, list[str]] = {
    "ethereum": [
        "0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7",  # 3pool (DAI/USDC/USDT)
        "0xd51a44d3fae010294c616388b506acda1bfaae46",  # Tricrypto2
        "0xdc24316b9ae028f1497c275eb9192a3ea0f67022",  # stETH/ETH
        "0xdcef968d416a41cdac0ed8702fac8128a64241a2",  # FRAX/USDC
        "0xa1f8a6807c402e4a15ef4eba36528a3fed24e577",  # ETH/frxETH
    ],
    "arbitrum": [
        "0x7f90122bf0700f9e7e1f688fe926940e8839f353",  # 2pool
    ],
    "polygon": [
        "0x445fe580ef8d70ff569ab36e80c647af338db351",  # aTriCrypto3
    ],
}

PROTOCOL = "curve"


class CurvePoolParser(BaseParser):
    PARSER_NAME = "CurvePoolParser"
    ENTRY_TYPE = EntryType.SWAP

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        to_addr = tx_data.get("to", "").lower()
        chain = tx_data.get("chain", "ethereum")
        return to_addr in CURVE_POOLS.get(chain, [])

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        chain = tx_data.get("chain", "ethereum")
        input_data = tx_data.get("input", "")
        selector = input_data[:10].lower() if len(input_data) >= 10 else ""

        splits = list(make_gas_splits(tx_data, chain, context))

        if selector in SWAP_SELECTORS:
            entry_type = EntryType.SWAP
            splits.extend(self._handle_net_flows(context, chain))
        elif selector in ADD_SELECTORS:
            entry_type = EntryType.DEPOSIT
            splits.extend(self._handle_add_liquidity(context, chain))
        elif selector in REMOVE_SELECTORS:
            entry_type = EntryType.WITHDRAWAL
            splits.extend(self._handle_remove_liquidity(context, chain))
        else:
            entry_type = EntryType.SWAP
            splits.extend(self._handle_net_flows(context, chain))

        return self._make_result(splits, entry_type)

    def _handle_net_flows(self, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        splits: list[ParsedSplit] = []
        nat_sym = native_symbol(chain)
        net = context.net_flows()

        for addr, flows in net.items():
            if not context.is_wallet(addr):
                continue
            for tok_symbol, qty in flows.items():
                if qty == Decimal(0):
                    continue
                subtype = "native_asset" if tok_symbol == nat_sym else "erc20_token"
                params = {"chain": chain} if tok_symbol == nat_sym else {"chain": chain, "symbol": tok_symbol}
                splits.append(ParsedSplit(account_subtype=subtype, account_params=params, quantity=qty, symbol=tok_symbol))

        return splits

    def _handle_add_liquidity(self, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        splits: list[ParsedSplit] = []
        nat_sym = native_symbol(chain)
        net = context.net_flows()

        for addr, flows in net.items():
            if not context.is_wallet(addr):
                continue
            for tok_symbol, qty in flows.items():
                if qty == Decimal(0):
                    continue
                if qty < 0:
                    subtype = "native_asset" if tok_symbol == nat_sym else "erc20_token"
                    params = {"chain": chain} if tok_symbol == nat_sym else {"chain": chain, "symbol": tok_symbol}
                    splits.append(ParsedSplit(account_subtype=subtype, account_params=params, quantity=qty, symbol=tok_symbol))
                else:
                    splits.append(ParsedSplit(
                        account_subtype="protocol_asset",
                        account_params={"chain": chain, "protocol": PROTOCOL},
                        quantity=qty, symbol=tok_symbol,
                    ))

        return splits

    def _handle_remove_liquidity(self, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        splits: list[ParsedSplit] = []
        nat_sym = native_symbol(chain)
        net = context.net_flows()

        for addr, flows in net.items():
            if not context.is_wallet(addr):
                continue
            for tok_symbol, qty in flows.items():
                if qty == Decimal(0):
                    continue
                if qty < 0:
                    splits.append(ParsedSplit(
                        account_subtype="protocol_asset",
                        account_params={"chain": chain, "protocol": PROTOCOL},
                        quantity=qty, symbol=tok_symbol,
                    ))
                else:
                    subtype = "native_asset" if tok_symbol == nat_sym else "erc20_token"
                    params = {"chain": chain} if tok_symbol == nat_sym else {"chain": chain, "symbol": tok_symbol}
                    splits.append(ParsedSplit(account_subtype=subtype, account_params=params, quantity=qty, symbol=tok_symbol))

        return splits
