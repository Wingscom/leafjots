# CryptoTax Vietnam

## What This Is

Automated DeFi tax accounting platform for Vietnam's 2026 crypto tax law (Law 71/2025/QH15). Parses on-chain DeFi transactions into double-entry journal entries, calculates FIFO capital gains, applies 0.1% transfer tax with VND 20M exemption, and generates Excel tax reports (bangketoan.xlsx). Local web dashboard for wallet management, TX viewing, parser debugging, error tracking, tax calculation, and report export.

## Core Value

Correctly parse any DeFi transaction into balanced double-entry journal entries. If parsing is wrong, everything downstream (gains, tax, reports) is wrong.

## Requirements

### Validated

- ✓ Domain models (Transaction, Account, JournalEntry, Wallet, Token) — Phase 1-2
- ✓ EVM TX loading via Etherscan v2 API — Phase 3
- ✓ Solana TX loading via RPC — Phase 8
- ✓ Generic EVM parser (transfers + gas) — Phase 4
- ✓ Generic Swap parser (token A↔B detection) — Phase 4
- ✓ Protocol parsers: Uniswap V3, Aave V3, Curve, PancakeSwap — Phase 5
- ✓ CEX parser: Binance — Phase 9
- ✓ Double-entry bookkeeper with balance validation — Phase 4
- ✓ FIFO capital gains engine — Phase 6
- ✓ 0.1% VN transfer tax with VND 20M exemption — Phase 6
- ✓ Price service (CoinGecko + cache) — Phase 6
- ✓ Excel report generator (14 sheets) — Phase 7
- ✓ FastAPI backend with 31+ endpoints — Phase 1-9
- ✓ React dashboard with 9 pages — Phase 1-9
- ✓ E2E test with real blockchain data — Phase 9
- ✓ ParseResult dataclass (replaces ENTRY_TYPE mutation) — v2.0 Phase 1
- ✓ Parser diagnostic data collection — v2.0 Phase 1-2
- ✓ Error page fix + diagnostic UI — v2.0 Phase 2
- ✓ Morpho Blue + MetaMorpho parsers — v2.0 Phase 3
- ✓ Lido stETH/wstETH parser — v2.0 Phase 4
- ✓ Pendle router/SY/YT parser — v2.0 Phase 5
- ✓ Block explorer links — v2.0 Phase 6
- ✓ Protocol coverage dashboard — v2.0 Phase 6

### Active

- [ ] Multi-entity client management (create/switch between clients: funds, individuals)
- [ ] Binance CSV import (48 operation types across 7 account types)
- [ ] Entity-scoped dashboard and all pages
- [ ] CEX CSV import model (raw storage + parsed journal entries)
- [ ] Multi-chain real TX testing (Arbitrum, Polygon) — deferred from v2.0
- [ ] TokenRegistry for cross-chain FIFO symbol mapping — deferred from v2.0

### Out of Scope

- Mobile app — web-first, local tool
- Real-time portfolio tracking — this is a tax tool, not a portfolio tracker
- AI-powered auto-classification — defer until manual parser coverage is solid
- End-user auth / login — admin-only for now, auth layer added later
- Multi-user permissions — single admin, multi-entity (not multi-user yet)

## Current Milestone: v3.0 Multi-Entity + CEX CSV Import

**Goal:** Transform from single-entity tool into multi-client platform with CEX CSV import support, so each client (fund/individual) has isolated wallets, transactions, journal entries, and tax reports.

**Target features:**
- Entity/Client CRUD — create, switch, manage multiple clients
- Entity-scoped UI — all pages filter by selected entity
- Binance CSV import — parse 48 operation types into journal entries
- CEX wallet type with CSV import tracking
- Database schema future-proof for auth layer later

## Context

- **Legacy codebase:** Ported patterns from Pennyworks/ChainCPA (~50K LOC). Knowledge gold, code broken.
- **Parser strategy:** Horizontal-first. GenericEVM ~60%, GenericSwap ~80%, protocol-specific for rest.
- **Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Celery+Redis, Web3.py, React 18, Vite, Tailwind
- **Current state:** 371 tests passing, 0 lint errors, 0 TS errors. 11 parsers active. E2E tested with real Ethereum data (19 TXs, 95% parse rate).
- **Milestones completed:** v1.0 (Phases 1-9, full platform), v2.0 (parser diagnostics, Morpho/Lido/Pendle)
- **Entity model:** Exists (UUID, name, base_currency) with wallet FK. All repos accept entity_id. API currently hardcodes get_default().
- **CEX wallet:** CEXWallet subtype exists. Binance API parser exists but NOT CSV parser.
- **Real CSV data:** legacy_code/docs/binance_export.csv — 340 rows, 48 op types, 7 account types, 21 coins

## Constraints

- **Tax law:** 0.1% per transfer, FIFO mandatory, VND 20M exemption, dual USD+VND
- **DeFi-first:** VN exchanges auto-withhold tax, DeFi is where the tool adds value
- **Parser accuracy:** Every journal entry must sum to $0 per symbol (non-negotiable)
- **Local-only:** Runs on localhost, no cloud deployment needed
- **API keys:** Etherscan (free), Alchemy, CoinGecko (free), Helius (optional, for Solana)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| DeFi-first over CEX | VN exchanges auto-withhold tax | ✓ Good |
| Horizontal parser strategy | Small team, cover more with less | ✓ Good |
| Rewrite over clone | Legacy broken, port patterns only | ✓ Good |
| ParseResult over mutable ENTRY_TYPE | Singletons in registry leaked state | ✓ Fixed in v2.0 |
| Addresses per-parser (not centralized) | Pragmatic, easy to maintain | ✓ Good |
| Lido staking as deposit (not swap) | stETH is rebasing, not a separate asset | ✓ Good |
| Pendle yield as income recognition | YT rewards are earned yield, not swaps | ✓ Good |
| Multi-chain deferred to v2.1 | Ethereum-only covers primary use case | — Pending |
| Admin-only multi-entity (no user auth) | Build core data isolation first, auth layer later | — Pending |
| Entity-scoped API via header/dropdown | Simpler than URL-based tenancy for local tool | — Pending |

---
*Last updated: 2026-02-18 after milestone v3.0 initialization*
