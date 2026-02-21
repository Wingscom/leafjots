# Roadmap: CryptoTax Vietnam

## Milestones

- **v1.0 Full Platform** - Phases 1-9 (shipped)
- **v2.0 Parser Diagnostics & Multi-Protocol** - Phases 1-6 (shipped)
- **v3.0 Multi-Entity + CEX CSV Import** - Phases 7-11 (shipped)

## Phases

<details>
<summary>v1.0 Full Platform (Phases 1-6) - SHIPPED</summary>

- [x] **Phase 1: Foundation + Dashboard Shell** - Config, DI, DB session, 12 domain enums, Alembic, FastAPI app, Vite+React scaffold, Layout+sidebar
- [x] **Phase 2: Domain Models + Wallet Manager** - Entity, Wallet STI, Transaction, Account STI (8 subtypes), Journal+Splits, repos, /api/wallets CRUD, Wallets page
- [x] **Phase 3: EVM Infrastructure + TX Viewer** - Etherscan client, EVM TX loader, Solana support, /api/transactions, Transactions page, explorer links
- [x] **Phase 4: Parser Engine + Journal/Error Views** - GenericEVM, GenericSwap, ParserRegistry, Bookkeeper, AccountMapper, /api/parse + /api/journal + /api/accounts + /api/errors, 4 UI pages
- [x] **Phase 5: DeFi Protocol Parsers** - Aave V3, Uniswap V3, Curve, PancakeSwap + Binance CEX infra (API client, loader, parsers)
- [x] **Phase 6: Price + Tax Engine** - CoinGecko price cache, FIFO capital gains, Vietnam 0.1% tax + VND 20M exemption, /api/tax, Tax page

Plans:
- [x] 01-01: Foundation + Dashboard Shell (9 tasks)
- [x] 02-01: Domain Models + Wallet Manager (10 tasks)
- [x] 03-01: EVM Infrastructure + TX Viewer (10 tasks)
- [x] 04-01: Parser Engine + Journal/Error Views (18 tasks)
- [x] 05-01: DeFi Protocol Parsers (10 tasks)
- [x] 06-01: Price + Tax Engine (12 tasks)

</details>

<details>
<summary>v2.0 Parser Diagnostics & Multi-Protocol (Phases 1-6) - SHIPPED 2026-02-18</summary>

- [x] **Phase 1: Parser Foundation & Diagnostics Infrastructure** - ParseResult dataclass, diagnostic_data column, wrap handler
- [x] **Phase 2: Diagnostic UI & Error Grouping** - Error page fix, summary bar, diagnostic panel, bulk retry
- [x] **Phase 3: Morpho Blue Parser** - MorphoBlueParser + MetaMorphoVaultParser
- [x] **Phase 4: Lido wstETH & Multi-Chain Verification** - LidoParser (Lido done, multi-chain deferred)
- [x] **Phase 5: Pendle Parser** - PendleParser (swaps/SY/YT yield)
- [x] **Phase 6: Dashboard Polish & Extended Features** - Protocol coverage badges, explorer links

</details>

### v3.0 Multi-Entity + CEX CSV Import

**Milestone Goal:** Transform from single-entity tool into multi-client platform with Binance CSV import. Each client (fund/individual) has isolated wallets, transactions, journal entries, and tax reports.

**Phase Numbering:**
- Integer phases (7, 8, 9, 10, 11): Planned milestone work
- Decimal phases (e.g., 8.1): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 7: Entity Management** - Admin can create/manage entities and all pages scope data by selected entity
- [x] **Phase 8: CEX Import Infrastructure** - Database models, upload API, and import history for CSV imports
- [x] **Phase 9: Binance CSV Parser -- Core Operations** - Spot trades, converts, deposits, withdrawals, P2P, internal transfers
- [x] **Phase 10: Binance CSV Parser -- Earn, Futures, Margin & Specials** - Earn products, futures PnL/fees, margin loans, flexible loans, special tokens
- [x] **Phase 11: Import UI Polish** - Async parsing progress, import summary, error detail view

## Phase Details

### Phase 7: Entity Management
**Goal**: Admin can create and manage multiple client entities, and every page in the application shows data scoped to the selected entity
**Depends on**: v2.0 complete (existing entity model, repos with entity_id support)
**Requirements**: ENTY-01, ENTY-02, ENTY-03, ENTY-04, ENTY-05, ENTY-06, ENTY-07
**Success Criteria** (what must be TRUE):
  1. Admin can create a new entity with a name and base currency, and it appears in the entity list with its wallet count
  2. A global entity selector dropdown in the UI header persists the selected entity across all page navigations
  3. All API endpoints accept entity context (header or query parameter) and return only data belonging to that entity -- no more hardcoded get_default()
  4. Switching entities in the dropdown causes Wallets, Transactions, Journal, Errors, Tax, Reports, and Dashboard pages to show only that entity's data
  5. Admin can rename or soft-delete an entity, and soft-deleted entities no longer appear in the selector
**Plans**: 2/2 complete

Plans:
- [x] 07-01: Backend Entity CRUD + API Entity Scoping (14 tasks, ENTY-01/02/03/05)
- [x] 07-02: Frontend Entity Selector + Page Scoping (11 tasks, ENTY-04/06/07, depends on 07-01)

### Phase 8: CEX Import Infrastructure
**Goal**: The system can receive a CSV file upload, store it with full audit trail, and display import history -- ready for parsers to process
**Depends on**: Phase 7 (entity scoping -- imports belong to an entity)
**Requirements**: CIMP-01, CIMP-02, CIMP-03, CIMP-04, CIMP-05, CIMP-06, IMUI-01
**Success Criteria** (what must be TRUE):
  1. CsvImport and CsvImportRow tables exist in the database (via Alembic migration) storing import metadata and raw CSV rows
  2. POST /api/imports/upload accepts a CSV file with entity_id, creates an import record, and stores every row from the file
  3. GET /api/imports returns import history for the selected entity showing filename, upload date, row count, and status
  4. The Import/Upload page in the UI lets admin select an entity, upload a CSV file, and see the import appear in the history table
**Plans**: 1/1 complete

Plans:
- [x] 08-01: DB Models, Upload API, Import History (12 tasks, CIMP-01..06 + IMUI-01)

### Phase 9: Binance CSV Parser -- Core Operations
**Goal**: The most common Binance operations (spot trading, converts, deposits/withdrawals, P2P, internal transfers) are parsed into balanced journal entries
**Depends on**: Phase 8 (import infrastructure to store CSV rows and link parsed entries)
**Requirements**: BCSV-01, BCSV-02, BCSV-03, BCSV-04, BCSV-05, BCSV-06, BCSV-16, BCSV-17
**Success Criteria** (what must be TRUE):
  1. Spot buy (Transaction Buy/Spend/Fee) and spot sell (Transaction Sold/Revenue/Fee) rows grouped by timestamp produce balanced SWAP journal entries with fees as expense
  2. Binance Convert paired rows, Deposit, Withdraw, and P2P Trading rows each produce correctly typed and balanced journal entries
  3. Internal transfers between Spot, Funding, Futures, Margin, and Options accounts are recorded as internal TRANSFER entries (no tax event)
  4. Every journal entry produced by the parser has splits that sum to zero per entry (balance validation)
  5. CSV rows that fail to parse are recorded in the import with error details (operation type, raw data, error message) rather than silently dropped
**Plans**: 1/1 complete

Plans:
- [x] 09-01: Binance CSV Transaction Parser + Parse Trigger API (9 tasks, BCSV-01..06 + BCSV-16/17)

### Phase 10: Binance CSV Parser -- Earn, Futures, Margin & Specials
**Goal**: All remaining Binance operation types (earn products, futures, margin, loans, special tokens) are parsed into balanced journal entries, achieving full coverage of the 48 known operation types
**Depends on**: Phase 9 (core parser framework and grouping logic established)
**Requirements**: BCSV-07, BCSV-08, BCSV-09, BCSV-10, BCSV-11, BCSV-12, BCSV-13, BCSV-14, BCSV-15
**Success Criteria** (what must be TRUE):
  1. Simple Earn subscriptions/redemptions produce DEPOSIT/WITHDRAWAL entries to earn accounts, and interest/rewards produce INCOME entries
  2. Futures fees and funding fees produce EXPENSE entries, and Futures Realized PnL produces INCOME or EXPENSE based on sign
  3. Margin loan, forced repayment, and cross margin liquidation produce correctly balanced BORROW/REPAY journal entries
  4. Flexible Loan operations (collateral transfer, lending, repayment) produce correct DEPOSIT/BORROW/REPAY entries
  5. Special token operations (RWUSD, BFUSD, WBETH) and Cashback Voucher each produce correctly typed and balanced journal entries
**Plans**: 1/1 complete

Plans:
- [x] 10-01: Binance CSV Extended Operations Parser (9 tasks, BCSV-07..15)

### Phase 11: Import UI Polish
**Goal**: The import experience shows real-time progress, clear summaries, and actionable error details so the admin can confidently import and verify CSV data
**Depends on**: Phase 10 (all parsers complete so progress and summaries are meaningful)
**Requirements**: IMUI-02, IMUI-03, IMUI-04
**Success Criteria** (what must be TRUE):
  1. After clicking upload, a progress indicator shows parsing status (not just a spinner -- shows row count or percentage)
  2. After import completes, a summary screen shows total rows processed, grouped operation counts, success count, and error count
  3. Failed rows are viewable in a list showing the raw CSV data and the specific error message for each failure
**Plans**: 1/1 complete

Plans:
- [x] 11-01: Import UI Polish — Progress, Summary, Error Detail (9 tasks, IMUI-02/03/04)

## Progress

**Execution Order:**
Phases execute in numeric order: 7 -> 8 -> 9 -> 10 -> 11

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 7. Entity Management | 2/2 | Complete | 2026-02-18 |
| 8. CEX Import Infrastructure | 1/1 | Complete | 2026-02-18 |
| 9. Binance CSV Parser -- Core Operations | 1/1 | Complete | 2026-02-19 |
| 10. Binance CSV Parser -- Earn, Futures, Margin & Specials | 1/1 | Complete | 2026-02-19 |
| 11. Import UI Polish | 1/1 | Complete | 2026-02-19 |

### Phase 12: Management Dashboard & Comprehensive Analytics

**Goal:** Comprehensive analytics dashboards with filterable charts, KPI cards, drill-down navigation, and tax analytics — plus filter improvements on all existing pages
**Depends on:** Phase 11
**Requirements:** ANAL-01 through ANAL-16
**Success Criteria** (what must be TRUE):
  1. Admin can view a management analytics dashboard with KPI cards, cash flow charts, composition donuts, top symbols/protocols, and activity heatmap
  2. Admin can view a tax analytics dashboard with realized gains charts, holding period distribution, winners/losers, tax breakdown, and unrealized P&L
  3. All existing pages (Transactions, Journal, Tax, Accounts) have comprehensive filter controls
  4. Clicking chart elements on analytics pages navigates to Journal page with pre-set filters for drill-down
  5. Sidebar navigation includes Analytics and Tax Analytics links
**Plans:** 6 plans

Plans:
- [ ] 12-01-PLAN.md -- Backend analytics repos + TaxableTransfer persistence (AnalyticsRepo, TaxAnalyticsRepo, TaxableTransferRecord)
- [ ] 12-02-PLAN.md -- Analytics API router (19 endpoints) + extend existing API filters
- [ ] 12-03-PLAN.md -- Frontend filter components + DataTable + Pagination
- [ ] 12-04-PLAN.md -- Recharts chart components + analytics API client + hooks
- [ ] 12-05-PLAN.md -- Improve existing pages with filters and mini-charts
- [ ] 12-06-PLAN.md -- Analytics + Tax Analytics pages + AI placeholder + routes
