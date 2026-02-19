"""End-to-end test with real blockchain data.

Usage:
    PYTHONPATH=src python scripts/e2e_test.py

Runs the full pipeline:
  1. Create entity + wallets (Ethereum + Solana)
  2. Load TXs from Etherscan / Solana RPC (real API calls)
  3. Parse all TXs via Bookkeeper (with price lookups)
  4. Calculate tax (FIFO + 0.1% VN transfer tax)
  5. Generate bangketoan.xlsx report
"""

import asyncio
import logging
import sys
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(name)s - %(message)s")
logger = logging.getLogger("e2e_test")

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# -- Test wallet addresses (public, well-known) --
# Vitalik's address - well-known public DeFi wallet
# We limit to a small block range (~5000 blocks ~ 17 hours) to keep it fast
ETH_TEST_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
ETH_TEST_LABEL = "E2E Test - Ethereum DeFi (vitalik.eth)"

# Solana wallet with some swap activity
SOL_TEST_ADDRESS = "DRpbCBMxVnDK7maPM5tGv6MvB3v1sRMC86PZ8okm21hy"
SOL_TEST_LABEL = "E2E Test - Solana"

# Block range limit for EVM - only load recent TXs to keep E2E fast
ETH_BLOCK_RANGE = 50000  # ~7 days of Ethereum blocks


def separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


async def main() -> None:
    from cryptotax.config import settings
    from cryptotax.db.session import build_engine, build_session_factory

    separator("E2E Test - LeafJots")
    print(f"Database:     {settings.db_host}:{settings.db_port}/{settings.db_name}")
    print(f"Etherscan:    {'configured' if settings.etherscan_api_key else 'NOT SET'}")
    print(f"CoinGecko:    {'configured' if settings.coingecko_api_key else 'free tier (no key)'}")
    print(f"Solana RPC:   {settings.solana_rpc_url}")
    print()

    engine = build_engine(settings.database_url, echo=False)
    session_factory = build_session_factory(engine)

    async with session_factory() as session:
        try:
            await run_pipeline(session, settings)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("E2E test failed")
            sys.exit(1)

    await engine.dispose()
    separator("E2E Test Complete")


async def run_pipeline(session, settings) -> None:
    from cryptotax.db.repos.entity_repo import EntityRepo
    from cryptotax.db.repos.wallet_repo import WalletRepo
    from cryptotax.domain.enums import Chain
    from cryptotax.infra.http.rate_limited_client import RateLimitedClient

    # -- Step 1: Entity + Wallets --
    separator("Step 1: Create Entity + Wallets")

    entity_repo = EntityRepo(session)
    wallet_repo = WalletRepo(session)
    entity = await entity_repo.get_or_create_default()
    await session.flush()
    print(f"Entity: {entity.name} (id={entity.id})")

    wallets = []
    # Use slower rate for Solana public RPC (strict rate limits)
    async with RateLimitedClient(rate_per_second=2.0) as http_client:

        # Ethereum wallet
        if settings.etherscan_api_key:
            eth_wallet = await wallet_repo.get_by_chain_and_address(entity.id, Chain.ETHEREUM, ETH_TEST_ADDRESS)
            if eth_wallet is None:
                eth_wallet = await wallet_repo.create(
                    entity_id=entity.id, chain=Chain.ETHEREUM, address=ETH_TEST_ADDRESS, label=ETH_TEST_LABEL,
                )
                await session.flush()
                print(f"Created Ethereum wallet: {ETH_TEST_ADDRESS[:10]}...")
            else:
                print(f"Reusing Ethereum wallet: {ETH_TEST_ADDRESS[:10]}...")
            wallets.append(eth_wallet)
        else:
            print("SKIP Ethereum - no ETHERSCAN_API_KEY set")

        # Solana wallet (requires Helius API key - public RPC rate-limits too aggressively)
        if settings.helius_api_key:
            sol_wallet = await wallet_repo.get_by_chain_and_address(entity.id, Chain.SOLANA, SOL_TEST_ADDRESS)
            if sol_wallet is None:
                sol_wallet = await wallet_repo.create(
                    entity_id=entity.id, chain=Chain.SOLANA, address=SOL_TEST_ADDRESS, label=SOL_TEST_LABEL,
                )
                await session.flush()
                print(f"Created Solana wallet: {SOL_TEST_ADDRESS[:10]}...")
            else:
                print(f"Reusing Solana wallet: {SOL_TEST_ADDRESS[:10]}...")
            wallets.append(sol_wallet)
        else:
            print("SKIP Solana - no HELIUS_API_KEY (public RPC too rate-limited)")

        print(f"\nTotal wallets: {len(wallets)}")

        # -- Step 2: Load Transactions --
        separator("Step 2: Load Transactions (real API calls)")

        total_loaded = 0
        for wallet in wallets:
            t0 = time.time()
            try:
                count = await load_wallet_txs(session, wallet, http_client, settings)
                elapsed = time.time() - t0
                total_loaded += count
                print(f"  [{wallet.chain}] {count} new TXs loaded in {elapsed:.1f}s")
            except Exception as e:
                elapsed = time.time() - t0
                print(f"  [{wallet.chain}] FAILED in {elapsed:.1f}s: {e}")
                logger.exception("Failed to load %s wallet", wallet.chain)

        print(f"\nTotal new TXs loaded: {total_loaded}")
        await session.flush()

        # -- Step 3: Parse Transactions --
        separator("Step 3: Parse Transactions")

        from cryptotax.accounting.bookkeeper import Bookkeeper
        from cryptotax.infra.price.coingecko import CoinGeckoProvider
        from cryptotax.infra.price.service import PriceService
        from cryptotax.parser.registry import build_default_registry

        coingecko = CoinGeckoProvider(http_client=http_client, api_key=settings.coingecko_api_key)
        price_service = PriceService(session=session, coingecko=coingecko)
        registry = build_default_registry()
        bookkeeper = Bookkeeper(session, registry, price_service=price_service)

        total_stats = {"processed": 0, "errors": 0, "total": 0}
        for wallet in wallets:
            t0 = time.time()
            stats = await bookkeeper.process_wallet(wallet, entity.id)
            elapsed = time.time() - t0
            total_stats["processed"] += stats["processed"]
            total_stats["errors"] += stats["errors"]
            total_stats["total"] += stats["total"]
            pct = (stats["processed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"  [{wallet.chain}] {stats['processed']}/{stats['total']} parsed ({pct:.0f}%), {stats['errors']} errors - {elapsed:.1f}s")

        await session.flush()

        pct_total = (total_stats["processed"] / total_stats["total"] * 100) if total_stats["total"] > 0 else 0
        print(f"\nTotal: {total_stats['processed']}/{total_stats['total']} parsed ({pct_total:.0f}%), {total_stats['errors']} errors")

    # -- Step 4: Tax Calculation --
    separator("Step 4: Tax Calculation (FIFO + capital gains)")

    from cryptotax.accounting.tax_engine import TaxEngine

    tax_engine = TaxEngine(session)
    # Use naive datetimes (PostgreSQL TIMESTAMP WITHOUT TIME ZONE)
    start = datetime(2024, 1, 1)
    end = datetime(2026, 12, 31)

    try:
        summary = await tax_engine.calculate(entity.id, start, end)
        await session.flush()

        print(f"Period:              {summary.period_start.date()} - {summary.period_end.date()}")
        print(f"Realized Gains:      ${summary.total_realized_gain_usd:,.2f} USD")
        print(f"Transfer Tax:        {summary.total_transfer_tax_vnd:,.0f} VND")
        print(f"Exempt Value:        {summary.total_exempt_vnd:,.0f} VND")
        print(f"Closed Lots:         {len(summary.closed_lots)}")
        print(f"Open Lots:           {len(summary.open_lots)}")
        print(f"Taxable Transfers:   {len(summary.taxable_transfers)}")
    except Exception as e:
        print(f"Tax calculation error: {e}")
        logger.exception("Tax calculation error")

    # -- Step 5: Report Generation --
    separator("Step 5: Report Generation (bangketoan.xlsx)")

    from cryptotax.report.service import ReportService

    report_service = ReportService(session)
    try:
        report = await report_service.generate(entity.id, start, end)
        await session.flush()
        print(f"Report status:   {report.status}")
        print(f"Filename:        {report.filename}")
        if report.error_message:
            print(f"Error:           {report.error_message}")
    except Exception as e:
        print(f"Report generation failed: {e}")
        logger.exception("Report generation error")

    # -- Summary --
    separator("Pipeline Summary")

    from sqlalchemy import func, select
    from cryptotax.db.models.transaction import Transaction
    from cryptotax.db.models.journal import JournalEntry, JournalSplit
    from cryptotax.db.models.account import Account

    tx_count = (await session.execute(select(func.count(Transaction.id)))).scalar() or 0
    je_count = (await session.execute(select(func.count(JournalEntry.id)))).scalar() or 0
    js_count = (await session.execute(select(func.count(JournalSplit.id)))).scalar() or 0
    acc_count = (await session.execute(select(func.count(Account.id)))).scalar() or 0

    print(f"Transactions:    {tx_count}")
    print(f"Journal Entries: {je_count}")
    print(f"Journal Splits:  {js_count}")
    print(f"Accounts:        {acc_count}")


async def load_wallet_txs(session, wallet, http_client, settings) -> int:
    """Load transactions for a wallet using the appropriate loader."""
    chain = wallet.chain or ""

    if chain == "solana":
        from cryptotax.infra.blockchain.solana.rpc_client import SolanaRPCClient
        from cryptotax.infra.blockchain.solana.tx_loader import SolanaTxLoader

        rpc = SolanaRPCClient(rpc_url=settings.solana_rpc_url, http_client=http_client)
        loader = SolanaTxLoader(session=session, rpc=rpc)
        return await loader.load_wallet(wallet)
    else:
        from cryptotax.infra.blockchain.evm.etherscan_client import EtherscanClient
        from cryptotax.infra.blockchain.evm.tx_loader import EVMTxLoader

        etherscan = EtherscanClient(
            api_key=settings.etherscan_api_key, chain=chain, http_client=http_client,
        )
        # For E2E test: limit block range to keep it fast
        latest_block = await etherscan.get_latest_block()
        from_block = max(latest_block - ETH_BLOCK_RANGE, 0)
        # Force wallet's last_block_loaded so loader only fetches recent range
        wallet.last_block_loaded = from_block
        await session.flush()
        print(f"    EVM block range: {from_block} -> {latest_block} ({ETH_BLOCK_RANGE} blocks)")

        loader = EVMTxLoader(session=session, etherscan=etherscan)
        return await loader.load_wallet(wallet)


if __name__ == "__main__":
    asyncio.run(main())
