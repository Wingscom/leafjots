"""Bookkeeper — orchestrates TX parsing into double-entry journal entries."""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptotax.infra.price.service import PriceService

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.db.models.journal import JournalEntry, JournalSplit
from cryptotax.db.models.parse_error_record import ParseErrorRecord
from cryptotax.db.models.transaction import Transaction
from cryptotax.db.models.wallet import Wallet
from cryptotax.domain.enums import ParseErrorType, TxStatus
from cryptotax.accounting.account_mapper import AccountMapper
from cryptotax.parser.registry import ParserRegistry
from cryptotax.parser.utils.context import TransactionContext
from cryptotax.parser.utils.transfers import extract_all_transfers
from cryptotax.parser.utils.types import ParsedSplit, ParseResult

logger = logging.getLogger(__name__)


class Bookkeeper:
    """TX -> Parser -> AccountMapper -> JournalEntry + JournalSplits."""

    def __init__(
        self,
        session: AsyncSession,
        registry: ParserRegistry,
        price_service: "PriceService | None" = None,
    ) -> None:
        self._session = session
        self._registry = registry
        self._mapper = AccountMapper(session)
        self._price_service = price_service

    async def process_transaction(
        self, tx: Transaction, wallet: Wallet, entity_id: uuid.UUID
    ) -> JournalEntry | None:
        try:
            tx_data = json.loads(tx.tx_data or "{}")
            tx_data["chain"] = tx.chain

            # Build context
            transfers = extract_all_transfers(tx_data, tx.chain)
            wallet_addresses: set[str] = set()
            if wallet.wallet_type == "onchain":
                wallet_addresses = {wallet.address or ""}  # type: ignore[union-attr]
            context = TransactionContext(transfers, wallet_addresses)

            # Collect diagnostic data
            diagnostics = self._build_diagnostics(tx_data, context)

            # Select parser
            parsers = self._registry.get(tx.chain, tx.to_addr)
            result: ParseResult | None = None
            parsers_attempted: list[dict] = []

            for parser in parsers:
                matched = parser.can_parse(tx_data, context)
                entry = {
                    "parser": parser.PARSER_NAME,
                    "matched": matched,
                }
                if matched:
                    result = parser.parse(tx_data, context)
                    entry["produced_splits"] = result is not None and len(result.splits) > 0
                    parsers_attempted.append(entry)
                    break
                parsers_attempted.append(entry)

            diagnostics["parsers_attempted"] = parsers_attempted

            if result is None or len(result.splits) == 0:
                await self._record_error(
                    tx, ParseErrorType.UNKNOWN_TRANSACTION_INPUT_ERROR,
                    "No parser produced splits for this transaction",
                    diagnostic_data=diagnostics,
                )
                tx.status = TxStatus.ERROR.value
                tx.entry_type = "UNKNOWN"
                return None

            # Validate quantity balance per symbol (skip for multi-symbol ops like swaps/deposits)
            multi_symbol_types = {"SWAP", "DEPOSIT", "WITHDRAWAL", "BRIDGE", "LIQUIDATION", "MINT", "BURN"}
            if result.entry_type not in multi_symbol_types and not self._validate_balance(result.splits):
                await self._record_error(
                    tx, ParseErrorType.BALANCE_ERROR,
                    f"Splits don't sum to zero: {self._balance_summary(result.splits)}",
                    diagnostic_data=diagnostics,
                )
                tx.status = TxStatus.ERROR.value
                return None

            # Resolve accounts and create journal entry
            entry = JournalEntry(
                entity_id=entity_id,
                transaction_id=tx.id,
                entry_type=result.entry_type,
                description=f"{result.parser_name}: {tx.tx_hash[:10]}...",
                timestamp=datetime.fromtimestamp(tx.timestamp or 0, tz=UTC).replace(tzinfo=None),
            )
            self._session.add(entry)
            await self._session.flush()

            tx_timestamp = tx.timestamp or 0
            for ps in result.splits:
                account = await self._resolve_account(ps, wallet)
                value_usd, value_vnd = await self._price_split(ps.symbol, ps.quantity, tx_timestamp)
                split = JournalSplit(
                    journal_entry_id=entry.id,
                    account_id=account.id,
                    quantity=ps.quantity,
                    value_usd=value_usd,
                    value_vnd=value_vnd,
                )
                self._session.add(split)

            await self._session.flush()
            await self._session.refresh(entry, ["splits"])

            tx.status = TxStatus.PARSED.value
            tx.entry_type = result.entry_type
            return entry

        except Exception as e:
            logger.exception("Failed to parse TX %s", tx.tx_hash)
            diagnostics = {}
            try:
                diagnostics = self._build_diagnostics(
                    json.loads(tx.tx_data or "{}"),
                    None,
                )
            except Exception:
                pass
            await self._record_error(
                tx, ParseErrorType.TX_PARSE_ERROR,
                str(e), traceback.format_exc(),
                diagnostic_data=diagnostics,
            )
            tx.status = TxStatus.ERROR.value
            return None

    def _build_diagnostics(self, tx_data: dict, context: TransactionContext | None) -> dict:
        """Build diagnostic info for error recording."""
        input_data = tx_data.get("input", "")
        diag: dict = {
            "tx_hash": tx_data.get("hash", ""),
            "contract_address": tx_data.get("to", "").lower(),
            "function_selector": input_data[:10].lower() if len(input_data) >= 10 else "",
            "chain": tx_data.get("chain", ""),
        }
        if context is not None:
            diag["detected_transfers"] = [
                {"type": t.transfer_type, "symbol": t.symbol, "from": t.from_address, "to": t.to_address}
                for t in context.remaining_transfers()
            ]
            diag["detected_events"] = [
                {"event": e.event, "address": e.address}
                for e in context.remaining_events()
            ]
        return diag

    async def process_wallet(
        self, wallet: Wallet, entity_id: uuid.UUID
    ) -> dict[str, int]:
        """Process all LOADED transactions for a wallet."""
        stmt_result = await self._session.execute(
            select(Transaction)
            .where(
                Transaction.wallet_id == wallet.id,
                Transaction.status == TxStatus.LOADED.value,
            )
            .order_by(Transaction.block_number.asc())
        )
        txs = stmt_result.scalars().all()

        stats = {"processed": 0, "errors": 0, "total": len(txs)}
        for tx in txs:
            entry = await self.process_transaction(tx, wallet, entity_id)
            if entry:
                stats["processed"] += 1
            else:
                stats["errors"] += 1

        return stats

    def _validate_balance(self, splits: list[ParsedSplit]) -> bool:
        by_symbol: dict[str, Decimal] = defaultdict(Decimal)
        for s in splits:
            by_symbol[s.symbol] += s.quantity
        return all(total == Decimal(0) for total in by_symbol.values())

    def _balance_summary(self, splits: list[ParsedSplit]) -> str:
        by_symbol: dict[str, Decimal] = defaultdict(Decimal)
        for s in splits:
            by_symbol[s.symbol] += s.quantity
        return ", ".join(f"{sym}={total}" for sym, total in by_symbol.items() if total != Decimal(0))

    async def _resolve_account(self, ps: ParsedSplit, wallet: Wallet):
        """Map a ParsedSplit to a DB Account via AccountMapper."""
        subtype = ps.account_subtype
        params = ps.account_params

        if subtype == "native_asset":
            return await self._mapper.native_asset(wallet)
        elif subtype == "erc20_token":
            token_addr = params.get("token_address", "")
            return await self._mapper.erc20_token(wallet, token_addr, ps.symbol)
        elif subtype == "cex_asset":
            return await self._mapper.cex_asset(wallet, ps.symbol)
        elif subtype == "wallet_expense":
            if wallet.wallet_type == "cex":
                return await self._mapper.cex_expense(wallet, ps.symbol)
            return await self._mapper.gas_expense(wallet)
        elif subtype == "external_transfer":
            ext_addr = params.get("ext_address", "unknown")
            return await self._mapper.external_transfer(wallet, ps.symbol, ext_addr)
        elif subtype == "protocol_asset":
            protocol = params.get("protocol", "unknown")
            return await self._mapper.protocol_asset(wallet, protocol, ps.symbol)
        elif subtype == "protocol_debt":
            protocol = params.get("protocol", "unknown")
            return await self._mapper.protocol_debt(wallet, protocol, ps.symbol)
        elif subtype == "wallet_income":
            tag = params.get("tag", "Interest")
            return await self._mapper.income(wallet, ps.symbol, tag)
        else:
            return await self._mapper.native_asset(wallet)

    async def _price_split(
        self, symbol: str, quantity: Decimal, timestamp: int
    ) -> tuple[Decimal | None, Decimal | None]:
        if self._price_service is None:
            return None, None
        try:
            return await self._price_service.price_split(symbol, quantity, timestamp)
        except Exception:
            logger.warning("Price lookup failed for %s at %d", symbol, timestamp)
            return None, None

    async def _record_error(
        self,
        tx: Transaction,
        error_type: ParseErrorType,
        message: str,
        stack_trace: str | None = None,
        diagnostic_data: dict | None = None,
    ) -> None:
        error = ParseErrorRecord(
            transaction_id=tx.id,
            wallet_id=tx.wallet_id,
            error_type=error_type.value,
            message=message,
            stack_trace=stack_trace,
            diagnostic_data=json.dumps(diagnostic_data) if diagnostic_data else None,
        )
        self._session.add(error)
        await self._session.flush()
