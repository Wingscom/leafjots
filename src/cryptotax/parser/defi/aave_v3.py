"""Aave V3 Pool Parser — handles Supply, Withdraw, Borrow, Repay.

Uses function-selector detection on the Aave V3 Pool contract,
then consumes token transfers from context to build balanced splits.
"""

from decimal import Decimal

from cryptotax.domain.enums import EntryType
from cryptotax.parser.generic.base import BaseParser
from cryptotax.parser.handlers.common import (
    make_borrow_splits,
    make_deposit_splits,
    make_repay_splits,
    make_withdrawal_splits,
)
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.gas import make_gas_splits
from cryptotax.parser.utils.types import ParsedSplit, ParseResult

# Function selectors (first 4 bytes of keccak256 of function signature)
SUPPLY_SELECTOR = "0x617ba037"      # supply(address,uint256,address,uint16)
WITHDRAW_SELECTOR = "0x69328dec"    # withdraw(address,uint256,address)
BORROW_SELECTOR = "0xa415bcad"      # borrow(address,uint256,uint256,uint16,address)
REPAY_SELECTOR = "0x573ade81"       # repay(address,uint256,uint256,address)
REPAY_WITH_ATOKENS = "0x2dad97d4"   # repayWithATokens(address,uint256,uint256)

# Aave V3 Pool addresses per chain (all lowercase)
AAVE_V3_POOL: dict[str, str] = {
    "ethereum": "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2",
    "arbitrum": "0x794a61358d6845594f94dc1db02a252b5b4814ad",
    "optimism": "0x794a61358d6845594f94dc1db02a252b5b4814ad",
    "polygon": "0x794a61358d6845594f94dc1db02a252b5b4814ad",
    "base": "0xa238dd80c259a72e81d7e4664a9801593f98d1c5",
    "avalanche": "0x794a61358d6845594f94dc1db02a252b5b4814ad",
}

PROTOCOL = "aave_v3"


class AaveV3Parser(BaseParser):
    PARSER_NAME = "AaveV3Parser"
    ENTRY_TYPE = EntryType.DEPOSIT

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        to_addr = tx_data.get("to", "").lower()
        chain = tx_data.get("chain", "ethereum")
        pool = AAVE_V3_POOL.get(chain, "")
        return to_addr == pool and pool != ""

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        chain = tx_data.get("chain", "ethereum")
        input_data = tx_data.get("input", "")
        selector = input_data[:10].lower() if len(input_data) >= 10 else ""

        splits = list(make_gas_splits(tx_data, chain, context))

        if selector == SUPPLY_SELECTOR:
            entry_type = EntryType.DEPOSIT
            splits.extend(self._handle_supply(tx_data, context, chain))
        elif selector == WITHDRAW_SELECTOR:
            entry_type = EntryType.WITHDRAWAL
            splits.extend(self._handle_withdraw(tx_data, context, chain))
        elif selector == BORROW_SELECTOR:
            entry_type = EntryType.BORROW
            splits.extend(self._handle_borrow(tx_data, context, chain))
        elif selector in (REPAY_SELECTOR, REPAY_WITH_ATOKENS):
            entry_type = EntryType.REPAY
            splits.extend(self._handle_repay(tx_data, context, chain))
        else:
            # Unknown Aave function — return empty to fall through to GenericSwap
            return self._make_result([])

        return self._make_result(splits, entry_type)

    def _handle_supply(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Supply: user sends token to pool. token_asset(-) / protocol_asset(+)."""
        wallet = tx_data.get("from", "").lower()
        pool = tx_data.get("to", "").lower()

        transfer = context.pop_transfer(from_address=wallet, to_address=pool, transfer_type="erc20")
        if transfer is None:
            transfer = context.pop_transfer(from_address=wallet, transfer_type="erc20")
        if transfer is None:
            return []

        qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals

        # Consume the aToken mint transfer (pool -> wallet)
        context.pop_transfer(to_address=wallet, transfer_type="erc20")

        return make_deposit_splits(transfer.symbol, qty, PROTOCOL, chain)

    def _handle_withdraw(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Withdraw: pool sends underlying to user. protocol_asset(-) / token_asset(+)."""
        wallet = tx_data.get("from", "").lower()

        transfer = context.pop_transfer(to_address=wallet, transfer_type="erc20")
        if transfer is None:
            return []

        qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals

        # Consume the aToken burn transfer (wallet -> pool)
        context.pop_transfer(from_address=wallet, transfer_type="erc20")

        return make_withdrawal_splits(transfer.symbol, qty, PROTOCOL, chain)

    def _handle_borrow(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Borrow: pool sends token to user. protocol_debt(-) / token_asset(+)."""
        wallet = tx_data.get("from", "").lower()

        transfer = context.pop_transfer(to_address=wallet, transfer_type="erc20")
        if transfer is None:
            return []

        qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals

        # Consume debt token mint (zero-address -> wallet)
        context.pop_transfer(to_address=wallet, transfer_type="erc20")

        return make_borrow_splits(transfer.symbol, qty, PROTOCOL, chain)

    def _handle_repay(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Repay: user sends token to pool. token_asset(-) / protocol_debt(+)."""
        wallet = tx_data.get("from", "").lower()

        transfer = context.pop_transfer(from_address=wallet, transfer_type="erc20")
        if transfer is None:
            return []

        qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals

        # Consume debt token burn (wallet -> zero-address)
        context.pop_transfer(from_address=wallet, transfer_type="erc20")

        return make_repay_splits(transfer.symbol, qty, PROTOCOL, chain)
