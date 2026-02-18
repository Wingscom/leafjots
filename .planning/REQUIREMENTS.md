# Requirements: CryptoTax Vietnam — Milestone v3.0

**Defined:** 2026-02-18
**Core Value:** Correctly parse any DeFi transaction into balanced double-entry journal entries. If parsing is wrong, everything downstream (gains, tax, reports) is wrong.

## v1 Requirements

Requirements for milestone v3.0: Multi-Entity Client Management + CEX CSV Import.

### Entity Management

- [ ] **ENTY-01**: Admin can create a new entity (client) with name and base currency
- [ ] **ENTY-02**: Admin can list all entities and see wallet count per entity
- [ ] **ENTY-03**: Admin can rename or soft-delete an entity
- [ ] **ENTY-04**: UI has a global entity selector dropdown that persists across page navigation
- [ ] **ENTY-05**: All API endpoints accept entity context (header or parameter) instead of hardcoded get_default()
- [ ] **ENTY-06**: All UI pages (Wallets, Transactions, Journal, Errors, Tax, Reports) filter data by the selected entity
- [ ] **ENTY-07**: Dashboard home shows stats scoped to the selected entity

### CEX Import Infrastructure

- [ ] **CIMP-01**: CsvImport model stores import metadata (entity_id, exchange, filename, row_count, status, created_at)
- [ ] **CIMP-02**: CsvImportRow model stores each raw CSV row linked to its import (for audit trail + re-parse)
- [ ] **CIMP-03**: POST /api/imports/upload accepts CSV file + entity_id, creates CsvImport record and stores rows
- [ ] **CIMP-04**: GET /api/imports lists import history for an entity (filename, date, rows, success/error counts)
- [ ] **CIMP-05**: Alembic migration for csv_imports and csv_import_rows tables
- [ ] **CIMP-06**: Simple Upload page in UI — select entity, upload CSV, show parse progress and results

### Binance CSV Parser

- [ ] **BCSV-01**: Spot trades parsed — Transaction Buy/Spend/Fee grouped by timestamp into SWAP journal entries
- [ ] **BCSV-02**: Spot sells parsed — Transaction Sold/Revenue/Fee grouped into SWAP journal entries
- [ ] **BCSV-03**: Binance Convert parsed — paired buy/sell entries at same timestamp into SWAP entries
- [ ] **BCSV-04**: Deposit and Withdraw parsed into TRANSFER journal entries
- [ ] **BCSV-05**: P2P Trading parsed as DEPOSIT (fiat→crypto acquire)
- [ ] **BCSV-06**: Internal transfers parsed — Spot↔Funding, Spot↔Futures, Spot↔Margin, Spot↔Options as internal TRANSFER (no tax event)
- [ ] **BCSV-07**: Simple Earn Flexible/Locked Subscription and Redemption parsed as DEPOSIT/WITHDRAWAL to earn account
- [ ] **BCSV-08**: Simple Earn Interest and Locked Rewards parsed as INCOME journal entries
- [ ] **BCSV-09**: Futures Fee and Funding Fee parsed as EXPENSE journal entries
- [ ] **BCSV-10**: Futures Realized PnL parsed as INCOME or EXPENSE based on sign
- [ ] **BCSV-11**: Isolated Margin Loan parsed as BORROW, Forced Repayment as REPAY
- [ ] **BCSV-12**: Cross Margin Liquidation (Small Assets Takeover) parsed correctly
- [ ] **BCSV-13**: Flexible Loan — Collateral Transfer, Lending, Repayment parsed as DEPOSIT/BORROW/REPAY
- [ ] **BCSV-14**: Special tokens — RWUSD Subscription/Distribution/Redemption, BFUSD Subscription/Reward, WBETH Staking parsed correctly
- [ ] **BCSV-15**: Cashback Voucher parsed as INCOME
- [ ] **BCSV-16**: All journal entries from CSV import are balanced (splits sum to 0 per entry)
- [ ] **BCSV-17**: CSV rows that fail to parse are recorded with error details for review

### Import UI

- [ ] **IMUI-01**: Upload page shows import history table (filename, date, rows, parsed, errors)
- [ ] **IMUI-02**: Upload triggers async parsing with progress indicator
- [ ] **IMUI-03**: After import, show summary: total rows, grouped operations, success count, error count
- [ ] **IMUI-04**: Failed rows are viewable with error message and raw CSV data

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Multi-Exchange CSV

- **MEXC-01**: OKX CSV import parser
- **MEXC-02**: Bybit CSV import parser
- **MEXC-03**: Generic CSV template for other exchanges

### Auth & Permissions

- **AUTH-01**: User model with email/password login
- **AUTH-02**: Role-based access (Admin, Accountant, Viewer)
- **AUTH-03**: Entity-user assignment (which users can see which entities)
- **AUTH-04**: JWT authentication middleware

### Advanced Entity

- **AENT-01**: Entity settings (tax year, reporting currency, FIFO method config)
- **AENT-02**: Entity audit log (who changed what, when)
- **AENT-03**: Entity export/import (backup and restore)

## Out of Scope

| Feature | Reason |
|---------|--------|
| End-user authentication / login | Admin-only tool for now, auth layer added in future milestone |
| Multi-user permissions | Single admin manages all entities, no user isolation needed yet |
| OKX/Bybit CSV import | Binance first, other exchanges in future milestone |
| Binance API live sync for CEX | CSV import covers the use case, API sync is nice-to-have |
| Real-time import progress via WebSocket | Simple polling/refresh is sufficient for local tool |
| CSV format auto-detection | Require user to specify exchange (Binance), auto-detect later |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENTY-01 | TBD | Pending |
| ENTY-02 | TBD | Pending |
| ENTY-03 | TBD | Pending |
| ENTY-04 | TBD | Pending |
| ENTY-05 | TBD | Pending |
| ENTY-06 | TBD | Pending |
| ENTY-07 | TBD | Pending |
| CIMP-01 | TBD | Pending |
| CIMP-02 | TBD | Pending |
| CIMP-03 | TBD | Pending |
| CIMP-04 | TBD | Pending |
| CIMP-05 | TBD | Pending |
| CIMP-06 | TBD | Pending |
| BCSV-01 | TBD | Pending |
| BCSV-02 | TBD | Pending |
| BCSV-03 | TBD | Pending |
| BCSV-04 | TBD | Pending |
| BCSV-05 | TBD | Pending |
| BCSV-06 | TBD | Pending |
| BCSV-07 | TBD | Pending |
| BCSV-08 | TBD | Pending |
| BCSV-09 | TBD | Pending |
| BCSV-10 | TBD | Pending |
| BCSV-11 | TBD | Pending |
| BCSV-12 | TBD | Pending |
| BCSV-13 | TBD | Pending |
| BCSV-14 | TBD | Pending |
| BCSV-15 | TBD | Pending |
| BCSV-16 | TBD | Pending |
| BCSV-17 | TBD | Pending |
| IMUI-01 | TBD | Pending |
| IMUI-02 | TBD | Pending |
| IMUI-03 | TBD | Pending |
| IMUI-04 | TBD | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 0 (awaiting roadmap)
- Unmapped: 28

---
*Requirements defined: 2026-02-18*
*Last updated: 2026-02-18 after initial definition*
