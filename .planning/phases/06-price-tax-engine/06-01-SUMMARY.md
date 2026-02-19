# Phase 6 Plan 01: Price + Tax Engine -- Summary

## One-liner
CoinGecko price service with cache, FIFO capital gains engine (GLOBAL_FIFO per entity), Vietnam 0.1% transfer tax with VND 20M exemption, Tax API (5 endpoints), and frontend Tax page with realized gains, open lots, and tax summary.

## What Was Built

### Backend — Price Infrastructure
- **PriceCache model**: DB-backed cache for historical prices (symbol, timestamp, price_usd, source)
- **CoinGeckoClient**: Rate-limited API client with symbol-to-ID mapping, fallback to daily prices
- **PriceService**: Cache-first lookup — check DB cache -> call CoinGecko -> persist result

### Backend — Tax Engine
- **FIFO engine** (`fifo.py`):
  - Pure function `fifo_match()` — GLOBAL_FIFO lot matching per entity
  - `trades_from_splits()` — converts journal splits to Trade events
  - Calculates: gain_usd, cost_basis, proceeds, holding_days per closed lot
  - Per-symbol lot queue tracking
- **Tax engine** (`tax_engine.py`):
  - Orchestrates: load journal splits -> FIFO match -> Vietnam 0.1% tax
  - Vietnam tax rules:
    - `TAX_RATE = 0.001` (0.1% per transfer)
    - `EXEMPTION_THRESHOLD_VND = 20,000,000` (~$800)
    - Exempt transfers where single value > VND 20M
  - Persists ClosedLotRecord + OpenLotRecord to DB

### Backend — API (5 new endpoints)
- **POST /api/tax/calculate**: Run full FIFO + tax calculation for entity + date range
- **GET /api/tax/realized-gains**: List closed lots with gain/loss
- **GET /api/tax/open-lots**: Current unrealized positions
- **GET /api/tax/transfers**: All taxable transfers with exemption status
- **GET /api/tax/summary**: Total tax due (VND + USD)

### Frontend
- **Tax.tsx**: Entity + date range picker, "Calculate Tax" button, results display:
  - Realized gains summary (total gain, short/long term breakdown)
  - Transfer tax table (0.1% per transfer, exemption markers)
  - Open lots table (unrealized positions)
  - Total tax due display
- **Dashboard.tsx**: Added portfolio value chart (Recharts) and tax summary card

## Key Decisions
- GLOBAL_FIFO per entity (as required by Vietnam tax law, not per-wallet)
- Price cache in DB (not in-memory) for persistence across restarts
- CoinGecko as primary price source (free tier sufficient for MVP)
- Tax exemption applied per individual transfer (not aggregated)
- VND conversion using configurable USD/VND rate from settings

## Files Created
~21 files across models, accounting, infra, API, frontend, and tests.
