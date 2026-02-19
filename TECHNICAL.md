# LeafJots — Technical Documentation

> Automated DeFi accounting platform. Parses on-chain transactions into double-entry journal entries,
> computes FIFO capital gains, and exports multi-sheet Excel reports.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Backend Modules](#backend-modules)
5. [Database Schema](#database-schema)
6. [Parser System](#parser-system)
7. [Accounting Engine](#accounting-engine)
8. [Price Feed](#price-feed)
9. [API Reference](#api-reference)
10. [Frontend](#frontend)
11. [Workers & Task Queue](#workers--task-queue)
12. [Report Generator](#report-generator)
13. [Testing](#testing)
14. [Configuration](#configuration)
15. [Deployment](#deployment)

---

## Architecture Overview

```
On-Chain TX → TX Loader → Parser Engine → Bookkeeper → Journal Entries
                                                ↓
                              Price Feed → Capital Gains (FIFO) → Tax → Report
                                                                          ↓
                                                                   Local Web Dashboard
                                                                   (view, debug, export)
```

### Full System Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    LOCAL WEB DASHBOARD                          │
│  React 18 + Vite (localhost:5173)                              │
│  ┌──────────┬───────────┬──────────┬──────────┬─────────────┐  │
│  │ Wallets  │ Tx Viewer │ Journal  │ Errors & │ Tax Report  │  │
│  │ Manager  │ & Parser  │ Entries  │ Warnings │ & Export    │  │
│  └──────────┴───────────┴──────────┴──────────┴─────────────┘  │
│         ↕ HTTP (localhost:8000/api)                             │
├────────────────────────────────────────────────────────────────┤
│                    FASTAPI BACKEND                              │
│  /entities  /wallets  /transactions  /parse  /journal          │
│  /accounts  /errors   /tax   /reports  /imports                │
├────────────────────────────────────────────────────────────────┤
│  Parser Engine │ Bookkeeper │ Tax Engine │ Price Feed │ Report │
├────────────────────────────────────────────────────────────────┤
│  PostgreSQL 16 │ Redis 7    │ Celery Workers                   │
└────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Horizontal-first parsing** — Generic parsers handle 80% of transactions; protocol-specific parsers only where generic fails.
2. **Clean Architecture** — Domain → Repository → Service → API. No circular dependencies.
3. **Dependency Injection** — `dependency-injector` for container management. No singletons.
4. **Double-entry accounting** — Every journal entry must balance to zero (quantity, USD, VND).
5. **Real transaction tests** — No mocks for accounting logic; test with real blockchain fixtures.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Python | >= 3.11 |
| API Framework | FastAPI | >= 0.115 |
| ORM | SQLAlchemy 2.0 (async) | >= 2.0 |
| Database | PostgreSQL | 16 |
| Migrations | Alembic | >= 1.14 |
| Validation | Pydantic v2 | >= 2.10 |
| DI Container | dependency-injector | >= 4.43 |
| Blockchain | web3.py | >= 7.6 |
| Task Queue | Celery + Redis | >= 5.4 |
| HTTP Client | httpx | >= 0.28 |
| Retry | tenacity | >= 9.0 |
| Excel | openpyxl | >= 3.1 |
| Frontend | React 18 + Vite 6 | |
| Styling | Tailwind CSS 3.4 | |
| Data Fetching | TanStack Query 5 | |
| Icons | lucide-react | |
| Linting | ruff | >= 0.9 |
| Testing | pytest + pytest-asyncio | >= 8.0 |

---

## Project Structure

```
leafjots/
├── CLAUDE.md                  # AI assistant instructions
├── TECHNICAL.md               # This file
├── README.md                  # Quick-start guide
├── pyproject.toml             # Python package config
├── docker-compose.yml         # PostgreSQL + Redis
├── alembic.ini                # Migration config
├── .env.example               # Environment template
│
├── src/cryptotax/             # Python backend package
│   ├── config.py              # Settings (pydantic-settings)
│   ├── container.py           # DI container
│   ├── exceptions.py          # Exception hierarchy
│   │
│   ├── domain/                # Pure domain models & enums
│   │   ├── enums/             # AccountType, Chain, EntryType, etc.
│   │   └── models/            # Pydantic domain models (Trade, TaxSummary)
│   │
│   ├── db/                    # Database layer
│   │   ├── session.py         # Engine & session factory, Base, mixins
│   │   ├── models/            # SQLAlchemy ORM models (10 models)
│   │   └── repos/             # Repository classes (7 repos)
│   │
│   ├── infra/                 # External infrastructure
│   │   ├── blockchain/        # Chain clients (EVM + Solana)
│   │   ├── cex/               # CEX clients (Binance API + CSV)
│   │   ├── http/              # Rate-limited HTTP client
│   │   └── price/             # Price feed (CoinGecko + cache)
│   │
│   ├── parser/                # Transaction parser engine
│   │   ├── registry.py        # Parser registry + default build
│   │   ├── generic/           # Generic parsers (EVM, Swap)
│   │   ├── defi/              # Protocol parsers (7 protocols)
│   │   ├── cex/               # CEX parsers (Binance)
│   │   ├── handlers/          # Reusable split builders
│   │   └── utils/             # Context, transfers, gas, types
│   │
│   ├── accounting/            # Core accounting logic
│   │   ├── bookkeeper.py      # TX → Journal orchestrator
│   │   ├── account_mapper.py  # Get-or-create accounts
│   │   ├── fifo.py            # FIFO lot matching (pure)
│   │   └── tax_engine.py      # Capital gains + tax calc
│   │
│   ├── report/                # Report generation
│   │   ├── data_collector.py  # Gather all report data
│   │   ├── excel_writer.py    # Write 14-sheet Excel
│   │   └── service.py         # Orchestration + file IO
│   │
│   ├── api/                   # FastAPI endpoints
│   │   ├── main.py            # App, CORS, routers, lifespan
│   │   ├── deps.py            # DI deps (get_db, build_bookkeeper)
│   │   ├── schemas/           # Request/response Pydantic models
│   │   └── *.py               # Route modules (10 routers)
│   │
│   └── workers/               # Celery background tasks
│       ├── celery_app.py      # Celery instance
│       └── tasks.py           # sync_wallet_task
│
├── web/                       # React frontend
│   ├── src/
│   │   ├── App.tsx            # Route definitions
│   │   ├── context/           # EntityContext (global state)
│   │   ├── api/               # API client modules
│   │   ├── hooks/             # TanStack Query hooks
│   │   ├── components/        # Layout, EntitySelector
│   │   └── pages/             # 11 page components
│   └── ...
│
├── tests/                     # Test suite
│   ├── conftest.py            # SQLite in-memory fixtures
│   ├── fixtures/              # Real TX JSON fixtures
│   ├── unit/                  # Unit tests (~40 files)
│   └── integration/           # Integration tests (~10 files)
│
├── scripts/                   # Utility scripts
│   └── e2e_test.py            # Full pipeline E2E test
│
├── docs/reference/            # Domain knowledge docs
└── .planning/                 # Project planning docs
```

---

## Backend Modules

### `config.py` — Application Settings

Uses `pydantic-settings` to load from `.env` file:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `db_host` | str | localhost | PostgreSQL host |
| `db_port` | int | 5432 | PostgreSQL port |
| `db_user` | str | postgres | DB user |
| `db_password` | str | postgres | DB password |
| `db_name` | str | cryptotax | DB name |
| `redis_url` | str | redis://localhost:6379/0 | Redis connection |
| `etherscan_api_key` | str | "" | Etherscan API key (v2 unified) |
| `coingecko_api_key` | str | "" | CoinGecko Pro API key |
| `solana_rpc_url` | str | public endpoint | Solana RPC URL |
| `helius_api_key` | str | "" | Helius API key (Solana) |
| `binance_api_key` | str | "" | Binance API key |
| `binance_api_secret` | str | "" | Binance API secret |
| `encryption_key` | str | placeholder | Fernet key for CEX credential storage |
| `usd_vnd_rate` | int | 25000 | USD/VND exchange rate |
| `debug` | bool | True | Debug mode |

### `container.py` — Dependency Injection

`Container(DeclarativeContainer)` provides:
- `settings` — Singleton Settings instance
- `engine` — Singleton async SQLAlchemy engine
- `session_factory` — Singleton session maker

### `exceptions.py` — Error Hierarchy

```
LeafJotsError
├── ParseError          — Transaction parsing failures
├── PriceNotFoundError  — Price lookup failures
├── BalanceError        — Journal entry imbalance
├── TaxCalculationError — Tax computation errors
├── ExternalServiceError — API/RPC failures
└── ValidationError     — Input validation errors
```

---

## Database Schema

### Entity

The top-level organizational unit (person, company, fund).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| name | VARCHAR(255) | Entity name |
| base_currency | VARCHAR(10) | Default "VND" |
| deleted_at | TIMESTAMP | Soft delete marker |
| created_at | TIMESTAMP | Auto-set |
| updated_at | TIMESTAMP | Auto-updated |

### Wallet (Single Table Inheritance)

Three subtypes: `Wallet` (base), `OnChainWallet`, `CEXWallet`.

| Column | Type | Subtype | Notes |
|--------|------|---------|-------|
| id | UUID | all | Primary key |
| entity_id | UUID FK | all | → entities |
| label | VARCHAR(255) | all | Display name |
| wallet_type | VARCHAR(50) | all | STI discriminator |
| sync_status | VARCHAR(20) | all | IDLE/SYNCING/SYNCED/ERROR |
| chain | VARCHAR(20) | OnChain | ethereum, arbitrum, etc. |
| address | VARCHAR(255) | OnChain | Wallet address, indexed |
| last_block_loaded | BIGINT | OnChain | Resume point for sync |
| exchange | VARCHAR(20) | CEX | "binance" |
| api_key_encrypted | VARCHAR(500) | CEX | Fernet-encrypted |
| api_secret_encrypted | VARCHAR(500) | CEX | Fernet-encrypted |
| last_synced_at | TIMESTAMP | both | Last successful sync time |

### Transaction

Stores raw blockchain transaction data.

| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT | Auto-increment PK (high volume) |
| wallet_id | UUID FK | → wallets |
| chain | VARCHAR(20) | Chain identifier |
| tx_hash | VARCHAR(100) | Indexed; unique with wallet_id |
| block_number | BIGINT | |
| timestamp | BIGINT | Unix epoch seconds |
| from_addr | VARCHAR(50) | Sender |
| to_addr | VARCHAR(50) | Receiver / contract |
| value_wei | BIGINT | Native token value |
| gas_used | INTEGER | Gas consumed |
| status | VARCHAR(20) | LOADED → PARSED / ERROR / IGNORED |
| tx_data | TEXT | Full JSON: Etherscan response + token_transfers + internal_transfers |
| entry_type | VARCHAR(50) | Set after parsing (SWAP, TRANSFER, etc.) |

### Account (Single Table Inheritance)

9 subtypes: `native_asset`, `erc20_token`, `protocol_asset`, `protocol_debt`, `wallet_income`, `wallet_expense`, `external_transfer`, `cex_asset`, `manual_entry`.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| wallet_id | UUID FK | → wallets |
| account_type | VARCHAR(20) | ASSET / LIABILITY / INCOME / EXPENSE |
| subtype | VARCHAR(50) | STI discriminator |
| symbol | VARCHAR(50) | Token symbol |
| token_address | VARCHAR(255) | Contract address (ERC20) |
| protocol | VARCHAR(50) | aave_v3, uniswap_v3, etc. |
| balance_type | VARCHAR(20) | supply / borrow |
| label | VARCHAR(255) | Unique hierarchical key |

### JournalEntry & JournalSplit

Double-entry accounting records.

**JournalEntry:**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| entity_id | UUID FK | → entities |
| transaction_id | BIGINT FK | Nullable (CSV entries have none) |
| entry_type | VARCHAR(50) | EntryType enum value |
| description | TEXT | e.g. "AaveV3Parser: 0xabc..." |
| timestamp | TIMESTAMP | Transaction time |

**JournalSplit:**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| journal_entry_id | UUID FK | → journal_entries |
| account_id | UUID FK | → accounts |
| quantity | NUMERIC(38,18) | Positive = increase, negative = decrease |
| value_usd | NUMERIC(20,4) | USD value (nullable if price missing) |
| value_vnd | NUMERIC(24,0) | VND value (nullable) |

**Invariant:** For every JournalEntry, `SUM(quantity) = 0`, `SUM(value_usd) = 0`, `SUM(value_vnd) = 0`.

### ClosedLotRecord & OpenLotRecord

FIFO capital gains tracking.

**ClosedLotRecord** (realized gains):
- symbol, quantity, cost_basis_usd, proceeds_usd, gain_usd, holding_days
- buy_timestamp, sell_timestamp, buy_entry_id FK, sell_entry_id FK

**OpenLotRecord** (unrealized positions):
- symbol, remaining_quantity, cost_basis_per_unit_usd
- buy_timestamp, buy_entry_id FK

### PriceCache

Hourly token price cache.

| Column | Type | Notes |
|--------|------|-------|
| symbol | VARCHAR(50) | Token symbol |
| timestamp | TIMESTAMP | Hour-rounded |
| price_usd | NUMERIC(20,8) | USD price |
| source | VARCHAR(50) | coingecko / manual |

Unique constraint: `(symbol, timestamp)`

### ParseErrorRecord

Records parsing failures with diagnostic data.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| transaction_id | BIGINT FK | → transactions |
| wallet_id | UUID FK | → wallets |
| error_type | VARCHAR(50) | ParseErrorType enum |
| message | TEXT | Error message |
| stack_trace | TEXT | Python traceback |
| diagnostic_data | TEXT | JSON with contract_address, function_selector, transfers, parsers_attempted |
| resolved | BOOLEAN | Default false |

### CsvImport & CsvImportRow

Binance CSV import tracking.

**CsvImport:** entity_id, exchange, filename, row_count, parsed_count, error_count, status (uploaded/parsing/completed/error)

**CsvImportRow:** import_id, row_number, utc_time, account, operation, coin, change, remark, status, error_message, journal_entry_id FK

### ReportRecord

Generated report metadata.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| entity_id | UUID FK | → entities |
| period_start | TIMESTAMP | Report start date |
| period_end | TIMESTAMP | Report end date |
| status | VARCHAR(20) | generating / completed / failed |
| filename | VARCHAR(255) | Saved file path |
| generated_at | TIMESTAMP | |
| error_message | TEXT | Failure details |

---

## Parser System

### Parser Resolution Order

```
Layer 1: Protocol-specific parsers  → Contract address match (Aave, Uniswap, etc.)
Layer 2: GenericSwapParser          → Net-flow pattern: 1 token out + 1 token in
Layer 3: GenericEVMParser           → Fallback: gas fee + raw transfers
```

### ParserRegistry

`ParserRegistry` maps `(chain, contract_address) → [Parser]`.

```python
registry = ParserRegistry()
registry.register("ethereum", "0x87870...", AaveV3Parser())
registry.register_chain_parsers("ethereum", [GenericSwapParser(), GenericEVMParser()])

# Resolution: specific → chain-level fallback
parsers = registry.get("ethereum", "0x87870...")  # [AaveV3Parser, GenericSwapParser, GenericEVMParser]
```

`build_default_registry()` pre-registers all known protocol contracts across all supported chains.

### BaseParser Interface

```python
class BaseParser(ABC):
    PARSER_NAME: str
    ENTRY_TYPE: EntryType

    def can_parse(self, tx_data: dict, context: TransactionContext) -> bool: ...
    def parse(self, tx_data: dict, context: TransactionContext) -> ParseResult | None: ...
```

### TransactionContext

Mutable working set that parsers consume from:

```python
context = TransactionContext(wallet_address, transfers, events)
context.pop_transfer(from_addr, to_addr, transfer_type)  # Consume a matching transfer
context.net_flows()         # dict[address, dict[symbol, Decimal]]
context.pop_event(name)     # Consume a decoded event
context.remaining_transfers()  # Unconsumed transfers
context.remaining_events()     # Unconsumed events
```

### Generic Parsers

**GenericEVMParser** (Layer 3 fallback):
- Always matches (`can_parse` returns True)
- Creates gas expense split + one split per unconsumed transfer
- Sets `ENTRY_TYPE = TRANSFER`

**GenericSwapParser** (Layer 2):
- Matches when net_flows show exactly: wallet lost token A, wallet gained token B
- Creates swap journal entry: asset_A debit + asset_B credit
- Sets `ENTRY_TYPE = SWAP`

### Protocol-Specific Parsers

| Parser | Protocol | Chains | Operations |
|--------|----------|--------|------------|
| `AaveV3Parser` | Aave V3 | eth, arb, opt, polygon, base, avax | supply, withdraw, borrow, repay |
| `UniswapV3Parser` | Uniswap V3 | eth, arb, polygon, opt, base | swap, LP mint/burn/collect |
| `CurvePoolParser` | Curve | eth, arb, polygon | exchange, add/remove liquidity |
| `LidoParser` | Lido | eth (stETH), multi (wstETH) | stake, wrap, unwrap |
| `MorphoBlueParser` | Morpho Blue | eth, base | supply, withdraw, borrow, repay, collateral |
| `MetaMorphoVaultParser` | MetaMorpho | eth, base | ERC-4626 deposit/withdraw |
| `PancakeSwapParser` | PancakeSwap V3 | bsc, eth | swap (net-flow) |
| `PendleParser` | Pendle | eth, arb | swap PT/YT, mintSY, redeemSY, yield |

### CEX Parsers

| Parser | Source | Operations |
|--------|--------|------------|
| `BinanceTradeParser` | API | Spot trade (buy/sell + commission) |
| `BinanceDepositParser` | API | On-chain deposit |
| `BinanceWithdrawalParser` | API | Withdrawal with fee |
| `BinanceCsvParser` | CSV | 30+ operation types (trade, earn, futures, margin, loan, etc.) |

### Reusable Split Handlers

```python
# handlers/common.py
make_deposit_splits(symbol, quantity, protocol, ...)   → [asset_debit, protocol_credit]
make_withdrawal_splits(symbol, quantity, protocol, ...) → [protocol_debit, asset_credit]
make_borrow_splits(symbol, quantity, protocol, ...)    → [asset_credit, debt_debit]
make_repay_splits(symbol, quantity, protocol, ...)     → [asset_debit, debt_credit]
make_yield_splits(symbol, quantity, protocol, ...)     → [asset_credit, income_debit]

# handlers/wrap.py
make_wrap_splits(from_symbol, to_symbol, ...)   → [asset_from_debit, asset_to_credit]
make_unwrap_splits(from_symbol, to_symbol, ...) → [asset_from_debit, asset_to_credit]
```

---

## Accounting Engine

### Bookkeeper

The central orchestrator that converts raw transactions into journal entries.

**Flow:**
1. Load `tx_data` JSON from Transaction record
2. `extract_all_transfers()` — parse Etherscan data into `RawTransfer` list
3. Build `TransactionContext` with transfers + decoded events
4. Registry lookup → get ordered parser list for `(chain, to_address)`
5. Try each parser: `can_parse()` → `parse()` → get `ParseResult` with splits
6. `AccountMapper` — resolve each split's account (get-or-create)
7. `PriceService.price_split()` — add USD and VND values
8. Create `JournalEntry` + `JournalSplit` records
9. Validate balance (sum must equal zero)
10. On failure → record `ParseErrorRecord` with diagnostics

**Key method:** `process_wallet(wallet, entity_id) -> {processed, errors, total}`

### AccountMapper

Session-scoped cache that maps hierarchical label keys to Account records:

```
ethereum:0xabc...:native           → Account(type=ASSET, subtype=native_asset, symbol=ETH)
ethereum:0xabc...:erc20:0xdead:USDC → Account(type=ASSET, subtype=erc20_token, symbol=USDC)
ethereum:0xabc...:protocol:aave_v3:asset:USDC → Account(type=ASSET, subtype=protocol_asset)
ethereum:0xabc...:gas              → Account(type=EXPENSE, subtype=wallet_expense)
```

### FIFO Matching

`fifo_match(trades: list[Trade]) -> (closed_lots, open_lots)`

- Pure function, no database dependency
- Input: list of `Trade` objects (side=BUY/SELL, symbol, quantity, price, timestamp)
- Uses a `deque` as buy queue; oldest lots consumed first
- Returns closed lots (with gain/loss) and remaining open lots

### Tax Engine

`TaxEngine.calculate(entity_id, start, end) -> TaxSummary`

1. Load all journal splits for entity in date range
2. Convert splits to `Trade` objects, grouped by symbol
3. Run `fifo_match()` per symbol → closed lots + open lots
4. Compute transfer tax: 0.1% per outgoing asset transfer
5. Apply exemptions (configurable — e.g., transfers > VND 20M threshold)
6. Persist results (delete-then-insert for idempotency)
7. Return `TaxSummary` with realized gains, open lots, taxable transfers, totals

---

## Price Feed

### CoinGeckoProvider

- Maps 48+ token symbols to CoinGecko IDs
- Stablecoin shortcut: USDC, USDT, DAI, FRAX, etc. → `$1.00` (no API call)
- Historical price: queries 2-hour window around target timestamp
- Rate limit handling: exponential backoff on 429 (2s → 4s → 8s, max 3 retries)
- Supports both free tier and Pro API key

### PriceService

- **Cache-first:** check `price_cache` table → CoinGecko fetch → store in cache
- **`get_price(symbol, timestamp) -> Decimal`** — returns USD price
- **`price_split(symbol, quantity, timestamp) -> (value_usd, value_vnd)`** — sign-preserving multiplication

---

## API Reference

**Base URL:** `http://localhost:8000`
**CORS:** Allows `http://localhost:5173`

### Health Check

```
GET /api/health → {"status": "ok", "version": "0.1.0"}
```

### Entities

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/entities | List all entities (with wallet_count) |
| POST | /api/entities | Create entity `{name, base_currency}` |
| GET | /api/entities/{id} | Get entity |
| PATCH | /api/entities/{id} | Update entity |
| DELETE | /api/entities/{id} | Soft delete |

### Wallets

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/wallets | Add on-chain wallet `{entity_id, chain, address, label}` |
| POST | /api/wallets/cex | Add CEX wallet `{entity_id, exchange, api_key, api_secret, label}` |
| GET | /api/wallets | List wallets `?entity_id=` |
| DELETE | /api/wallets/{id} | Remove wallet |
| POST | /api/wallets/{id}/sync | Trigger Celery sync task |
| GET | /api/wallets/{id}/status | Get sync status |

### Transactions

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/transactions | List `?entity_id=&wallet_id=&chain=&status=&limit=&offset=` |
| GET | /api/transactions/{tx_hash} | Transaction detail |

### Parser

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/parse/test | Parse single TX hash `{tx_hash, persist}` |
| POST | /api/parse/wallet/{wallet_id} | Parse all LOADED TXs for wallet |
| GET | /api/parse/stats | `{total, parsed, errors, unknown}` |

### Journal

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/journal | List entries `?entity_id=&entry_type=&limit=&offset=` |
| GET | /api/journal/validation | List unbalanced entries |
| GET | /api/journal/{entry_id} | Entry + splits with account details |

### Accounts

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/accounts | List all accounts `?entity_id=&account_type=` |
| GET | /api/accounts/{id}/history | Splits for account (paginated) |

### Errors

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/errors | List parse errors `?entity_id=&error_type=&resolved=&contract_address=&function_selector=` |
| GET | /api/errors/summary | Count by error type `{total, by_type, resolved, unresolved}` |
| POST | /api/errors/{id}/retry | Re-parse this error's transaction |
| POST | /api/errors/{id}/ignore | Mark resolved, TX → IGNORED |
| POST | /api/errors/retry-group | Bulk re-parse by contract/function filter |

### Tax

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/tax/calculate | Run FIFO + tax `{entity_id, start_date, end_date}` |
| GET | /api/tax/realized-gains | List closed lots `?entity_id=` |
| GET | /api/tax/open-lots | List open positions `?entity_id=` |
| GET | /api/tax/summary | Aggregate tax summary `?entity_id=` |

### Reports

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/reports/generate | Generate Excel report `{entity_id, start_date, end_date}` |
| GET | /api/reports | List past reports `?entity_id=` |
| GET | /api/reports/{id}/status | Report generation status |
| GET | /api/reports/{id}/download | Download .xlsx file |

### Imports (CSV)

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/imports/upload | Upload CSV file (multipart) |
| GET | /api/imports | List imports `?entity_id=` |
| GET | /api/imports/{id} | Import detail |
| GET | /api/imports/{id}/rows | Import rows `?status=&limit=&offset=` |
| GET | /api/imports/{id}/summary | Operation counts + status breakdown |
| POST | /api/imports/{id}/parse | Parse all pending CSV rows |

### Common Patterns

- **Pagination:** `?limit=50&offset=0` (max 200)
- **Entity scoping:** Most endpoints accept `?entity_id=` query parameter
- **Response format:** `{items: [...], total: N}` for lists

---

## Frontend

### Architecture

- **React 18** with `react-router-dom` v6 for routing
- **TanStack Query 5** for server-state management (caching, refetching)
- **Tailwind CSS 3.4** for styling (no CSS modules)
- **lucide-react** for icons

### Pages (11 routes)

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `Dashboard` | Summary cards, quick actions, protocol coverage |
| `/entities` | `Entities` | Entity CRUD |
| `/imports` | `Imports` | CSV upload and import management |
| `/wallets` | `Wallets` | Wallet add/list/sync/delete |
| `/transactions` | `Transactions` | TX list with filters |
| `/parser` | `ParserDebug` | Parse test + coverage stats |
| `/journal` | `Journal` | Journal entries + expandable splits |
| `/accounts` | `Accounts` | Account tree + balances |
| `/errors` | `Errors` | Error dashboard with diagnostics |
| `/tax` | `Tax` | Tax calculator + results |
| `/reports` | `Reports` | Report generation + download |

### Shared Components

- `Layout` — Sidebar navigation + `<Outlet />` main content area
- `EntitySelector` — Global entity picker (persisted to localStorage)
- `EntityContext` — React context for active entity ID

### API Client

`api/client.ts` provides:
- `apiFetch<T>(path, options)` — typed fetch wrapper to `http://localhost:8000`
- `withEntityId(params)` — injects active entity_id into query params

### Hooks

Each hook wraps a TanStack Query call:
- `useWallets()`, `useTransactions()`, `useJournal()`, `useAccounts()`
- `useEntities()`, `useErrors()`, `useImports()`, `useParser()`
- `useReports()`, `useTax()`

---

## Workers & Task Queue

### Celery Configuration

```python
# celery_app.py
app = Celery("cryptotax")
app.config_from_object({
    "broker_url": settings.redis_url,
    "result_backend": settings.redis_url,
    "task_serializer": "json",
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
})
```

### sync_wallet_task

Async wallet synchronization dispatched by `POST /api/wallets/{id}/sync`.

Routes by wallet type:
- **OnChainWallet + EVM chain** → `EVMTxLoader` (Etherscan API)
- **OnChainWallet + Solana** → `SolanaTxLoader` (Helius/public RPC)
- **CEXWallet + Binance** → `BinanceLoader` (Binance REST API)

Creates its own engine + session (no sharing with FastAPI process).

---

## Report Generator

### Output Format: `bangketoan.xlsx`

14-sheet Excel workbook:

| Sheet | Content |
|-------|---------|
| summary | Key metrics (entity, period, gains, tax) |
| balance_sheet_by_qty | Account balances in token quantity |
| balance_sheet_by_value_USD | Account balances in USD |
| balance_sheet_by_value_VND | Account balances in VND |
| income_statement | Income/expense breakdown |
| flows_by_qty | Token quantity flows over time |
| flows_by_value_USD | USD value flows over time |
| realized_gains | FIFO closed lots |
| open_lots | Unrealized positions |
| journal | Full journal entry + split listing |
| tax_summary | Taxable transfers |
| warnings | Missing prices, unbalanced entries |
| wallets | Tracked wallets |
| settings | Report parameters |

### Pipeline

```
ReportService.generate(entity_id, start, end)
  → ReportDataCollector.collect()    # Queries all DB data
    → TaxEngine.calculate()          # Fresh FIFO run
  → ExcelWriter.write(data)          # openpyxl → .xlsx
  → Save to reports/{uuid}_{name}.xlsx
  → Create ReportRecord in DB
```

---

## Testing

### Test Stack

- **pytest** with `pytest-asyncio` (`asyncio_mode = "auto"`)
- **SQLite in-memory** for database tests (no PostgreSQL needed)
- **conftest.py** provides: `engine`, `session`, `create_tables` fixtures

### Test Structure

```
tests/
├── conftest.py            # Shared fixtures
├── fixtures/              # Real TX JSON from Etherscan
│   ├── aave_supply.json
│   ├── curve_exchange.json
│   ├── eth_transfer.json
│   ├── swap.json
│   └── uniswap_swap.json
├── unit/                  # ~40 test files
│   ├── accounting/        # fifo, tax_engine, account_mapper
│   ├── parser/            # Each protocol parser + generic parsers
│   ├── infra/             # Blockchain clients, CSV import
│   ├── price/             # CoinGecko, price cache, price service
│   └── report/            # Data collector, Excel writer
└── integration/           # ~10 test files
    ├── test_bookkeeper.py # Full TX → Journal pipeline
    ├── test_*_api.py      # FastAPI endpoint tests
    └── test_*_db.py       # Multi-model DB tests
```

### Running Tests

```bash
# All tests
python -m pytest tests/ -x -q

# Unit only
python -m pytest tests/unit/ -x -q

# Specific module
python -m pytest tests/unit/parser/ -x -q

# With coverage
python -m pytest tests/ --cov=src/cryptotax --cov-report=html
```

---

## Configuration

### Environment Variables

Copy `.env.example` → `.env` and fill in:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=leafjots

# Redis
REDIS_URL=redis://localhost:6379/0

# Blockchain APIs
ETHERSCAN_API_KEY=<your-key>       # Required for EVM TX loading
COINGECKO_API_KEY=<your-key>       # Optional (free tier works with rate limits)
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
HELIUS_API_KEY=<your-key>          # Recommended for Solana

# CEX (optional)
BINANCE_API_KEY=<your-key>
BINANCE_API_SECRET=<your-secret>

# Security
ENCRYPTION_KEY=<32-byte-fernet-key>
SECRET_KEY=<random-string>

# Settings
USD_VND_RATE=25000
DEBUG=true
```

### Alembic Migrations

```
alembic/versions/
├── 0964d9636ae2_initial_phase1_tables.py     # Core tables
├── phase2_add_last_synced_at.py              # Wallet sync tracking
├── phase3_extend_transactions.py             # TX detail columns
├── phase4_indexes.py                         # Performance indexes
├── 6080bbca93a1_phase5_to_9_complete.py      # Price, reports, capital gains, CEX
├── v2_001_add_diagnostic_data.py             # Error diagnostics
└── v3_001_csv_import_tables.py               # CSV import tables
```

---

## Deployment

### Local Development

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Run migrations
alembic upgrade head

# 3. Start backend (auto-reload)
uvicorn src.cryptotax.api.main:app --reload --port 8000

# 4. Start frontend (hot-reload)
cd web && npm run dev

# 5. (Optional) Start Celery worker
celery -A src.cryptotax.workers.celery_app worker -l info

# 6. Open browser
# http://localhost:5173
```

### Supported Chains

| Chain | Chain ID | Explorer |
|-------|----------|----------|
| Ethereum | 1 | etherscan.io |
| Arbitrum | 42161 | arbiscan.io |
| Optimism | 10 | optimistic.etherscan.io |
| Polygon | 137 | polygonscan.com |
| Base | 8453 | basescan.org |
| BSC | 56 | bscscan.com |
| Avalanche | 43114 | snowtrace.io |
| Solana | — | solscan.io |

### Supported Protocols

Aave V3, Uniswap V3, Curve, PancakeSwap V3, Morpho Blue, MetaMorpho, Lido, Pendle, Binance (API + CSV), Generic EVM, Generic Swap.
