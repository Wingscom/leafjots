"""Load + parse + tax + report for dripgroup.eth from Jan 1 2026.

Usage:
    PYTHONPATH=src python scripts/run_dripgroup.py
"""

import asyncio
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(name)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

ENTITY_NAME = "dripgroup.eth"
JAN_2026_BLOCK = 21525000  # ~Jan 1 2026 00:00 UTC


async def main() -> None:
    from sqlalchemy import select

    from cryptotax.accounting.bookkeeper import Bookkeeper
    from cryptotax.accounting.tax_engine import TaxEngine
    from cryptotax.config import settings
    from cryptotax.db.models.entity import Entity
    from cryptotax.db.repos.wallet_repo import WalletRepo
    from cryptotax.db.session import build_engine, build_session_factory
    from cryptotax.infra.blockchain.evm.etherscan_client import EtherscanClient
    from cryptotax.infra.blockchain.evm.tx_loader import EVMTxLoader
    from cryptotax.infra.http.rate_limited_client import RateLimitedClient
    from cryptotax.infra.price.coingecko import CoinGeckoProvider
    from cryptotax.infra.price.service import PriceService
    from cryptotax.parser.registry import build_default_registry
    from cryptotax.report.service import ReportService

    engine = build_engine(settings.database_url, echo=False)
    sf = build_session_factory(engine)

    async with sf() as session:
        result = await session.execute(select(Entity).where(Entity.name == ENTITY_NAME))
        entity = result.scalar_one()
        wr = WalletRepo(session)
        wallets = await wr.get_all(entity.id)
        print(f"Entity: {entity.name}  ({entity.base_currency})  wallets: {len(wallets)}")

        async with RateLimitedClient(rate_per_second=2.0) as http:

            # --- Step 1: Load TXs from Jan 2026 ---
            print(f"\n--- Step 1: Load TXs (from block {JAN_2026_BLOCK} = ~Jan 1 2026) ---")
            for w in wallets:
                etherscan = EtherscanClient(
                    api_key=settings.etherscan_api_key, chain="ethereum", http_client=http
                )
                latest = await etherscan.get_latest_block()
                w.last_block_loaded = JAN_2026_BLOCK
                await session.flush()
                print(f"  [{w.label}]  blocks: {JAN_2026_BLOCK} -> {latest}  (~{latest - JAN_2026_BLOCK:,})")
                t0 = time.time()
                loader = EVMTxLoader(session=session, etherscan=etherscan)
                count = await loader.load_wallet(w)
                print(f"  Loaded: {count} TXs  ({time.time() - t0:.1f}s)")

            await session.flush()

            # --- Step 2: Parse ---
            print("\n--- Step 2: Parse ---")
            cg = CoinGeckoProvider(http_client=http, api_key=settings.coingecko_api_key)
            ps = PriceService(session=session, coingecko=cg)
            registry = build_default_registry()
            bk = Bookkeeper(session, registry, price_service=ps)
            for w in wallets:
                t0 = time.time()
                stats = await bk.process_wallet(w, entity.id)
                pct = stats["processed"] / stats["total"] * 100 if stats["total"] else 0
                print(
                    f"  [{w.label}]  {stats['processed']}/{stats['total']} parsed"
                    f" ({pct:.0f}%), {stats['errors']} errors  ({time.time() - t0:.1f}s)"
                )
            await session.flush()

            # --- Step 3: Tax ---
            print("\n--- Step 3: Tax Calculation (2026) ---")
            tax = TaxEngine(session)
            start = datetime(2026, 1, 1)
            end = datetime(2026, 12, 31)
            try:
                summary = await tax.calculate(entity.id, start, end)
                await session.flush()
                print(f"  Realized Gains:    ${summary.total_realized_gain_usd:,.2f}")
                print(f"  Transfer Tax:      {summary.total_transfer_tax_vnd:,.0f} VND")
                print(f"  Closed Lots:       {len(summary.closed_lots)}")
                print(f"  Open Lots:         {len(summary.open_lots)}")
                print(f"  Taxable Transfers: {len(summary.taxable_transfers)}")
            except Exception as e:
                print(f"  ERROR: {e}")

            # --- Step 4: Report ---
            print("\n--- Step 4: Report ---")
            rs = ReportService(session)
            try:
                report = await rs.generate(entity.id, start, end)
                await session.flush()
                print(f"  Status:   {report.status}")
                print(f"  Filename: {report.filename}")
                if report.error_message:
                    print(f"  Error:    {report.error_message}")
            except Exception as e:
                print(f"  ERROR: {e}")

        await session.commit()

    await engine.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
