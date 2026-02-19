"""AccountMapper — get-or-create accounts by hierarchical label key."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.account import Account
from cryptotax.db.models.wallet import Wallet
from cryptotax.domain.enums import AccountType
from cryptotax.parser.utils.gas import native_symbol


def _wallet_prefix(wallet: Wallet) -> str:
    """Build a unique key prefix for any wallet type."""
    chain = getattr(wallet, "chain", None)
    address = getattr(wallet, "address", None)
    exchange = getattr(wallet, "exchange", None)
    if chain and address:
        return f"{chain}:{address}"
    if exchange:
        return f"cex:{exchange}:{wallet.id}"
    return f"wallet:{wallet.id}"


class AccountMapper:
    """Lazily creates/retrieves accounts. Caches per session to avoid N+1."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._cache: dict[str, Account] = {}

    async def native_asset(self, wallet: Wallet) -> Account:
        chain = getattr(wallet, "chain", None) or "ethereum"
        symbol = native_symbol(chain)
        key = f"{_wallet_prefix(wallet)}:native_asset"
        return await self._get_or_create(key, dict(
            wallet_id=wallet.id,
            account_type=AccountType.ASSET.value,
            subtype="native_asset",
            symbol=symbol,
        ))

    async def erc20_token(self, wallet: Wallet, token_address: str, symbol: str) -> Account:
        key = f"{_wallet_prefix(wallet)}:erc20:{symbol}:{token_address}"
        return await self._get_or_create(key, dict(
            wallet_id=wallet.id,
            account_type=AccountType.ASSET.value,
            subtype="erc20_token",
            symbol=symbol,
            token_address=token_address,
        ))

    async def gas_expense(self, wallet: Wallet) -> Account:
        chain = getattr(wallet, "chain", None) or "ethereum"
        symbol = native_symbol(chain)
        key = f"{_wallet_prefix(wallet)}:expense:gas"
        return await self._get_or_create(key, dict(
            wallet_id=wallet.id,
            account_type=AccountType.EXPENSE.value,
            subtype="wallet_expense",
            symbol=symbol,
        ))

    async def cex_expense(self, wallet: Wallet, symbol: str) -> Account:
        """CEX fee expense account for a specific asset."""
        key = f"{_wallet_prefix(wallet)}:expense:{symbol}"
        return await self._get_or_create(key, dict(
            wallet_id=wallet.id,
            account_type=AccountType.EXPENSE.value,
            subtype="wallet_expense",
            symbol=symbol,
        ))

    async def external_transfer(self, wallet: Wallet, symbol: str, ext_address: str) -> Account:
        key = f"{_wallet_prefix(wallet)}:external:{symbol}:{ext_address}"
        return await self._get_or_create(key, dict(
            wallet_id=wallet.id,
            account_type=AccountType.ASSET.value,
            subtype="external_transfer",
            symbol=symbol,
            token_address=ext_address,
        ))

    async def cex_asset(self, wallet: Wallet, symbol: str) -> Account:
        """CEX asset holding account (e.g. BTC on Binance)."""
        key = f"{_wallet_prefix(wallet)}:asset:{symbol}"
        return await self._get_or_create(key, dict(
            wallet_id=wallet.id,
            account_type=AccountType.ASSET.value,
            subtype="cex_asset",
            symbol=symbol,
        ))

    async def protocol_asset(self, wallet: Wallet, protocol: str, symbol: str) -> Account:
        key = f"{_wallet_prefix(wallet)}:protocol:{protocol}:asset:{symbol}"
        return await self._get_or_create(key, dict(
            wallet_id=wallet.id,
            account_type=AccountType.ASSET.value,
            subtype="protocol_asset",
            symbol=symbol,
            protocol=protocol,
            balance_type="supply",
        ))

    async def protocol_debt(self, wallet: Wallet, protocol: str, symbol: str) -> Account:
        key = f"{_wallet_prefix(wallet)}:protocol:{protocol}:debt:{symbol}"
        return await self._get_or_create(key, dict(
            wallet_id=wallet.id,
            account_type=AccountType.LIABILITY.value,
            subtype="protocol_debt",
            symbol=symbol,
            protocol=protocol,
            balance_type="borrow",
        ))

    async def income(self, wallet: Wallet, symbol: str, tag: str = "Interest") -> Account:
        key = f"{_wallet_prefix(wallet)}:income:{tag}:{symbol}"
        return await self._get_or_create(key, dict(
            wallet_id=wallet.id,
            account_type=AccountType.INCOME.value,
            subtype="wallet_income",
            symbol=symbol,
        ))

    async def _get_or_create(self, unique_key: str, attrs: dict) -> Account:
        if unique_key in self._cache:
            return self._cache[unique_key]

        result = await self._session.execute(
            select(Account).where(Account.label == unique_key)
        )
        account = result.scalar_one_or_none()

        if account is None:
            account = Account(label=unique_key, **attrs)
            self._session.add(account)
            await self._session.flush()

        self._cache[unique_key] = account
        return account
