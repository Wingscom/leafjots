"""Integration tests for multi-chain DB support — Solana + EVM column widths."""

from cryptotax.db.models.entity import Entity
from cryptotax.db.models.transaction import Transaction
from cryptotax.db.models.wallet import OnChainWallet


class TestSolanaWallet:
    async def test_create_solana_wallet(self, session):
        entity = Entity(name="solana_test")
        session.add(entity)
        await session.flush()

        wallet = OnChainWallet(
            entity_id=entity.id,
            chain="solana",
            address="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        )
        session.add(wallet)
        await session.flush()

        assert wallet.id is not None
        assert wallet.chain == "solana"
        assert len(wallet.address) == 44  # Solana base58 address

    async def test_solana_address_44_chars(self, session):
        """Solana addresses are base58-encoded, ~44 chars."""
        entity = Entity(name="sol_addr")
        session.add(entity)
        await session.flush()

        addr = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC mint (44 chars)
        wallet = OnChainWallet(entity_id=entity.id, chain="solana", address=addr)
        session.add(wallet)
        await session.flush()

        assert wallet.address == addr


class TestSolanaTransaction:
    async def test_88_char_tx_hash(self, session):
        """Solana signatures are base58, ~87-88 chars."""
        entity = Entity(name="sol_tx")
        session.add(entity)
        await session.flush()

        wallet = OnChainWallet(entity_id=entity.id, chain="solana", address="SomeAddr")
        session.add(wallet)
        await session.flush()

        sig = "4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi" + "ABCDEFGHIJ" * 4 + "ABCDE"
        # Ensure it's ~88 chars
        sig = sig[:88]

        tx = Transaction(
            wallet_id=wallet.id,
            chain="solana",
            tx_hash=sig,
            block_number=123456,
            timestamp=1700000000,
            from_addr="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            to_addr="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            gas_used=5000,
        )
        session.add(tx)
        await session.flush()

        assert tx.id is not None
        assert len(tx.tx_hash) == 88
        assert tx.chain == "solana"

    async def test_44_char_addresses(self, session):
        """Solana from_addr and to_addr should support 44-char base58 addresses."""
        entity = Entity(name="sol_addr_tx")
        session.add(entity)
        await session.flush()

        wallet = OnChainWallet(entity_id=entity.id, chain="solana", address="SomeAddr")
        session.add(wallet)
        await session.flush()

        from_addr = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"  # 44 chars
        to_addr = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # 44 chars

        tx = Transaction(
            wallet_id=wallet.id,
            chain="solana",
            tx_hash="shortSig123",
            from_addr=from_addr,
            to_addr=to_addr,
        )
        session.add(tx)
        await session.flush()

        assert tx.from_addr == from_addr
        assert tx.to_addr == to_addr
        assert len(tx.from_addr) == 44
        assert len(tx.to_addr) == 44

    async def test_evm_still_works(self, session):
        """EVM transactions should still work with widened columns."""
        entity = Entity(name="evm_tx")
        session.add(entity)
        await session.flush()

        wallet = OnChainWallet(entity_id=entity.id, chain="ethereum", address="0x" + "a" * 40)
        session.add(wallet)
        await session.flush()

        tx = Transaction(
            wallet_id=wallet.id,
            chain="ethereum",
            tx_hash="0x" + "b" * 64,  # 66 chars (EVM)
            from_addr="0x" + "c" * 40,  # 42 chars
            to_addr="0x" + "d" * 40,
            block_number=12345,
        )
        session.add(tx)
        await session.flush()

        assert len(tx.tx_hash) == 66
        assert len(tx.from_addr) == 42


class TestChainEnum:
    def test_solana_in_chain_enum(self):
        from cryptotax.domain.enums.chain import Chain
        assert Chain.SOLANA.value == "solana"

    def test_all_evm_chains_still_exist(self):
        from cryptotax.domain.enums.chain import Chain
        expected = ["ethereum", "arbitrum", "optimism", "polygon", "base", "bsc", "avalanche"]
        for chain_val in expected:
            assert chain_val in [c.value for c in Chain]
