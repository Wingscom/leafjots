---
phase: 12-management-dashboard-comprehensive-analytics
plan: 02
subsystem: api
tags: [fastapi, analytics, pydantic, filters, sqlalchemy]

requires:
  - phase: 12-management-dashboard-comprehensive-analytics
    plan: 01
    provides: "AnalyticsRepo (11 methods) + TaxAnalyticsRepo (8 methods)"

provides:
  - "Analytics API router with 19 endpoints at /api/analytics/*"
  - "Pydantic response schemas for all 19 analytics endpoints"
  - "Extended filter params on /api/transactions, /api/journal, /api/tax/*, /api/accounts"

affects: [12-03, 12-04, 12-05, 12-06]

tech-stack:
  added: []
  patterns:
    - "_build_filters() helper centralizes entity+filter kwargs construction for analytics router"
    - "Conditional join pattern in JournalRepo.list_for_entity: simple query when no split-level filters, joined query with distinct() when symbol/account_type/wallet/protocol filters needed"
    - "Epoch conversion for Transaction.timestamp (BigInteger unix) date filtering"

key-files:
  created:
    - src/cryptotax/api/schemas/analytics.py
    - src/cryptotax/api/analytics.py
  modified:
    - src/cryptotax/api/main.py
    - src/cryptotax/db/repos/transaction_repo.py
    - src/cryptotax/db/repos/journal_repo.py
    - src/cryptotax/db/repos/account_repo.py
    - src/cryptotax/api/transactions.py
    - src/cryptotax/api/journal.py
    - src/cryptotax/api/tax.py
    - src/cryptotax/api/accounts.py

key-decisions:
  - "Analytics router uses _build_filters() helper to build kwargs dict for AnalyticsRepo/TaxAnalyticsRepo calls, keeping endpoint signatures clean"
  - "JournalRepo.list_for_entity uses conditional join: avoids unnecessary join overhead when no split-level filters are requested"
  - "Transaction date filtering converts datetime to epoch int (Transaction.timestamp is BigInteger unix seconds)"
  - "Decimal-to-float conversion handled by _to_float() helper in schemas/analytics.py to ensure JSON serialization"

requirements-completed: [ANAL-04, ANAL-05, ANAL-06]

duration: 20min
completed: 2026-02-22
---

# Phase 12 Plan 02: Analytics API Router & Extended Filters Summary

**Analytics API router (19 endpoints) + Pydantic response schemas + comprehensive filter parameters added to transactions, journal, tax, and accounts endpoints**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-02-22
- **Completed:** 2026-02-22
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Created `src/cryptotax/api/schemas/analytics.py` with 19 Pydantic response models (KPISummaryResponse, CashFlowPeriod, SymbolVolume, ProtocolVolume, CompositionItem, ActivityDay, EntryTypeBreakdown, IncomeExpensePeriod, BalancePeriod, WalletFlow, ChainFlow, OverviewResponse, RealizedGainsPeriod, GainsBySymbol, HoldingBucket, WinnersLosers, TaxBreakdownPeriod, TaxByCategory, UnrealizedPosition, CostBasisItem)
- Created `src/cryptotax/api/analytics.py` with 19 endpoints covering general analytics (overview, cash-flow, income-expense, balance-over-time, top-symbols, top-protocols, composition, activity, entry-types, flow-by-wallet, flow-by-chain) and tax analytics (gains-over-time, gains-by-symbol, holding-distribution, winners-losers, breakdown, by-category, unrealized, cost-basis)
- Registered analytics router in `src/cryptotax/api/main.py` via `app.include_router(analytics_router)`
- Extended `TransactionRepo.list_for_entity` with `date_from`/`date_to` (converts to unix epoch for BigInteger timestamp column)
- Extended `JournalRepo.list_for_entity` with `date_from`, `date_to`, `symbol`, `account_type`, `wallet_id`, `protocol`, `account_subtype` (uses conditional join pattern — avoids join overhead when no split-level filters)
- Extended `JournalRepo.get_splits_for_account` with `date_from`/`date_to` (joins JournalEntry for timestamp filter)
- Extended `AccountRepo.get_all_for_entity` with `subtype`, `symbol`, `protocol`, `wallet_id`
- Extended `/api/transactions` GET with `date_from`, `date_to` query params
- Extended `/api/journal` GET with `date_from`, `date_to`, `symbol`, `account_type`, `wallet_id`, `protocol`, `account_subtype` query params
- Extended `/api/tax/realized-gains` GET with `symbol`, `date_from`, `date_to`, `gain_only`, `loss_only`, `min_holding_days`, `max_holding_days`
- Extended `/api/tax/open-lots` GET with `symbol`, `min_quantity`
- Extended `/api/accounts` GET with `subtype`, `symbol`, `protocol`, `wallet_id`
- Extended `/api/accounts/{id}/history` GET with `date_from`, `date_to`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create analytics Pydantic schemas and API router with 19 endpoints** - pending commit
2. **Task 2: Extend existing API routers with comprehensive filter parameters** - pending commit

## Files Created/Modified

- `src/cryptotax/api/schemas/analytics.py` - 19 Pydantic response models for analytics endpoints
- `src/cryptotax/api/analytics.py` - Analytics router with 19 endpoints connecting to AnalyticsRepo + TaxAnalyticsRepo
- `src/cryptotax/api/main.py` - Registered analytics_router via app.include_router
- `src/cryptotax/db/repos/transaction_repo.py` - Added date_from/date_to to list_for_entity (epoch conversion)
- `src/cryptotax/db/repos/journal_repo.py` - Added comprehensive filters to list_for_entity + date filters to get_splits_for_account
- `src/cryptotax/db/repos/account_repo.py` - Added subtype/symbol/protocol/wallet_id to get_all_for_entity
- `src/cryptotax/api/transactions.py` - Added date_from/date_to query params
- `src/cryptotax/api/journal.py` - Added full filter set query params
- `src/cryptotax/api/tax.py` - Added symbol/date/gain_only/loss_only/holding_days to realized-gains; symbol/min_quantity to open-lots
- `src/cryptotax/api/accounts.py` - Added subtype/symbol/protocol/wallet_id to list; date_from/date_to to history

## Decisions Made

- Used `_build_filters()` helper in analytics.py to centralize entity+filter kwargs construction — keeps each endpoint implementation concise
- JournalRepo uses conditional join: simple `select(JournalEntry)` when only entry_type/date filters, full `JOIN splits->accounts->wallets` with `distinct()` only when split-level filters (symbol, account_type, etc.) are needed — avoids unnecessary join overhead
- Transaction date filtering converts `datetime` to `int(dt.timestamp())` because `Transaction.timestamp` is a BigInteger unix epoch column
- `_to_float()` helper in schemas file converts Decimal results to float for JSON serialization across all 19 analytics endpoints

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 19 analytics endpoints are accessible via `/api/analytics/*`
- All existing endpoints have comprehensive filter params for frontend use
- Ready for frontend analytics pages (Plans 03-06)

---
*Phase: 12-management-dashboard-comprehensive-analytics*
*Completed: 2026-02-22*
