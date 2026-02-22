# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Correctly parse any DeFi transaction into balanced double-entry journal entries. If parsing is wrong, everything downstream (gains, tax, reports) is wrong.
**Current focus:** v3.0 Milestone COMPLETE

## Current Position

Phase: 12 of 12 (Management Dashboard & Comprehensive Analytics) — COMPLETE (6/6 plans)
Plan: 6 of 6 in current phase
Status: Phase 12 Complete — v3.0 Milestone DONE
Last activity: 2026-02-22 -- Completed 12-06 (Analytics Dashboards + AI Insight Placeholder)

Progress: [██████████] 100% (6/6 plans)

## Overall Project Stats

| Metric | Value |
|--------|-------|
| Tests passing | 444 |
| Lint errors | 0 |
| TypeScript errors | 0 |
| Backend parsers | 12 |
| API endpoints | 43+ |
| Web pages | 13 |
| Alembic migrations | base + v3_001 + phase12 |

## Performance Metrics

**Velocity:**
- Total plans completed: 8 (v3.0)
- Average duration: --
- Total execution time: --

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 7. Entity Management | 2/2 | -- | -- |
| 8. CEX Import Infrastructure | 1/1 | -- | -- |
| 9. Binance CSV Parser Core | 1/1 | -- | -- |
| 10. Binance CSV Extended Ops | 1/1 | -- | -- |
| 11. Import UI Polish | 1/1 | -- | -- |
| 12. Management Dashboard | 6/6 | -- | -- |

## Accumulated Context

### Decisions Made (from v1.0 + v2.0 + v3.0 Phases 7-12)

- Entity model exists with UUID, name, base_currency, soft delete -- repos accept entity_id
- API parameterized: all endpoints accept optional entity_id query param via resolve_entity dependency
- EntityRepo has full CRUD: list_all, create, update, soft_delete, count_wallets
- Frontend EntityContext with localStorage persistence -- all hooks pass entityId
- EntitySelector in sidebar with stale-localStorage guard
- CsvImport + CsvImportRow models store raw CSV rows with audit trail
- Upload endpoint at POST /api/imports/upload accepts multipart form with entity_id
- CsvImportRow stores fields individually (utc_time, account, operation, coin, change, remark)
- CsvImportRow has status tracking (pending/parsed/error/skipped) and journal_entry_id FK
- Binance CSV Transaction History format: User_ID, UTC_Time, Account, Operation, Coin, Change, Remark
- BinanceCsvParser groups rows by UTC_Time, splits mixed-op groups, dispatches to handlers
- Core ops: spot trade (Buy/Spend/Fee, Sold/Revenue/Fee), Convert, Deposit, Withdraw, P2P, internal Transfer
- Extended ops: Simple Earn, Futures fees/PnL, Margin loan/repay/liquidation, Flexible Loans, RWUSD/BFUSD/WBETH, Cashback
- POST /api/imports/{id}/parse triggers parsing, auto-creates CEXWallet per entity+exchange
- GET /api/imports/{id}/summary returns operation counts and status breakdown
- GET /api/imports/{id}/rows?status=error returns failed rows with error messages
- Unknown operations marked "skipped" (not error)
- CexAsset polymorphic identity added to Account STI model
- SWAP entries don't balance per-symbol (different coins in/out) — correct behavior
- Admin-only multi-entity (no user auth) -- build data isolation first
- Import UI auto-parses after upload, shows expandable rows with summary panel and error detail
- Shared filter components (DateRangePicker, WalletSelector, ChainSelector, etc.) use controlled props pattern
- FilterBar accepts children for composable filter layouts with reset button
- DataTable uses TypeScript generics for type-safe sortable columns with custom renderers
- Pagination component handles ellipsis, edge cases, and "Showing X-Y of Z" display
- AnalyticsRepo (11 methods) queries journal/split/account/wallet joins with common filter kwargs
- TaxAnalyticsRepo (8 methods) queries ClosedLotRecord, OpenLotRecord, TaxableTransferRecord
- TaxableTransferRecord table persisted by TaxEngine alongside closed/open lots
- TaxableTransfer domain model has value_usd + journal_entry_id for DB persistence
- Analytics TypeScript client uses analyticsPath() helper building URL + filter query string + entityId
- BalanceOverTimeChart groups BalancePeriod[] by symbol into period->symbol map for Recharts multi-line
- CompositionDonut uses Math.abs() on balance_usd before account_type aggregation to avoid negative cancellation
- ActivityHeatmap is pure CSS grid (not Recharts) — 52 cols x 7 rows colored by volume percentile
- Journal URL drill-down uses useSearchParams -- filters sync to URL so analytics pages can link with pre-set filters
- Accounts filters applied client-side -- avoids API changes for simple wallet/symbol/protocol/type filtering
- Journal balance indicator computed from value_usd sum across splits (must be < $0.01 absolute)
- ChainSelector values are lowercase (matching API) -- value/label separation in component
- Dashboard mini CashFlowChart uses last6MonthsRange + granularity=month with graceful empty state
- useRealizedGains and useOpenLots hooks accept filter params (RealizedGainsFilters, OpenLotsFilters)
- AnalyticsFilters imported directly from api/analytics (useAnalytics hooks do not re-export it)
- NavLink end=true on /, /analytics, /tax nav items prevents parent-path active highlight on child routes

### Roadmap Evolution

- Phase 12 added: Management Dashboard & Comprehensive Analytics
- v3.0 Milestone now fully complete

### Known Limitations / Concerns

- Multi-chain gas calculation deferred from v2.0

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed 12-06-PLAN.md (Analytics Dashboards + AI Insight Placeholder) — Phase 12 COMPLETE
Resume file: None
