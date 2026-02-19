# CLAUDE.md — LeafJots

> Claude Code: Đọc file này TRƯỚC, làm theo BOOTSTRAP khi user yêu cầu init.

---

## BOOTSTRAP — AUTO-SETUP INSTRUCTIONS

Khi user nói "init", "setup", "bắt đầu", "start", hoặc tương tự, thực hiện theo thứ tự:

### Step 1: Check prerequisites
```bash
node --version    # Cần >= 18
python3 --version # Cần >= 3.11
git --version
```
Nếu thiếu, DỪNG và báo user cài.

### Step 2: Init git + base structure
```bash
git init
mkdir -p src/cryptotax/{domain/{models,enums},db/{models,repos},infra/{blockchain/evm,blockchain/solana,price,http},parser/{generic,defi,cex,handlers,utils},accounting,report,api,workers}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p docs/reference
mkdir -p .planning/reference
mkdir -p web/{src/{components,pages,hooks,api},public}
touch src/cryptotax/__init__.py
```

### Step 3: Install GSD
```bash
npx get-shit-done-cc@latest
```
Nếu fail → skip, tiếp tục scaffold.

### Step 4: Create project files
Tạo files theo [PROJECT SCAFFOLD](#project-scaffold).

### Step 5: Install dependencies
```bash
# Backend
pip install -e ".[dev]" --break-system-packages

# Frontend
cd web && npm install && cd ..
```

### Step 6: Init GSD (nếu có)
`/gsd:new-project` với [GSD PROJECT DESCRIPTION](#gsd-project-description).

### Step 7: Report
Báo user: setup xong gì, thiếu gì, next steps.

---

## PROJECT IDENTITY

**Name:** LeafJots
**Mission:** Automated DeFi accounting — parse, classify, and report on-chain transactions
**Team:** 4 engineers + AI-assisted (Claude Code, Windsurf, Devin)

---

## WHY DEFI-FIRST

```
Sàn nội địa (MBBank, SSI, VIX...)  →  Tự thu thuế 0.1% thay user  →  KHÔNG CẦN tool
Binance/OKX (sàn ngoại)            →  Chưa rõ comply               →  NICE-TO-HAVE
DeFi (Uniswap, Aave, Curve...)     →  Không ai thu thuế được       →  MUST-HAVE ← FOCUS
```

---

## VIETNAM TAX RULES

```
Law:        Luật Công nghệ số (No. 71/2025/QH15)
Tax:        0.1% trên giá trị chuyển nhượng mỗi lần
Exemption:  Giao dịch đơn lẻ > VND 20M (~$800) được MIỄN
Filing:     Tự khai hàng năm, deadline 31/03
Method:     FIFO bắt buộc
Currency:   Dual: USD + VND
```

---

## ARCHITECTURE

### Core Flow
```
On-Chain TX → TX Loader → Parser Engine → Bookkeeper → Journal Entries
                                                ↓
                              Price Feed → Capital Gains (FIFO) → Tax (0.1%) → Report
                                                                                 ↓
                                                                          Local Web Dashboard
                                                                          (view, debug, export)
```

### Full System Architecture
```
┌─────────────────────────────────────────────────────────────────────┐
│                      LOCAL WEB DASHBOARD                            │
│  React + Vite (localhost:5173)                                      │
│  ┌──────────┬───────────┬──────────┬──────────┬──────────────────┐  │
│  │ Wallets  │ Tx Viewer │ Journal  │ Errors & │ Tax Report       │  │
│  │ Manager  │ & Parser  │ Entries  │ Warnings │ & Export         │  │
│  │          │ Debug     │          │          │                  │  │
│  └──────────┴───────────┴──────────┴──────────┴──────────────────┘  │
│         ↕ HTTP (localhost:8000/api)                                  │
├─────────────────────────────────────────────────────────────────────┤
│                      FASTAPI BACKEND                                │
│  ┌──────────┬───────────┬──────────┬──────────┬──────────────────┐  │
│  │ /wallets │ /txs      │ /journal │ /parse   │ /reports         │  │
│  │ CRUD     │ list/view │ entries  │ run/test │ generate/download│  │
│  │          │ filter    │ splits   │ debug    │                  │  │
│  └──────────┴───────────┴──────────┴──────────┴──────────────────┘  │
│         ↕                                                           │
├─────────────────────────────────────────────────────────────────────┤
│  Parser Engine │ Bookkeeper │ Tax Engine │ Price Feed │ Report Gen  │
├─────────────────────────────────────────────────────────────────────┤
│  PostgreSQL    │ Redis      │ Celery Workers                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Principles
1. **HORIZONTAL** — Generic parsers first (80%), specific only when needed
2. **CLEAN ARCHITECTURE** — Domain → Repository → Service → API
3. **DI** — dependency-injector. No singletons.
4. **CLEAN PATTERNS** — Domain-driven, well-tested.
5. **UI FROM DAY 1** — Local dashboard grows with each phase

### Tech Stack
```
Backend:   Python 3.11+  |  FastAPI  |  SQLAlchemy 2.0 async  |  PostgreSQL
Queue:     Celery + Redis
Blockchain: Web3.py  |  Pydantic v2  |  dependency-injector
Frontend:  React 18  |  Vite  |  Tailwind CSS  |  TanStack Query
           shadcn/ui components  |  Recharts (charts)
Testing:   pytest  |  Vitest
```

---

## LOCAL WEB DASHBOARD — PAGE SPECS

Dashboard grows incrementally. Each backend phase unlocks new UI pages.

### Page 1: Wallet Manager
```
Unlocked: Phase 2 (Domain Models)
Route:    /wallets

Features:
  - Add wallet (chain + address)
  - List all tracked wallets
  - Show sync status (last_block_loaded, last_synced_at)
  - Button: "Sync Now" → triggers TX loading
  - Show sync progress (Celery task status)

API endpoints:
  POST   /api/wallets              — add wallet
  GET    /api/wallets              — list wallets
  DELETE /api/wallets/{id}         — remove wallet
  POST   /api/wallets/{id}/sync    — trigger sync
  GET    /api/wallets/{id}/status  — sync progress
```

### Page 2: Transaction Viewer
```
Unlocked: Phase 3 (EVM Infrastructure)
Route:    /transactions

Features:
  - List all loaded transactions (paginated, filterable)
  - Filter by: wallet, chain, date range, status (parsed/unparsed/error)
  - Click TX → detail view:
    - Raw TX data (hash, block, from, to, value, gas)
    - Decoded events/logs
    - Transfer list (ERC20, native, NFT)
    - Link to block explorer
  - Badge: "Parsed ✓" / "Unparsed" / "Error ✗"

API endpoints:
  GET  /api/transactions                    — list (paginated + filters)
  GET  /api/transactions/{hash}             — detail
  GET  /api/transactions/{hash}/events      — decoded events
  GET  /api/transactions/{hash}/transfers   — extracted transfers
```

### Page 3: Parser Debug
```
Unlocked: Phase 4 (Parser Engine)
Route:    /parser

Features:
  - "Test Parse" input: paste TX hash → see parse result live
  - Show which parser was selected (Generic? Aave? Uniswap?)
  - Show resulting journal splits with accounts + amounts
  - Show balance check (sum = 0? ✓/✗)
  - Show warnings/errors if any
  - "Re-parse" button → re-run parser on specific TX
  - Bulk re-parse: re-process all TXs for a wallet

  Parser Stats panel:
  - Total TXs: 1,234
  - Parsed: 1,100 (89%)
  - Generic: 800 (73%)
  - Protocol-specific: 300 (27%)
  - Errors: 50 (4%)
  - Unknown: 84 (7%)

API endpoints:
  POST /api/parse/test          — parse single TX hash, return result
  POST /api/parse/wallet/{id}   — re-parse all TXs for wallet
  GET  /api/parse/stats         — parser coverage statistics
  GET  /api/parse/errors        — list parse errors
  GET  /api/parse/unknown       — list unknown/unclassified TXs
```

### Page 4: Journal Viewer
```
Unlocked: Phase 4 (Parser Engine)
Route:    /journal

Features:
  - List all journal entries (paginated)
  - Each entry shows: timestamp, description, entry_type, TX link
  - Expand entry → see all splits:
    - account | symbol | quantity | value (USD) | value (VND)
  - Color coding: Asset=blue, Liability=red, Income=green, Expense=orange
  - Balance validation indicator per entry (✓ balanced / ✗ unbalanced)
  - Filter by: date range, account type, symbol, protocol

API endpoints:
  GET  /api/journal                       — list entries
  GET  /api/journal/{id}                  — entry detail + splits
  GET  /api/journal/validation            — list unbalanced entries
```

### Page 5: Accounts & Balances
```
Unlocked: Phase 4
Route:    /accounts

Features:
  - Tree view of all accounts grouped by type:
    ASSET
    ├── Ethereum:Wallet1:Native (ETH): 1.5
    ├── Ethereum:Wallet1:ERC20:USDC: 2,500
    ├── Ethereum:Wallet1:Protocol:Aave:USDC: 10,000
    LIABILITY
    ├── Ethereum:Wallet1:Protocol:Aave:Debt:DAI: -5,000
    INCOME
    ├── Ethereum:Wallet1:Interest:Aave:USDC: -120
    EXPENSE
    ├── Ethereum:Wallet1:Gas Fees: 0.5
  - Click account → transaction history for that account
  - Balance at any date (date picker)
  - Reconciliation check: on-chain balance vs journal balance

API endpoints:
  GET  /api/accounts                      — list all accounts + balances
  GET  /api/accounts/{id}/history         — splits for this account
  GET  /api/accounts/reconciliation       — on-chain vs journal comparison
```

### Page 6: Error & Warning Dashboard
```
Unlocked: Phase 4
Route:    /errors

Features:
  - Tabs: Parse Errors | Unknown TXs | Price Missing | Unbalanced | Warnings
  
  Parse Errors:
    - TX hash, error message, stack trace, timestamp
    - Button: "Retry Parse" / "Mark Ignored"
  
  Unknown TXs:
    - TXs that GenericParser couldn't classify meaningfully
    - Show transfers detected, suggest classification
    - Button: "Classify As..." (swap, deposit, withdrawal, etc.)
  
  Price Missing:
    - Token + timestamp where price lookup failed
    - Button: "Enter Manual Price" / "Retry"
  
  Unbalanced Entries:
    - Journal entries where splits don't sum to 0
    - Show the imbalance amount
  
  Summary bar at top:
    🔴 12 Errors  |  🟡 84 Unknown  |  🟠 5 Missing Prices  |  🟢 1,100 OK

API endpoints:
  GET   /api/errors                 — all errors (filterable by type)
  POST  /api/errors/{id}/retry      — retry failed parse
  POST  /api/errors/{id}/ignore     — mark as ignored
  GET   /api/errors/summary         — counts by type
  POST  /api/prices/manual          — insert manual price
```

### Page 7: Tax Calculator
```
Unlocked: Phase 6 (Tax Engine)
Route:    /tax

Features:
  - Select entity + date range
  - "Calculate Tax" button → runs FIFO + 0.1% calculation
  - Results:
    - Realized gains summary (short/long term)
    - 0.1% tax per transfer (list)
    - Exempted transfers (> VND 20M)
    - Total tax due
  - Open lots view (unrealized positions)
  - Lot matching detail (which lot matched which sale)

API endpoints:
  POST /api/tax/calculate           — run tax calculation
  GET  /api/tax/realized-gains      — realized gains list
  GET  /api/tax/open-lots           — open lots
  GET  /api/tax/transfers           — all taxable transfers
  GET  /api/tax/summary             — total tax due
```

### Page 8: Reports & Export
```
Unlocked: Phase 7 (Report)
Route:    /reports

Features:
  - Select: entity, date range, options
  - "Generate Report" → creates bangketoan.xlsx
  - Download button: Excel / PDF
  - Preview: summary numbers inline
  - History of generated reports

API endpoints:
  POST /api/reports/generate        — create report (async)
  GET  /api/reports/{id}/status     — generation progress
  GET  /api/reports/{id}/download   — download file
  GET  /api/reports                 — list past reports
```

### Dashboard Home (/)
```
Unlocked: Phase 2+
Route:    /

Summary cards:
  - Wallets tracked: 5
  - Transactions loaded: 12,345
  - Parsed: 11,200 (91%)
  - Errors: 45
  - Last sync: 2 hours ago

Quick actions:
  - [Sync All Wallets]
  - [Run Tax Calculation]
  - [Generate Report]
  - [View Errors]

Charts (Phase 6+):
  - Portfolio value over time
  - Tax liability by month
```

---

## PROJECT STRUCTURE (updated with web/)

```
leafjots/
├── CLAUDE.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
│
├── src/cryptotax/                     # Python backend
│   ├── config.py
│   ├── container.py
│   ├── exceptions.py
│   ├── domain/{models,enums}/
│   ├── db/{models,repos,session.py}
│   ├── infra/{blockchain,price,http}/
│   ├── parser/{generic,defi,cex,handlers,utils}/
│   ├── accounting/
│   ├── report/
│   ├── api/                           # FastAPI
│   │   ├── main.py                    # FastAPI app + CORS for localhost:5173
│   │   ├── deps.py                    # DI dependencies
│   │   ├── wallets.py                 # /api/wallets
│   │   ├── transactions.py            # /api/transactions
│   │   ├── journal.py                 # /api/journal
│   │   ├── parser.py                  # /api/parse
│   │   ├── accounts.py                # /api/accounts
│   │   ├── errors.py                  # /api/errors
│   │   ├── tax.py                     # /api/tax
│   │   └── reports.py                 # /api/reports
│   └── workers/
│
├── web/                               # React frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts              # API client (fetch wrapper)
│       ├── hooks/
│       │   ├── useWallets.ts
│       │   ├── useTransactions.ts
│       │   └── ...
│       ├── components/
│       │   ├── Layout.tsx             # Sidebar + main content
│       │   ├── StatusBadge.tsx
│       │   ├── DataTable.tsx
│       │   ├── JournalSplits.tsx
│       │   └── ...
│       └── pages/
│           ├── Dashboard.tsx
│           ├── Wallets.tsx
│           ├── Transactions.tsx
│           ├── ParserDebug.tsx
│           ├── Journal.tsx
│           ├── Accounts.tsx
│           ├── Errors.tsx
│           ├── Tax.tsx
│           └── Reports.tsx
│
├── tests/
├── docs/reference/
├── docs/reference/                    # Distilled knowledge docs
└── .planning/
```

---

## PROJECT SCAFFOLD

### pyproject.toml
```toml
[project]
name = "leafjots"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "dependency-injector>=4.43",
    "web3>=7.6",
    "celery[redis]>=5.4",
    "redis>=5.2",
    "httpx>=0.28",
    "tenacity>=9.0",
    "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "ruff>=0.9",
    "mypy>=1.14",
]

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### web/package.json
```json
{
  "name": "leafjots-web",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3",
    "react-router-dom": "^6.28",
    "@tanstack/react-query": "^5.62",
    "recharts": "^2.14",
    "lucide-react": "^0.460",
    "clsx": "^2.1",
    "tailwind-merge": "^2.6"
  },
  "devDependencies": {
    "@types/react": "^18.3",
    "@types/react-dom": "^18.3",
    "@vitejs/plugin-react": "^4.3",
    "autoprefixer": "^10.4",
    "postcss": "^8.4",
    "tailwindcss": "^3.4",
    "typescript": "^5.7",
    "vite": "^6.0"
  }
}
```

### docker-compose.yml
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: cryptotax
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
volumes:
  pgdata:
```

### src/cryptotax/config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "cryptotax"
    redis_url: str = "redis://localhost:6379/0"
    alchemy_api_key: str = ""
    etherscan_api_key: str = ""
    coingecko_api_key: str = ""
    cryptocompare_api_key: str = ""
    secret_key: str = "change-me"
    debug: bool = True

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    class Config:
        env_file = ".env"

settings = Settings()
```

### src/cryptotax/exceptions.py
```python
class LeafJotsError(Exception): ...
class ParseError(LeafJotsError): ...
class PriceNotFoundError(LeafJotsError): ...
class BalanceError(LeafJotsError): ...
class TaxCalculationError(LeafJotsError): ...
class ExternalServiceError(LeafJotsError): ...
class ValidationError(LeafJotsError): ...
```

### Run commands
```bash
# Start infrastructure
docker compose up -d

# Start backend (port 8000)
uvicorn src.cryptotax.api.main:app --reload --port 8000

# Start frontend (port 5173)
cd web && npm run dev

# Start Celery worker
celery -A src.cryptotax.workers.celery_app worker -l info

# Open browser
# http://localhost:5173
```

---

## GENERIC-FIRST PARSER STRATEGY

```
Layer 1: GenericEVMParser     → auto-detect transfers, gas           → 60%
Layer 2: GenericSwapParser    → TokenA↔TokenB pattern                → 80%
Layer 3: Protocol-specific    → Aave/Uniswap LP/Curve (only these)  → 95%
Layer 4: Manual/AI classify   → unknown TXs flagged in dashboard     → 100%
```

---

## ACCOUNTING QUICK REFERENCE

```
SWAP 1 ETH → 2500 USDC:   asset_eth -1      | asset_usdc +2500
AAVE DEPOSIT 1000 USDC:   asset_usdc -1000   | protocol_aave +1000
AAVE BORROW 500 DAI:      asset_dai +500     | debt_aave -500
GAS 0.01 ETH:             asset_eth -0.01    | expense_gas +0.01
YIELD 10 USDC:            asset_usdc +10     | income -10
REPAY 500 DAI:            asset_dai -500     | debt_aave +500 (POSITIVE!)

Tax: configurable per-jurisdiction rules (transfer tax, capital gains, exemptions)
```

---

## REPORT FORMAT (bangketoan.xlsx)

```
summary | balance_sheet_by_qty | balance_sheet_by_value_USD | balance_sheet_by_value_VND
income_statement | flows_by_qty | flows_by_value_USD
realized_gains | open_lots | journal | tax_summary | warnings | wallets | settings
```

---

## GSD PROJECT DESCRIPTION

```
LeafJots — Automated DeFi Accounting Platform

Parses on-chain DeFi TXs into double-entry journals, FIFO capital gains,
and configurable tax rules.

Backend: Python 3.11, FastAPI, SQLAlchemy async, PostgreSQL, Celery+Redis,
Web3.py, Pydantic v2, dependency-injector.
Frontend: React 18, Vite, Tailwind, TanStack Query. Local web dashboard
for wallet management, TX viewing, parser debugging, error tracking,
tax calculation, and report export.

HORIZONTAL parser: GenericEVMParser 80% coverage, specific only for
Aave/Uniswap/Curve. DeFi-first (VN exchanges auto-withhold tax).

Output: Excel 12+ sheets. Team: 4 engineers, AI-assisted.
Clean architecture, well-tested codebase.
```

---

## PHASE ROADMAP (UI grows with each phase)

```
Phase 1: Foundation + Dashboard Shell                  Week 1
  Backend: scaffold, config, DI, DB, enums, pytest
  Frontend: Vite+React setup, Layout, sidebar nav, Dashboard home (empty state)
  Run: docker compose up → uvicorn → npm run dev → see empty dashboard

Phase 2: Domain Models + Wallet Manager                Week 2
  Backend: Transaction, Account, Journal, Token models, repos, migrations
  Backend: /api/wallets CRUD
  Frontend: Wallets page (add/list/delete wallets)
  Frontend: Dashboard cards (wallet count)

Phase 3: EVM Infrastructure + TX Viewer                Week 3
  Backend: Web3Provider, Etherscan, ABI, TX loader
  Backend: /api/wallets/{id}/sync, /api/transactions
  Frontend: Transactions page (list, filter, TX detail)
  Frontend: Sync button on wallets page

Phase 4: Parser Engine + Journal/Error Views           Week 3-4
  Backend: GenericEVM, GenericSwap, ParserEngine, ParserRegistry
  Backend: /api/parse, /api/journal, /api/accounts, /api/errors
  Frontend: Parser Debug page (test parse, stats)
  Frontend: Journal page (entries + splits view)
  Frontend: Accounts page (tree view + balances)
  Frontend: Errors page (parse errors, unknown TXs, missing prices)
  Frontend: Dashboard updates (parsed %, error count)

Phase 5: DeFi Protocol Parsers                         Week 4-5
  Backend: Aave V3, Uniswap V3, PancakeSwap, Curve parsers
  Frontend: Parser stats shows protocol breakdown
  Frontend: Parser Debug shows which parser selected

Phase 6: Price + Tax Engine                            Week 5-6
  Backend: CoinGecko, FIFO, 0.1% VN tax, VND 20M exemption
  Backend: /api/tax/*
  Frontend: Tax page (calculate, realized gains, open lots, tax due)
  Frontend: Dashboard chart (portfolio value over time)

Phase 7: Report Generator                              Week 6-7
  Backend: Excel output, /api/reports
  Frontend: Reports page (generate, download, history)
  Frontend: Dashboard "Generate Report" quick action

Phase 8: Multi-chain + Protocols                       Week 7-8
  Solana, BSC, Polygon, Arbitrum support
  Additional protocol parsers

Phase 9: CEX (optional)                                Parallel
  Binance for foreign exchange users
```

---

## CODING STANDARDS

```
Backend:  snake_case.py | PascalCase classes | UPPER enums | type hints always
          Async IO, Sync compute | Pydantic models | Repository pattern
          pytest | ruff | line length 120 | never bare except

Frontend: PascalCase.tsx components | camelCase functions/hooks
          TanStack Query for API | Tailwind for styling | no CSS modules
          pages/ = route-level | components/ = shared | hooks/ = data fetching
```

---

## DECISIONS LOG

| Decision | Choice | Why |
|----------|--------|-----|
| DeFi vs CEX first | DeFi-first | VN exchanges auto-withhold |
| Clone vs Rewrite | Clean rewrite | Domain knowledge preserved |
| Vertical vs Horizontal | Horizontal generic-first | Small team |
| Task queue | Celery + Redis | Community |
| FIFO scope | GLOBAL_FIFO per entity | VN requires |
| Frontend | React + Vite + Tailwind | Team knows React, fast dev |
| UI timing | From Phase 1 | Need to see/debug from start |

---

## REMEMBER

1. **DeFi is our moat.** CEX tax automated by exchanges.
2. **Generic first.** No specific parser unless generic fails.
3. **Clean patterns.** Domain-driven, well-tested.
4. **Every journal entry = $0.** Non-negotiable.
5. **Real transaction tests.** No mocks for accounting logic.
6. **UI from day 1.** Can't debug what you can't see.
