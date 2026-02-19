# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Correctly parse any DeFi transaction into balanced double-entry journal entries. If parsing is wrong, everything downstream (gains, tax, reports) is wrong.
**Current focus:** v3.0 Milestone COMPLETE

## Current Position

Phase: 11 of 11 (Import UI Polish) — ALL PHASES COMPLETE
Plan: 1 of 1 in current phase
Status: Milestone v3.0 shipped
Last activity: 2026-02-19 -- Phase 11 Import UI Polish complete (1/1 plan)

Progress: [██████████] 100%

## Overall Project Stats

| Metric | Value |
|--------|-------|
| Tests passing | 444 |
| Lint errors | 0 |
| TypeScript errors | 0 |
| Backend parsers | 12 |
| API endpoints | 43+ |
| Web pages | 11 |
| Alembic migrations | base + v3_001 |

## Performance Metrics

**Velocity:**
- Total plans completed: 6 (v3.0)
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

## Accumulated Context

### Decisions Made (from v1.0 + v2.0 + v3.0 Phases 7-11)

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

### Known Limitations / Concerns

- Multi-chain gas calculation deferred from v2.0

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-19
Stopped at: Milestone v3.0 complete
Resume file: None
