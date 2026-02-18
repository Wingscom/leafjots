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
- ✓ FastAPI backend with 31 endpoints — Phase 1-9
- ✓ React dashboard with 9 pages — Phase 1-9
- ✓ E2E test with real blockchain data — Phase 9

### Active

- [ ] Fix Errors page crash (schema mismatch frontend/backend)
- [ ] Parser diagnostic data (rich error info: contract, function, transfers, parsers tried)
- [ ] Fix parser bugs (ENTRY_TYPE mutation, ERC20 counterpart)
- [ ] Lido (stETH) parser — liquid staking wrap/unwrap
- [ ] Morpho parser — yield optimization vaults
- [ ] Pendle parser — PT/YT token handling
- [ ] Multi-chain: Arbitrum support
- [ ] Multi-chain: Polygon support
- [ ] Improve parser coverage beyond current ~80%

### Out of Scope

- Mobile app — web-first, local tool
- Real-time portfolio tracking — this is a tax tool, not a portfolio tracker
- BSC/Base chains — defer to later milestone
- AI-powered auto-classification — defer until manual parser coverage is solid
- Multi-user auth — single-user local tool

## Context

- **Legacy codebase:** Ported patterns from Pennyworks/ChainCPA (~50K LOC). Knowledge gold, code broken.
- **Parser strategy:** Horizontal-first. GenericEVMParser covers ~60%, GenericSwapParser reaches ~80%, protocol-specific for the rest.
- **Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Celery+Redis, Web3.py, React 18, Vite, Tailwind
- **Current state:** 341 tests passing, 0 lint errors, 0 TS errors. E2E tested with real Ethereum data (19 TXs, 95% parse rate).
- **Known bugs:** Errors page white screen (schema mismatch), ENTRY_TYPE class variable mutation in parsers, ERC20 counterpart hardcoded to "unknown"

## Constraints

- **Tax law:** 0.1% per transfer, FIFO mandatory, VND 20M exemption, dual USD+VND
- **DeFi-first:** VN exchanges auto-withhold tax, DeFi is where the tool adds value
- **Parser accuracy:** Every journal entry must sum to $0 per symbol (non-negotiable)
- **Local-only:** Runs on localhost, no cloud deployment needed
- **API keys:** Etherscan (free), Alchemy, CoinGecko (free), Solana public RPC (rate limited)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| DeFi-first over CEX | VN exchanges auto-withhold tax | ✓ Good |
| Horizontal parser strategy | Small team, cover more with less | ✓ Good |
| Rewrite over clone | Legacy broken, port patterns only | ✓ Good |
| Parser diagnostics priority | Need to know WHY TX fails before writing new parsers | — Pending |
| Lido + Morpho + Pendle protocols | User's DeFi usage pattern | — Pending |
| Arbitrum + Polygon chains | L2s share Etherscan v2 API | — Pending |

---
*Last updated: 2026-02-18 after milestone v2.0 initialization*
