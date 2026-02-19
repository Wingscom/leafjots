"""Binance CSV Transaction History parser.

Parses CsvImportRow records (from Phase 8 upload) into double-entry
journal entries. Groups multi-row transactions by UTC_Time and dispatches
to operation-specific handlers.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cryptotax.accounting.account_mapper import AccountMapper
from cryptotax.db.models.csv_import import CsvImport, CsvImportRow
from cryptotax.db.models.journal import JournalEntry, JournalSplit
from cryptotax.db.models.wallet import Wallet
from cryptotax.parser.utils.types import ParsedSplit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Operation constants
# ---------------------------------------------------------------------------

TRADE_OPS = frozenset({
    "Transaction Buy",
    "Transaction Spend",
    "Transaction Fee",
    "Transaction Sold",
    "Transaction Revenue",
})

CORE_OPS = TRADE_OPS | frozenset({
    "Binance Convert",
    "Deposit",
    "Withdraw",
    "P2P Trading",
})

EARN_OPS = frozenset({
    "Simple Earn Flexible Subscription",
    "Simple Earn Flexible Redemption",
    "Simple Earn Locked Subscription",
    "Simple Earn Flexible Interest",
    "Simple Earn Locked Rewards",
})

FUTURES_OPS = frozenset({
    "Fee",
    "Funding Fee",
    "Realized Profit and Loss",
})

MARGIN_OPS = frozenset({
    "Isolated Margin Loan",
    "Isolated Margin Liquidation - Forced Repayment",
    "Cross Margin Liquidation - Small Assets Takeover",
})

LOAN_OPS = frozenset({
    "Flexible Loan - Collateral Transfer",
    "Flexible Loan - Lending",
    "Flexible Loan - Repayment",
})

SPECIAL_TOKEN_OPS = frozenset({
    "RWUSD - Subscription",
    "RWUSD - Distribution",
    "RWUSD - Redemption",
    "BFUSD Subscription",
    "BFUSD Daily Reward",
    "WBETH2.0 - Staking",
})

TRANSFER_FUND_OPS = frozenset({
    "Transfer Funds to Spot",
    "Transfer Funds to Funding Wallet",
})

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ParseStats:
    total: int = 0
    parsed: int = 0
    errors: int = 0
    skipped: int = 0


@dataclass
class ParsedEntry:
    splits: list[ParsedSplit] = field(default_factory=list)
    entry_type: str = "UNKNOWN"
    source_rows: list[CsvImportRow] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class BinanceCsvParser:
    """Parse Binance Transaction History CSV rows into journal entries."""

    def __init__(
        self,
        session: AsyncSession,
        entity_id: uuid.UUID,
        wallet: Wallet,
    ) -> None:
        self._session = session
        self._entity_id = entity_id
        self._wallet = wallet
        self._mapper = AccountMapper(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def parse_import(self, csv_import: CsvImport) -> ParseStats:
        """Parse all pending rows in an import. Returns stats."""
        rows = await self._get_pending_rows(csv_import.id)
        groups = self._group_by_timestamp(rows)

        stats = ParseStats(total=len(rows))
        for utc_time, group_rows in groups.items():
            try:
                entries = self._parse_group(utc_time, group_rows)
                for entry_data in entries:
                    journal_entry = await self._create_journal_entry(entry_data, utc_time)
                    for row in entry_data.source_rows:
                        row.status = "parsed"
                        row.journal_entry_id = journal_entry.id
                    stats.parsed += len(entry_data.source_rows)
            except Exception as exc:
                logger.warning("Error parsing group at %s: %s", utc_time, exc)
                for row in group_rows:
                    if row.status == "pending":
                        row.status = "error"
                        row.error_message = str(exc)
                        stats.errors += 1

        # Count skipped rows (set inside _parse_group for unknown ops)
        for _utc_time, group_rows in groups.items():
            for row in group_rows:
                if row.status == "skipped":
                    stats.skipped += 1

        # Flush all row status changes (parsed, error, skipped)
        await self._session.flush()

        return stats

    # ------------------------------------------------------------------
    # Row loading & grouping
    # ------------------------------------------------------------------

    async def _get_pending_rows(self, import_id: uuid.UUID) -> list[CsvImportRow]:
        result = await self._session.execute(
            select(CsvImportRow)
            .where(
                CsvImportRow.import_id == import_id,
                CsvImportRow.status == "pending",
            )
            .order_by(CsvImportRow.row_number)
        )
        return list(result.scalars().all())

    @staticmethod
    def _group_by_timestamp(rows: list[CsvImportRow]) -> dict[str, list[CsvImportRow]]:
        """Group rows by UTC_Time string. Same timestamp = one logical transaction."""
        groups: dict[str, list[CsvImportRow]] = {}
        for row in rows:
            groups.setdefault(row.utc_time, []).append(row)
        return groups

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _parse_group(self, utc_time: str, rows: list[CsvImportRow]) -> list[ParsedEntry]:
        """Split mixed groups and dispatch each sub-group to its handler."""
        # Phase 9 core operations
        trade_rows = [r for r in rows if r.operation in TRADE_OPS]
        convert_rows = [r for r in rows if r.operation == "Binance Convert"]
        deposit_rows = [r for r in rows if r.operation == "Deposit"]
        withdraw_rows = [r for r in rows if r.operation == "Withdraw"]
        p2p_rows = [r for r in rows if r.operation == "P2P Trading"]
        transfer_rows = [r for r in rows if "Transfer Between" in r.operation]

        # Phase 10 extended operations
        earn_rows = [r for r in rows if r.operation in EARN_OPS]
        futures_rows = [r for r in rows if r.operation in FUTURES_OPS]
        margin_rows = [r for r in rows if r.operation in MARGIN_OPS]
        loan_rows = [r for r in rows if r.operation in LOAN_OPS]
        special_rows = [r for r in rows if r.operation in SPECIAL_TOKEN_OPS]
        cashback_rows = [r for r in rows if r.operation == "Cashback Voucher"]
        fund_transfer_rows = [r for r in rows if r.operation in TRANSFER_FUND_OPS]

        categorised = set(id(r) for r in (
            trade_rows + convert_rows + deposit_rows + withdraw_rows + p2p_rows + transfer_rows
            + earn_rows + futures_rows + margin_rows + loan_rows + special_rows
            + cashback_rows + fund_transfer_rows
        ))
        other_rows = [r for r in rows if id(r) not in categorised]

        entries: list[ParsedEntry] = []

        # Phase 9 dispatch
        if trade_rows:
            entries.append(self._handle_spot_trade(trade_rows))
        if convert_rows:
            entries.append(self._handle_convert(convert_rows))
        for r in deposit_rows:
            entries.append(self._handle_deposit(r))
        for r in withdraw_rows:
            entries.append(self._handle_withdraw(r))
        for r in p2p_rows:
            entries.append(self._handle_p2p(r))
        if transfer_rows:
            entries.append(self._handle_internal_transfer(transfer_rows))

        # Phase 10 dispatch
        for r in earn_rows:
            entries.append(self._handle_earn(r))
        for r in futures_rows:
            entries.append(self._handle_futures(r))
        for r in margin_rows:
            entries.append(self._handle_margin(r))
        for r in loan_rows:
            entries.append(self._handle_loan(r))
        if special_rows:
            entries.extend(self._handle_special_tokens(special_rows))
        for r in cashback_rows:
            entries.append(self._handle_cashback(r))
        if fund_transfer_rows:
            entries.append(self._handle_internal_transfer(fund_transfer_rows))

        # Unknown operations -- mark as skipped, not error
        for r in other_rows:
            r.status = "skipped"
            r.error_message = f"Operation '{r.operation}' not handled"

        return entries

    # ------------------------------------------------------------------
    # Operation handlers
    # ------------------------------------------------------------------

    def _handle_spot_trade(self, rows: list[CsvImportRow]) -> ParsedEntry:
        """Transaction Buy/Spend/Fee OR Transaction Sold/Revenue/Fee -> SWAP."""
        splits: list[ParsedSplit] = []
        for row in rows:
            amount = Decimal(row.change)
            if row.operation == "Transaction Fee":
                # Fee is negative in CSV: record asset decrease + expense increase
                splits.append(ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount))
                splits.append(ParsedSplit(account_subtype="wallet_expense", symbol=row.coin, quantity=-amount))
            else:
                splits.append(ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount))
        return ParsedEntry(splits=splits, entry_type="SWAP", source_rows=list(rows))

    def _handle_convert(self, rows: list[CsvImportRow]) -> ParsedEntry:
        """Binance Convert: 2+ rows, one positive (buy), one negative (sell) -> SWAP."""
        splits: list[ParsedSplit] = []
        for row in rows:
            amount = Decimal(row.change)
            splits.append(ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount))
        return ParsedEntry(splits=splits, entry_type="SWAP", source_rows=list(rows))

    def _handle_deposit(self, row: CsvImportRow) -> ParsedEntry:
        """Single row: coin deposited to exchange -> DEPOSIT."""
        amount = Decimal(row.change)
        splits = [
            ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
            ParsedSplit(
                account_subtype="external_transfer",
                symbol=row.coin,
                quantity=-amount,
                account_params={"ext_address": "deposit"},
            ),
        ]
        return ParsedEntry(splits=splits, entry_type="DEPOSIT", source_rows=[row])

    def _handle_withdraw(self, row: CsvImportRow) -> ParsedEntry:
        """Single row: coin withdrawn (negative change, fee included) -> WITHDRAWAL."""
        amount = Decimal(row.change)  # negative
        splits = [
            ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
            ParsedSplit(
                account_subtype="external_transfer",
                symbol=row.coin,
                quantity=-amount,
                account_params={"ext_address": "withdrawal"},
            ),
        ]
        return ParsedEntry(splits=splits, entry_type="WITHDRAWAL", source_rows=[row])

    def _handle_p2p(self, row: CsvImportRow) -> ParsedEntry:
        """P2P Trading: fiat-to-crypto buy on Funding account -> DEPOSIT."""
        amount = Decimal(row.change)
        splits = [
            ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
            ParsedSplit(
                account_subtype="external_transfer",
                symbol=row.coin,
                quantity=-amount,
                account_params={"ext_address": "p2p"},
            ),
        ]
        return ParsedEntry(splits=splits, entry_type="DEPOSIT", source_rows=[row])

    def _handle_internal_transfer(self, rows: list[CsvImportRow]) -> ParsedEntry:
        """Transfer Between accounts: 2 mirrored rows (one +, one -) -> TRANSFER."""
        splits: list[ParsedSplit] = []
        for row in rows:
            amount = Decimal(row.change)
            splits.append(ParsedSplit(
                account_subtype="cex_asset",
                symbol=row.coin,
                quantity=amount,
                account_params={"sub_account": row.account},
            ))
        return ParsedEntry(splits=splits, entry_type="TRANSFER", source_rows=list(rows))

    # ------------------------------------------------------------------
    # Phase 10 handlers: Earn, Futures, Margin, Loan, Special, Cashback
    # ------------------------------------------------------------------

    def _handle_earn(self, row: CsvImportRow) -> ParsedEntry:
        """Simple Earn operations: subscription, redemption, interest/rewards."""
        amount = Decimal(row.change)
        op = row.operation

        if op in ("Simple Earn Flexible Subscription", "Simple Earn Locked Subscription"):
            # Move from spot to earn: negative = deducted from spot
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(
                    account_subtype="protocol_asset", symbol=row.coin, quantity=-amount,
                    account_params={"protocol": "binance_earn"},
                ),
            ]
            return ParsedEntry(splits=splits, entry_type="DEPOSIT", source_rows=[row])

        elif op == "Simple Earn Flexible Redemption":
            # Move from earn back to spot: positive = received in spot
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(
                    account_subtype="protocol_asset", symbol=row.coin, quantity=-amount,
                    account_params={"protocol": "binance_earn"},
                ),
            ]
            return ParsedEntry(splits=splits, entry_type="WITHDRAWAL", source_rows=[row])

        elif op in ("Simple Earn Flexible Interest", "Simple Earn Locked Rewards"):
            # Interest/rewards: income
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(
                    account_subtype="wallet_income", symbol=row.coin, quantity=-amount,
                    account_params={"tag": "Earn Interest"},
                ),
            ]
            return ParsedEntry(splits=splits, entry_type="YIELD", source_rows=[row])

        # Fallback (should not be reached)
        return ParsedEntry(
            splits=[ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount)],
            entry_type="UNKNOWN", source_rows=[row],
        )

    def _handle_futures(self, row: CsvImportRow) -> ParsedEntry:
        """Futures Fee, Funding Fee, Realized PnL."""
        amount = Decimal(row.change)
        op = row.operation

        if op == "Fee":
            # Trading fee: negative = expense
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(account_subtype="wallet_expense", symbol=row.coin, quantity=-amount),
            ]
            return ParsedEntry(splits=splits, entry_type="GAS_FEE", source_rows=[row])

        elif op == "Funding Fee":
            # Funding fee: can be positive (received) or negative (paid)
            if amount < 0:
                splits = [
                    ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                    ParsedSplit(account_subtype="wallet_expense", symbol=row.coin, quantity=-amount),
                ]
                return ParsedEntry(splits=splits, entry_type="GAS_FEE", source_rows=[row])
            else:
                splits = [
                    ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                    ParsedSplit(
                        account_subtype="wallet_income", symbol=row.coin, quantity=-amount,
                        account_params={"tag": "Funding Fee"},
                    ),
                ]
                return ParsedEntry(splits=splits, entry_type="YIELD", source_rows=[row])

        elif op == "Realized Profit and Loss":
            # PnL: positive = income, negative = loss (expense)
            if amount >= 0:
                splits = [
                    ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                    ParsedSplit(
                        account_subtype="wallet_income", symbol=row.coin, quantity=-amount,
                        account_params={"tag": "Futures PnL"},
                    ),
                ]
                return ParsedEntry(splits=splits, entry_type="YIELD", source_rows=[row])
            else:
                splits = [
                    ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                    ParsedSplit(account_subtype="wallet_expense", symbol=row.coin, quantity=-amount),
                ]
                return ParsedEntry(splits=splits, entry_type="GAS_FEE", source_rows=[row])

        return ParsedEntry(
            splits=[ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount)],
            entry_type="UNKNOWN", source_rows=[row],
        )

    def _handle_margin(self, row: CsvImportRow) -> ParsedEntry:
        """Margin operations: loan, forced repayment, liquidation."""
        amount = Decimal(row.change)
        op = row.operation

        if op == "Isolated Margin Loan":
            # Borrow: receive asset + incur debt
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(
                    account_subtype="protocol_debt", symbol=row.coin, quantity=-amount,
                    account_params={"protocol": "binance_margin"},
                ),
            ]
            return ParsedEntry(splits=splits, entry_type="BORROW", source_rows=[row])

        elif op == "Isolated Margin Liquidation - Forced Repayment":
            # Forced repayment: negative = paid back debt
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(
                    account_subtype="protocol_debt", symbol=row.coin, quantity=-amount,
                    account_params={"protocol": "binance_margin"},
                ),
            ]
            return ParsedEntry(splits=splits, entry_type="REPAY", source_rows=[row])

        elif op == "Cross Margin Liquidation - Small Assets Takeover":
            # Takeover: can be negative (asset taken) or positive (received)
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(
                    account_subtype="protocol_debt", symbol=row.coin, quantity=-amount,
                    account_params={"protocol": "binance_margin"},
                ),
            ]
            return ParsedEntry(splits=splits, entry_type="LIQUIDATION", source_rows=[row])

        return ParsedEntry(
            splits=[ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount)],
            entry_type="UNKNOWN", source_rows=[row],
        )

    def _handle_loan(self, row: CsvImportRow) -> ParsedEntry:
        """Flexible Loan operations: collateral, lending, repayment."""
        amount = Decimal(row.change)
        op = row.operation

        if op == "Flexible Loan - Collateral Transfer":
            # Collateral locked: negative = moved from spot to collateral
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(
                    account_subtype="protocol_asset", symbol=row.coin, quantity=-amount,
                    account_params={"protocol": "binance_loan"},
                ),
            ]
            return ParsedEntry(splits=splits, entry_type="DEPOSIT", source_rows=[row])

        elif op == "Flexible Loan - Lending":
            # Receive borrowed funds
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(
                    account_subtype="protocol_debt", symbol=row.coin, quantity=-amount,
                    account_params={"protocol": "binance_loan"},
                ),
            ]
            return ParsedEntry(splits=splits, entry_type="BORROW", source_rows=[row])

        elif op == "Flexible Loan - Repayment":
            # Repay loan: negative = paid back
            splits = [
                ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                ParsedSplit(
                    account_subtype="protocol_debt", symbol=row.coin, quantity=-amount,
                    account_params={"protocol": "binance_loan"},
                ),
            ]
            return ParsedEntry(splits=splits, entry_type="REPAY", source_rows=[row])

        return ParsedEntry(
            splits=[ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount)],
            entry_type="UNKNOWN", source_rows=[row],
        )

    def _handle_special_tokens(self, rows: list[CsvImportRow]) -> list[ParsedEntry]:
        """RWUSD, BFUSD, WBETH special token operations."""
        entries: list[ParsedEntry] = []
        for row in rows:
            amount = Decimal(row.change)
            op = row.operation

            if op in ("RWUSD - Distribution", "BFUSD Daily Reward"):
                # Income/reward
                entries.append(ParsedEntry(
                    splits=[
                        ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
                        ParsedSplit(
                            account_subtype="wallet_income", symbol=row.coin, quantity=-amount,
                            account_params={"tag": "Token Reward"},
                        ),
                    ],
                    entry_type="YIELD",
                    source_rows=[row],
                ))
            else:
                # Subscription, Redemption, Staking: single cex_asset leg
                # Paired rows at same timestamp form a balanced swap across entries
                entries.append(ParsedEntry(
                    splits=[ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount)],
                    entry_type="SWAP",
                    source_rows=[row],
                ))

        return entries

    def _handle_cashback(self, row: CsvImportRow) -> ParsedEntry:
        """Cashback Voucher: free income."""
        amount = Decimal(row.change)
        splits = [
            ParsedSplit(account_subtype="cex_asset", symbol=row.coin, quantity=amount),
            ParsedSplit(
                account_subtype="wallet_income", symbol=row.coin, quantity=-amount,
                account_params={"tag": "Cashback"},
            ),
        ]
        return ParsedEntry(splits=splits, entry_type="YIELD", source_rows=[row])

    # ------------------------------------------------------------------
    # Journal entry creation (integrated CsvBookkeeper)
    # ------------------------------------------------------------------

    async def _create_journal_entry(
        self,
        entry_data: ParsedEntry,
        utc_time: str,
    ) -> JournalEntry:
        """Create a JournalEntry + JournalSplits from parsed data."""
        timestamp = datetime.strptime(utc_time, "%Y-%m-%d %H:%M:%S")

        entry = JournalEntry(
            entity_id=self._entity_id,
            entry_type=entry_data.entry_type,
            description=f"Binance CSV: {entry_data.entry_type} at {utc_time}",
            timestamp=timestamp,
        )
        self._session.add(entry)
        await self._session.flush()

        for ps in entry_data.splits:
            account = await self._resolve_account(ps)
            split = JournalSplit(
                journal_entry_id=entry.id,
                account_id=account.id,
                quantity=ps.quantity,
            )
            self._session.add(split)

        await self._session.flush()
        return entry

    async def _resolve_account(self, ps: ParsedSplit):
        """Route a ParsedSplit to an Account via AccountMapper."""
        subtype = ps.account_subtype
        params = ps.account_params

        if subtype == "cex_asset":
            return await self._mapper.cex_asset(self._wallet, ps.symbol)
        elif subtype == "wallet_expense":
            return await self._mapper.cex_expense(self._wallet, ps.symbol)
        elif subtype == "external_transfer":
            ext_addr = params.get("ext_address", "external")
            return await self._mapper.external_transfer(self._wallet, ps.symbol, ext_addr)
        elif subtype == "wallet_income":
            tag = params.get("tag", "CEX")
            return await self._mapper.income(self._wallet, ps.symbol, tag)
        elif subtype == "protocol_asset":
            protocol = params.get("protocol", "unknown")
            return await self._mapper.protocol_asset(self._wallet, protocol, ps.symbol)
        elif subtype == "protocol_debt":
            protocol = params.get("protocol", "unknown")
            return await self._mapper.protocol_debt(self._wallet, protocol, ps.symbol)
        else:
            return await self._mapper.cex_asset(self._wallet, ps.symbol)
