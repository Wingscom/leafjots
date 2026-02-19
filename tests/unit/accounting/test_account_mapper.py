from cryptotax.accounting.account_mapper import AccountMapper
from cryptotax.db.models.entity import Entity
from cryptotax.db.models.wallet import OnChainWallet


async def _create_wallet(session) -> OnChainWallet:
    entity = Entity(name="Test", base_currency="VND")
    session.add(entity)
    await session.flush()
    wallet = OnChainWallet(entity_id=entity.id, chain="ethereum", address="0xabc")
    session.add(wallet)
    await session.flush()
    return wallet


class TestAccountMapper:
    async def test_native_asset_creates_account(self, session):
        wallet = await _create_wallet(session)
        mapper = AccountMapper(session)
        account = await mapper.native_asset(wallet)

        assert account is not None
        assert account.account_type == "ASSET"
        assert account.subtype == "native_asset"
        assert account.symbol == "ETH"
        assert account.label == "ethereum:0xabc:native_asset"

    async def test_native_asset_is_cached(self, session):
        wallet = await _create_wallet(session)
        mapper = AccountMapper(session)

        a1 = await mapper.native_asset(wallet)
        a2 = await mapper.native_asset(wallet)
        assert a1.id == a2.id  # Same instance from cache

    async def test_gas_expense_creates_expense_account(self, session):
        wallet = await _create_wallet(session)
        mapper = AccountMapper(session)
        account = await mapper.gas_expense(wallet)

        assert account.account_type == "EXPENSE"
        assert account.subtype == "wallet_expense"
        assert account.symbol == "ETH"

    async def test_erc20_token_creates_asset(self, session):
        wallet = await _create_wallet(session)
        mapper = AccountMapper(session)
        account = await mapper.erc20_token(wallet, "0xusdc", "USDC")

        assert account.account_type == "ASSET"
        assert account.subtype == "erc20_token"
        assert account.symbol == "USDC"
        assert account.token_address == "0xusdc"

    async def test_external_transfer_creates_account(self, session):
        wallet = await _create_wallet(session)
        mapper = AccountMapper(session)
        account = await mapper.external_transfer(wallet, "ETH", "0xdead")

        assert account.account_type == "ASSET"
        assert account.subtype == "external_transfer"
        assert "0xdead" in account.label

    async def test_protocol_asset_creates_supply(self, session):
        wallet = await _create_wallet(session)
        mapper = AccountMapper(session)
        account = await mapper.protocol_asset(wallet, "aave", "USDC")

        assert account.account_type == "ASSET"
        assert account.subtype == "protocol_asset"
        assert account.protocol == "aave"
        assert account.balance_type == "supply"

    async def test_protocol_debt_creates_liability(self, session):
        wallet = await _create_wallet(session)
        mapper = AccountMapper(session)
        account = await mapper.protocol_debt(wallet, "aave", "DAI")

        assert account.account_type == "LIABILITY"
        assert account.subtype == "protocol_debt"
        assert account.protocol == "aave"
        assert account.balance_type == "borrow"

    async def test_different_wallets_different_accounts(self, session):
        entity = Entity(name="Test", base_currency="VND")
        session.add(entity)
        await session.flush()

        w1 = OnChainWallet(entity_id=entity.id, chain="ethereum", address="0x111")
        w2 = OnChainWallet(entity_id=entity.id, chain="ethereum", address="0x222")
        session.add_all([w1, w2])
        await session.flush()

        mapper = AccountMapper(session)
        a1 = await mapper.native_asset(w1)
        a2 = await mapper.native_asset(w2)
        assert a1.id != a2.id

    async def test_persists_to_db_and_reloads(self, session):
        wallet = await _create_wallet(session)

        # First mapper creates the account
        mapper1 = AccountMapper(session)
        a1 = await mapper1.native_asset(wallet)

        # Second mapper (empty cache) should find existing in DB
        mapper2 = AccountMapper(session)
        a2 = await mapper2.native_asset(wallet)
        assert a1.id == a2.id
