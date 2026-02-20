# LeafJots

Automated DeFi accounting platform. Parses on-chain transactions into double-entry journal entries, computes FIFO capital gains, and exports multi-sheet Excel reports.

## Features

- **Multi-chain support** — Ethereum, Arbitrum, Optimism, Polygon, Base, BSC, Avalanche, Solana
- **11 transaction parsers** — Aave V3, Uniswap V3, Curve, PancakeSwap, Morpho Blue, MetaMorpho, Lido, Pendle, Binance (API + CSV), Generic EVM, Generic Swap
- **Double-entry accounting** — Every journal entry balances to zero
- **FIFO capital gains** — Global FIFO lot matching per entity per symbol
- **Configurable tax rules** — Transfer tax with exemption thresholds
- **14-sheet Excel reports** — Balance sheets, income statement, realized gains, open lots, journal, tax summary
- **Local web dashboard** — React frontend for managing wallets, viewing transactions, debugging parsers, and exporting reports
- **CEX integration** — Binance API + CSV import (30+ operation types including trades, earn, futures, margin, loans)
- **Price feed** — CoinGecko with rate-limit retry and DB caching

## Quick Start

### Prerequisites

- Python >= 3.11
- Node.js >= 18
- Docker (for PostgreSQL + Redis)

### Setup

```bash
# 1. Clone and install
git clone https://github.com/Wingscom/leafjots.git && cd leafjots
pip install -e ".[dev]"
cd web && npm install && cd ..

# 2. Configure environment
cp .env.example .env
# Edit .env — add your API keys (ETHERSCAN_API_KEY required for EVM chains)
# Or get the shared .env from team Drive (has all keys pre-filled)

# 3. Start infrastructure (PostgreSQL:5433, Redis:6380)
docker compose up -d

# 4. Run database migrations
alembic upgrade head

# 5. (Optional) Import shared DB dump — skip if starting fresh
docker compose exec -T db psql -U postgres -d leafjots < leafjots_dump.sql

# 6. Start backend
uvicorn src.cryptotax.api.main:app --reload --port 8000

# 7. Start frontend (separate terminal)
cd web && npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Team Setup (shared env + data)

Team Drive chứa 2 file cần copy vào project root:

| File | Mô tả |
|------|--------|
| `.env` | API keys (Alchemy, Etherscan, CoinGecko, Helius) — thay cho bước 2 |
| `leafjots_dump.sql` | DB dump có sẵn data mẫu (395 TXs, 478 journal entries) — dùng ở bước 5 |

> **Port note:** LeafJots dùng PostgreSQL port **5433** và Redis port **6380** (không phải default) để tránh conflict với các project khác.

### First Steps

1. **Create an Entity** — represents a person or organization
2. **Add a Wallet** — enter an EVM address or import a Binance CSV
3. **Sync & Parse** — load transactions from the blockchain, then parse into journal entries
4. **Calculate & Export** — run FIFO matching and download reports

## Architecture

```
On-Chain TX → TX Loader → Parser Engine → Bookkeeper → Journal Entries
                                                ↓
                              Price Feed → Capital Gains (FIFO) → Tax → Report
```

| Layer | Stack |
|-------|-------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16 |
| Task Queue | Celery + Redis |
| Blockchain | web3.py, Etherscan v2 API, Solana RPC |
| Frontend | React 18, Vite 6, Tailwind CSS, TanStack Query |
| Testing | pytest, pytest-asyncio, SQLite in-memory |

## Parser Strategy

Horizontal-first: generic parsers handle ~80% of transactions automatically.

```
Layer 1: GenericEVMParser     → auto-detect transfers + gas fee       → 60% coverage
Layer 2: GenericSwapParser    → token A ↔ token B pattern             → 80% coverage
Layer 3: Protocol-specific    → Aave, Uniswap, Curve, Lido, etc.     → 95% coverage
Layer 4: Error dashboard      → unknown TXs flagged for review        → 100% coverage
```

## API

RESTful API at `http://localhost:8000`. Key endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `POST /api/entities` | Create entity |
| `POST /api/wallets` | Add wallet |
| `POST /api/wallets/{id}/sync` | Sync wallet (Celery task) |
| `GET /api/transactions` | List transactions |
| `POST /api/parse/wallet/{id}` | Parse all loaded TXs |
| `GET /api/journal` | List journal entries |
| `GET /api/accounts` | List accounts + balances |
| `GET /api/errors` | List parse errors with diagnostics |
| `POST /api/tax/calculate` | Run FIFO + tax calculation |
| `POST /api/reports/generate` | Generate Excel report |
| `POST /api/imports/upload` | Upload Binance CSV |

Full API reference in [TECHNICAL.md](TECHNICAL.md#api-reference).

## Testing

```bash
# Run all tests
python -m pytest tests/ -x -q

# Unit tests only
python -m pytest tests/unit/ -x -q

# With coverage
python -m pytest tests/ --cov=src/cryptotax --cov-report=html

# Lint
ruff check src/

# TypeScript check
cd web && npx tsc --noEmit
```

## E2E Test

```bash
# Requires ETHERSCAN_API_KEY in .env
PYTHONPATH=src python scripts/e2e_test.py
```

Runs the full pipeline: create entity → add wallet → load TXs → parse → calculate tax → generate report.

## Project Structure

```
src/cryptotax/          # Backend
  ├── api/              # FastAPI endpoints + schemas
  ├── accounting/       # Bookkeeper, FIFO, tax engine
  ├── parser/           # 11 transaction parsers
  ├── infra/            # Blockchain, CEX, price, HTTP clients
  ├── db/               # Models + repositories
  ├── domain/           # Enums + domain models
  ├── report/           # Excel report generator
  └── workers/          # Celery tasks

web/src/                # Frontend
  ├── pages/            # 11 page components
  ├── hooks/            # TanStack Query hooks
  ├── api/              # API client modules
  └── components/       # Shared components

tests/                  # Test suite
  ├── unit/             # ~40 unit test files
  ├── integration/      # ~10 integration tests
  └── fixtures/         # Real TX JSON fixtures
```

## Documentation

- [TECHNICAL.md](TECHNICAL.md) — Full technical documentation (architecture, schema, API, parser details)
- [CLAUDE.md](CLAUDE.md) — AI assistant instructions and project context

## License

Proprietary. All rights reserved.
