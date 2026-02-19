"""Celery tasks for background processing."""

import asyncio
import logging

from cryptotax.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="sync_wallet", max_retries=2, default_retry_delay=30)
def sync_wallet_task(self, wallet_id: str) -> dict:
    """Load transactions for a wallet (on-chain or CEX).

    Bridges to async code via asyncio.run() — each task invocation
    creates its own engine + session (no shared state with FastAPI).
    """
    return asyncio.run(_sync_wallet_async(wallet_id))


async def _sync_wallet_async(wallet_id: str) -> dict:
    import uuid

    from cryptotax.config import settings
    from cryptotax.db.models.wallet import CEXWallet, OnChainWallet
    from cryptotax.db.repos.wallet_repo import WalletRepo
    from cryptotax.db.session import build_engine, build_session_factory
    from cryptotax.infra.http.rate_limited_client import RateLimitedClient

    engine = build_engine(settings.database_url, echo=False)
    session_factory = build_session_factory(engine)

    async with session_factory() as session:
        try:
            wallet_repo = WalletRepo(session)
            wallet = await wallet_repo.get_by_id(uuid.UUID(wallet_id))

            if wallet is None:
                logger.error("Wallet %s not found", wallet_id)
                return {"status": "error", "message": "Wallet not found"}

            async with RateLimitedClient(rate_per_second=5.0) as http_client:
                if isinstance(wallet, OnChainWallet):
                    count = await _sync_onchain(wallet, session, http_client, settings)
                elif isinstance(wallet, CEXWallet):
                    count = await _sync_cex(wallet, session, http_client, settings)
                else:
                    return {"status": "error", "message": f"Unknown wallet type: {wallet.wallet_type}"}

            await session.commit()
            logger.info("Synced wallet %s: %d new TXs", wallet_id, count)
            return {"status": "ok", "new_tx_count": count}
        except Exception as e:
            await session.rollback()
            logger.exception("Failed to sync wallet %s", wallet_id)
            return {"status": "error", "message": str(e)}
    await engine.dispose()


async def _sync_onchain(wallet, session, http_client, settings) -> int:
    """Sync an on-chain wallet (EVM or Solana)."""
    chain = wallet.chain or ""

    if chain == "solana":
        from cryptotax.infra.blockchain.solana.rpc_client import SolanaRPCClient
        from cryptotax.infra.blockchain.solana.tx_loader import SolanaTxLoader

        rpc_url = settings.solana_rpc_url
        rpc = SolanaRPCClient(rpc_url=rpc_url, http_client=http_client)
        loader = SolanaTxLoader(session=session, rpc=rpc)
    else:
        from cryptotax.infra.blockchain.evm.etherscan_client import EtherscanClient
        from cryptotax.infra.blockchain.evm.tx_loader import EVMTxLoader

        etherscan = EtherscanClient(
            api_key=settings.etherscan_api_key,
            chain=chain,
            http_client=http_client,
        )
        loader = EVMTxLoader(session=session, etherscan=etherscan)

    return await loader.load_wallet(wallet)


async def _sync_cex(wallet, session, http_client, settings) -> int:
    """Sync a CEX wallet (e.g. Binance)."""
    from cryptotax.infra.cex.binance_client import BinanceClient
    from cryptotax.infra.cex.binance_loader import BinanceLoader
    from cryptotax.infra.cex.crypto import decrypt_value

    api_key = decrypt_value(wallet.api_key_encrypted, settings.encryption_key) if wallet.api_key_encrypted else ""
    api_secret = decrypt_value(wallet.api_secret_encrypted, settings.encryption_key) if wallet.api_secret_encrypted else ""

    client = BinanceClient(api_key=api_key, api_secret=api_secret, http_client=http_client)
    loader = BinanceLoader(session=session, client=client)
    return await loader.load_wallet(wallet)
