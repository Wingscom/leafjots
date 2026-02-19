"""Morpho Blue Parser — supply, withdraw, borrow, repay, supplyCollateral, withdrawCollateral.

Morpho Blue is a singleton lending protocol. All markets share one contract.
MetaMorpho vaults use ERC-4626 deposit/withdraw pattern.

Uses transfer consumption from context (same pattern as AaveV3Parser).
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

# Morpho Blue singleton contract per chain
MORPHO_BLUE: dict[str, str] = {
    "ethereum": "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb",
    "base": "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb",
}

# Function selectors (first 4 bytes of keccak256)
SUPPLY_SELECTOR = "0x0c0a769b"           # supply(MarketParams,uint256,uint256,address,bytes)
WITHDRAW_SELECTOR = "0x5c2bea49"         # withdraw(MarketParams,uint256,uint256,address,address)
BORROW_SELECTOR = "0x50d8cd4b"           # borrow(MarketParams,uint256,uint256,address,address)
REPAY_SELECTOR = "0x20b76e81"            # repay(MarketParams,uint256,uint256,address,bytes)
SUPPLY_COLLATERAL_SELECTOR = "0x238d6579"   # supplyCollateral(MarketParams,uint256,address,bytes)
WITHDRAW_COLLATERAL_SELECTOR = "0x8720316d"  # withdrawCollateral(MarketParams,uint256,address,address)
LIQUIDATE_SELECTOR = "0xd8efbe76"        # liquidate(MarketParams,address,uint256,uint256,bytes)

# MetaMorpho vault (ERC-4626) selectors
VAULT_DEPOSIT_SELECTOR = "0x6e553f65"    # deposit(uint256,address)
VAULT_MINT_SELECTOR = "0x94bf804d"       # mint(uint256,address)
VAULT_WITHDRAW_SELECTOR = "0xb460af94"   # withdraw(uint256,address,address)
VAULT_REDEEM_SELECTOR = "0xba087652"     # redeem(uint256,address,address)

VAULT_DEPOSIT_SELECTORS = {VAULT_DEPOSIT_SELECTOR, VAULT_MINT_SELECTOR}
VAULT_WITHDRAW_SELECTORS = {VAULT_WITHDRAW_SELECTOR, VAULT_REDEEM_SELECTOR}

PROTOCOL = "morpho"

# Well-known MetaMorpho vault addresses (Ethereum)
# These are the most popular vaults; the parser also uses a heuristic fallback
METAMORPHO_VAULTS: dict[str, list[str]] = {
    "ethereum": [
        "0x78fc2c2ed1a4cdb5402365934ae5648adad094d0",  # Steakhouse USDC
        "0xa0e430870c4604ccfc7b38ca7845b1ff653d0ff1",  # Steakhouse USDT
        "0x38989bba00bdf8181f4082995b3deae96163ac5d",  # Steakhouse ETH
        "0xd63070114470f685b75b74d60eec7c1113d33a3d",  # Gauntlet USDC Prime
        "0x4881ef0bf6d2365d3dd6499ccd7532bcdbce0658",  # Gauntlet WETH Prime
        "0xbeef01735c132ada46aa9aa4c54623caa92a64cb",  # Re7 WETH
        "0xbeef02e5e13584ab96848af90261f0c8ee04722a",  # Re7 wstETH
    ],
    "base": [
        "0xc1256ae5ff1cf2719d4937adb3bbcccab2e00a2c",  # Moonwell USDC
    ],
}


def _is_metamorpho_vault(chain: str, address: str) -> bool:
    """Check if address is a known MetaMorpho vault."""
    return address.lower() in METAMORPHO_VAULTS.get(chain, [])


class MorphoBlueParser(BaseParser):
    """Handles Morpho Blue lending operations."""

    PARSER_NAME = "MorphoBlueParser"
    ENTRY_TYPE = EntryType.DEPOSIT

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        to_addr = tx_data.get("to", "").lower()
        chain = tx_data.get("chain", "ethereum")
        pool = MORPHO_BLUE.get(chain, "")
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
        elif selector == REPAY_SELECTOR:
            entry_type = EntryType.REPAY
            splits.extend(self._handle_repay(tx_data, context, chain))
        elif selector == SUPPLY_COLLATERAL_SELECTOR:
            entry_type = EntryType.DEPOSIT
            splits.extend(self._handle_supply_collateral(tx_data, context, chain))
        elif selector == WITHDRAW_COLLATERAL_SELECTOR:
            entry_type = EntryType.WITHDRAWAL
            splits.extend(self._handle_withdraw_collateral(tx_data, context, chain))
        else:
            return self._make_result([])

        return self._make_result(splits, entry_type)

    def _handle_supply(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Supply: user sends token to Morpho. token_asset(-) / protocol_asset(+)."""
        wallet = tx_data.get("from", "").lower()
        transfer = context.pop_transfer(from_address=wallet, transfer_type="erc20")
        if transfer is None:
            return []
        qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals
        return make_deposit_splits(transfer.symbol, qty, PROTOCOL, chain)

    def _handle_withdraw(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Withdraw: Morpho sends token to user. protocol_asset(-) / token_asset(+)."""
        wallet = tx_data.get("from", "").lower()
        transfer = context.pop_transfer(to_address=wallet, transfer_type="erc20")
        if transfer is None:
            return []
        qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals
        return make_withdrawal_splits(transfer.symbol, qty, PROTOCOL, chain)

    def _handle_borrow(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Borrow: Morpho sends token to user. protocol_debt(-) / token_asset(+)."""
        wallet = tx_data.get("from", "").lower()
        transfer = context.pop_transfer(to_address=wallet, transfer_type="erc20")
        if transfer is None:
            return []
        qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals
        return make_borrow_splits(transfer.symbol, qty, PROTOCOL, chain)

    def _handle_repay(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """Repay: user sends token to Morpho. token_asset(-) / protocol_debt(+)."""
        wallet = tx_data.get("from", "").lower()
        transfer = context.pop_transfer(from_address=wallet, transfer_type="erc20")
        if transfer is None:
            return []
        qty = Decimal(str(transfer.value)) / Decimal(10) ** transfer.decimals
        return make_repay_splits(transfer.symbol, qty, PROTOCOL, chain)

    def _handle_supply_collateral(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """SupplyCollateral: same as supply — token to protocol."""
        return self._handle_supply(tx_data, context, chain)

    def _handle_withdraw_collateral(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """WithdrawCollateral: same as withdraw — protocol to token."""
        return self._handle_withdraw(tx_data, context, chain)


class MetaMorphoVaultParser(BaseParser):
    """Handles MetaMorpho vault (ERC-4626) deposit/withdraw."""

    PARSER_NAME = "MetaMorphoVaultParser"
    ENTRY_TYPE = EntryType.DEPOSIT

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool:
        to_addr = tx_data.get("to", "").lower()
        chain = tx_data.get("chain", "ethereum")
        return _is_metamorpho_vault(chain, to_addr)

    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult:
        chain = tx_data.get("chain", "ethereum")
        input_data = tx_data.get("input", "")
        selector = input_data[:10].lower() if len(input_data) >= 10 else ""

        splits = list(make_gas_splits(tx_data, chain, context))

        if selector in VAULT_DEPOSIT_SELECTORS:
            entry_type = EntryType.DEPOSIT
            splits.extend(self._handle_vault_deposit(tx_data, context, chain))
        elif selector in VAULT_WITHDRAW_SELECTORS:
            entry_type = EntryType.WITHDRAWAL
            splits.extend(self._handle_vault_withdraw(tx_data, context, chain))
        else:
            return self._make_result([])

        return self._make_result(splits, entry_type)

    def _handle_vault_deposit(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """ERC-4626 deposit: user sends underlying, receives vault shares."""
        wallet = tx_data.get("from", "").lower()
        vault = tx_data.get("to", "").lower()

        # Token sent to vault (underlying)
        transfer_out = context.pop_transfer(from_address=wallet, to_address=vault, transfer_type="erc20")
        if transfer_out is None:
            transfer_out = context.pop_transfer(from_address=wallet, transfer_type="erc20")
        if transfer_out is None:
            return []

        qty = Decimal(str(transfer_out.value)) / Decimal(10) ** transfer_out.decimals

        # Consume vault share mint (vault -> wallet or 0x0 -> wallet)
        context.pop_transfer(to_address=wallet, transfer_type="erc20")

        return make_deposit_splits(transfer_out.symbol, qty, PROTOCOL, chain)

    def _handle_vault_withdraw(self, tx_data: dict, context: TransactionContext, chain: str) -> list[ParsedSplit]:
        """ERC-4626 withdraw: user burns vault shares, receives underlying."""
        wallet = tx_data.get("from", "").lower()

        # Underlying token received
        transfer_in = context.pop_transfer(to_address=wallet, transfer_type="erc20")
        if transfer_in is None:
            return []

        qty = Decimal(str(transfer_in.value)) / Decimal(10) ** transfer_in.decimals

        # Consume vault share burn (wallet -> vault or wallet -> 0x0)
        context.pop_transfer(from_address=wallet, transfer_type="erc20")

        return make_withdrawal_splits(transfer_in.symbol, qty, PROTOCOL, chain)
