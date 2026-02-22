"""Full pipeline test for seeded global DeFi entities.

Usage:
    PYTHONPATH=src python scripts/e2e_seed_entities.py

Runs the full pipeline for Uniswap Foundation and Compound Protocol:
  1. Load TXs from Etherscan (real API calls, limited block range)
  2. Parse all TXs via Bookkeeper (with price lookups)
  3. Calculate tax (FIFO + capital gains)
  4. Generate bangketoan.xlsx report

Mirrors e2e_test.py behaviour for the 2 seeded entities.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(name)s - %(message)s")
logger = logging.getLogger("e2e_seed_entities")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Limit block range per wallet to keep E2E fast (~7 days of Ethereum blocks)
ETH_BLOCK_RANGE = 200000  # ~2 months of Ethereum blocks — broad enough for most DeFi wallets

ENTITY_NAMES = ["DeFi Power User Alpha", "DeFi Power User Beta"]


def separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


async def main() -> None:
    from cryptotax.config import settings
    from cryptotax.db.session import build_engine, build_session_factory

    separator("E2E Pipeline — Seeded DeFi Entities")
    print(f"Database:  {settings.db_host}:{settings.db_port}/{settings.db_name}")
    print(f"Etherscan: {'configured' if settings.etherscan_api_key else 'NOT SET — TX loading will be skipped'}")
    print(f"CoinGecko: {'configured' if settings.coingecko_api_key else 'free tier (no key)'}")
    print()

    if not settings.etherscan_api_key:
        print("WARNING: ETHERSCAN_API_KEY not set. TX loading will be skipped.")

    engine = build_engine(settings.database_url, echo=False)
    session_factory = build_session_factory(engine)

    async with session_factory() as session:
        try:
            await run_pipeline(session, settings)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Pipeline failed")
            sys.exit(1)

    await engine.dispose()
    separator("Pipeline Complete")


async def run_pipeline(session, settings) -> None:
    from sqlalchemy import select

    from cryptotax.accounting.bookkeeper import Bookkeeper
    from cryptotax.accounting.tax_engine import TaxEngine
    from cryptotax.db.models.entity import Entity
    from cryptotax.db.repos.wallet_repo import WalletRepo
    from cryptotax.infra.http.rate_limited_client import RateLimitedClient
    from cryptotax.infra.price.coingecko import CoinGeckoProvider
    from cryptotax.infra.price.service import PriceService
    from cryptotax.parser.registry import build_default_registry
    from cryptotax.report.service import ReportService

    # -- Resolve entities --
    separator("Step 0: Resolve Entities")
    result = await session.execute(
        select(Entity)
        .where(Entity.name.in_(ENTITY_NAMES), Entity.deleted_at.is_(None))
        .order_by(Entity.name)
    )
    entities = list(result.scalars().all())

    if not entities:
        print("No seeded entities found. Run scripts/seed_entities.py first.")
        return

    for e in entities:
        print(f"  {e.name} ({e.base_currency})  id={e.id}")

    wallet_repo = WalletRepo(session)

    async with RateLimitedClient(rate_per_second=2.0) as http_client:

        coingecko = CoinGeckoProvider(http_client=http_client, api_key=settings.coingecko_api_key)
        price_service = PriceService(session=session, coingecko=coingecko)
        registry = build_default_registry()
        bookkeeper = Bookkeeper(session, registry, price_service=price_service)

        for entity in entities:
            separator(f"Entity: {entity.name}")

            wallets = await wallet_repo.get_all(entity.id)
            print(f"Wallets: {len(wallets)}")
            for w in wallets:
                print(f"  {w.label}  {getattr(w, 'address', '')}")

            # -- Step 1: Load TXs --
            print("\n--- Step 1: Load Transactions ---")
            total_loaded = 0

            if settings.etherscan_api_key:
                from cryptotax.infra.blockchain.evm.etherscan_client import EtherscanClient
                from cryptotax.infra.blockchain.evm.tx_loader import EVMTxLoader

                for wallet in wallets:
                    chain = getattr(wallet, "chain", None)
                    if chain != "ethereum":
                        print(f"  SKIP non-ethereum wallet: {wallet.label}")
                        continue

                    t0 = time.time()
                    try:
                        etherscan = EtherscanClient(
                            api_key=settings.etherscan_api_key, chain=chain, http_client=http_client,
                        )
                        latest_block = await etherscan.get_latest_block()
                        from_block = max(latest_block - ETH_BLOCK_RANGE, 0)
                        wallet.last_block_loaded = from_block
                        await session.flush()
                        print(f"  [{wallet.label}] block range: {from_block} -> {latest_block}")

                        loader = EVMTxLoader(session=session, etherscan=etherscan)
                        count = await loader.load_wallet(wallet)
                        elapsed = time.time() - t0
                        total_loaded += count
                        print(f"  [{wallet.label}] {count} TXs loaded in {elapsed:.1f}s")
                    except Exception as e:
                        elapsed = time.time() - t0
                        print(f"  [{wallet.label}] FAILED in {elapsed:.1f}s: {e}")
                        logger.exception("Failed to load wallet %s", wallet.label)
            else:
                print("  SKIP — no ETHERSCAN_API_KEY")

            print(f"\nTotal TXs loaded: {total_loaded}")
            await session.flush()

            # -- Step 2: Parse TXs --
            print("\n--- Step 2: Parse Transactions ---")
            total_stats = {"processed": 0, "errors": 0, "total": 0}
            for wallet in wallets:
                t0 = time.time()
                stats = await bookkeeper.process_wallet(wallet, entity.id)
                elapsed = time.time() - t0
                total_stats["processed"] += stats["processed"]
                total_stats["errors"] += stats["errors"]
                total_stats["total"] += stats["total"]
                pct = (stats["processed"] / stats["total"] * 100) if stats["total"] > 0 else 0
                print(
                    f"  [{wallet.label}] {stats['processed']}/{stats['total']} "
                    f"parsed ({pct:.0f}%), {stats['errors']} errors — {elapsed:.1f}s"
                )

            await session.flush()
            pct_total = (total_stats["processed"] / total_stats["total"] * 100) if total_stats["total"] > 0 else 0
            print(f"\nTotal: {total_stats['processed']}/{total_stats['total']} parsed ({pct_total:.0f}%), {total_stats['errors']} errors")

            # -- Step 3: Tax Calculation --
            print("\n--- Step 3: Tax Calculation ---")
            tax_engine = TaxEngine(session)
            start = datetime(2024, 1, 1)
            end = datetime(2026, 12, 31)
            try:
                summary = await tax_engine.calculate(entity.id, start, end)
                await session.flush()
                print(f"  Period:            {summary.period_start.date()} - {summary.period_end.date()}")
                print(f"  Realized Gains:    ${summary.total_realized_gain_usd:,.2f} USD")
                print(f"  Transfer Tax:      {summary.total_transfer_tax_vnd:,.0f} VND")
                print(f"  Closed Lots:       {len(summary.closed_lots)}")
                print(f"  Open Lots:         {len(summary.open_lots)}")
                print(f"  Taxable Transfers: {len(summary.taxable_transfers)}")
            except Exception as e:
                print(f"  Tax calculation error: {e}")
                logger.exception("Tax calculation error for %s", entity.name)

            # -- Step 4: Report --
            print("\n--- Step 4: Report Generation ---")
            report_service = ReportService(session)
            try:
                report = await report_service.generate(entity.id, start, end)
                await session.flush()
                print(f"  Status:   {report.status}")
                print(f"  Filename: {report.filename}")
                if report.error_message:
                    print(f"  Error:    {report.error_message}")
            except Exception as e:
                print(f"  Report generation failed: {e}")
                logger.exception("Report generation error for %s", entity.name)


if __name__ == "__main__":
    asyncio.run(main())
