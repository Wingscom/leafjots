"""Lido Parser — ETH staking via submit() and wstETH wrap/unwrap.

Lido stETH is a rebasing token. wstETH is the non-rebasing wrapper.
Submit: ETH → stETH (staking)
Wrap: stETH → wstETH
Unwrap: wstETH → stETH
"""

from decimal import Decimal

from cryptotax.domain.enums import EntryType
from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.handlers.wrap import make_wrap_splits, make_unwrap_splits
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.gas import make_gas_splits, native_symbol
from cryptotax.parser.utils.types import ParsedSplit, ParseResult

# Lido stETH contract per chain
LIDO_STETH: dict[str, str] = {
    "ethereum": "0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
}

# wstETH contract per chain
LIDO_WSTETH: dict[str, str] = {
    "ethereum": "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0",
    "arbitrum": "0x5979d7b546e38e414f7e9822514be443a4800529",
    "optimism": "0x1f32b1c2345538c0c6f582fcb022739c4a194ebb",
    "polygon": "0x03b54a6e9a984069379fae1a4fc4dbae93b3bccd",
    "base": "0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452",
}

# Function selectors
SUBMIT_SELECTOR = "0xa1903eab"    # submit(address) — stake ETH
WRAP_SELECTOR = "0xea598cb0"      # wrap(uint256) — stETH → wstETH
UNWRAP_SELECTOR = "0xde0e9a3e"    # unwrap(uint256) — wstETH → stETH

PROTOCOL = "lido"


def _all_lido_addresses(chain: str) -> set[str]:
    """All Lido-related addresses for a chain."""
    addrs: set[str] = set()
    if chain in LIDO_STETH:
        addrs.add(LIDO_STETH[chain])
    if chain in LIDO_WSTETH:
        addrs.add(LIDO_WSTETH[chain])
    return addrs


class LidoParser(BaseParser):
    """Handles Lido staking and wstETH wrap/unwrap."""

    PARSER_NAME = "LidoParser"
    ENTRY_TYPE = EntryType.DEPOSIT

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        to_addr = tx_data.get("to", "").lower()
        chain = tx_data.get("chain", "ethereum")
        return to_addr in _all_lido_addresses(chain)

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        chain = tx_data.get("chain", "ethereum")
        to_addr = tx_data.get("to", "").lower()
        input_data = tx_data.get("input", "")
        selector = input_data[:10].lower() if len(input_data) >= 10 else ""

        splits = list(make_gas_splits(tx_data, chain, context))

        steth_addr = LIDO_STETH.get(chain, "")
        wsteth_addr = LIDO_WSTETH.get(chain, "")

        if to_addr == steth_addr and selector == SUBMIT_SELECTOR:
            # Stake ETH → receive stETH
            entry_type = EntryType.DEPOSIT
            splits.extend(self._handle_submit(tx_data, context, chain))
        elif to_addr == wsteth_addr and selector == WRAP_SELECTOR:
            # Wrap stETH → wstETH
            entry_type = EntryType.SWAP
            splits.extend(self._handle_wrap(tx_data, context, chain))
        elif to_addr == wsteth_addr and selector == UNWRAP_SELECTOR:
            # Unwrap wstETH → stETH
            entry_type = EntryType.SWAP
            splits.extend(self._handle_unwrap(tx_data, context, chain))
        else:
            return self._make_result([])

        return self._make_result(splits, entry_type)

    def _handle_submit(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Stake ETH: native ETH out, stETH in."""
        wallet = tx_data.get("from", "").lower()
        nat_sym = native_symbol(chain)

        # ETH value sent
        value_wei = int(tx_data.get("value", "0"))
        if value_wei == 0:
            return []

        eth_qty = Decimal(value_wei) / Decimal(10**18)

        # Consume the stETH transfer (Lido -> wallet) so it doesn't leak to GenericEVM
        context.pop_transfer(to_address=wallet, transfer_type="erc20")

        return [
            # ETH leaves wallet
            ParsedSplit(
                account_subtype="native_asset",
                account_params={"chain": chain},
                quantity=-eth_qty,
                symbol=nat_sym,
            ),
            # stETH enters protocol (staking position)
            ParsedSplit(
                account_subtype="protocol_asset",
                account_params={"chain": chain, "protocol": PROTOCOL},
                quantity=eth_qty,
                symbol=nat_sym,
            ),
        ]

    def _handle_wrap(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Wrap stETH → wstETH."""
        wallet = tx_data.get("from", "").lower()

        # stETH sent to wstETH contract
        steth_transfer = context.pop_transfer(from_address=wallet, transfer_type="erc20")
        if steth_transfer is None:
            return []
        steth_qty = Decimal(str(steth_transfer.value)) / Decimal(10) ** steth_transfer.decimals

        # wstETH received
        wsteth_transfer = context.pop_transfer(to_address=wallet, transfer_type="erc20")
        wsteth_qty = steth_qty  # default
        if wsteth_transfer is not None:
            wsteth_qty = Decimal(str(wsteth_transfer.value)) / Decimal(10) ** wsteth_transfer.decimals

        return make_wrap_splits("stETH", steth_qty, "wstETH", wsteth_qty, chain)

    def _handle_unwrap(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Unwrap wstETH → stETH."""
        wallet = tx_data.get("from", "").lower()

        # wstETH sent
        wsteth_transfer = context.pop_transfer(from_address=wallet, transfer_type="erc20")
        if wsteth_transfer is None:
            return []
        wsteth_qty = Decimal(str(wsteth_transfer.value)) / Decimal(10) ** wsteth_transfer.decimals

        # stETH received
        steth_transfer = context.pop_transfer(to_address=wallet, transfer_type="erc20")
        steth_qty = wsteth_qty  # default
        if steth_transfer is not None:
            steth_qty = Decimal(str(steth_transfer.value)) / Decimal(10) ** steth_transfer.decimals

        return make_unwrap_splits("wstETH", wsteth_qty, "stETH", steth_qty, chain)
