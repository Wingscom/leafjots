# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Correctly parse any DeFi transaction into balanced double-entry journal entries. If parsing is wrong, everything downstream (gains, tax, reports) is wrong.
**Current focus:** Milestone v3.0 — Multi-Entity + CEX CSV Import

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-02-18 — Milestone v3.0 started

Progress: [░░░░░░░░░░] 0%

## Overall Project Stats

| Metric | Value |
|--------|-------|
| Tests passing | 371 |
| Lint errors | 0 |
| TypeScript errors | 0 |
| Backend parsers | 11 |
| API endpoints | 31+ |
| Web pages | 9 |
| Alembic migrations | base + v2_001 |

## Accumulated Context

### Decisions Made (from v1.0 + v2.0)

- ParseResult dataclass pattern chosen over resetting ENTRY_TYPE at top of parse()
- Morpho selectors hardcoded (singleton contract, stable ABI)
- Lido staking modeled as ETH→protocol_asset (not swap) since stETH is rebasing
- Pendle yield claiming modeled as income recognition
- Addresses kept per-parser (not centralized) — pragmatic, easy to maintain
- Entity model exists with soft delete, wallet FK, journal FK — repos accept entity_id
- API currently uses get_default() — needs scoping for v3.0

### Known Limitations / Concerns

- All API endpoints hardcode get_default() entity — must be parameterized
- CEXWallet subtype exists but only for API-fetched trades, not CSV import
- Binance CSV has no TX ID — must group by (timestamp, account, coin)
- Multi-chain gas calculation not yet implemented
- No git commits yet — entire project is untracked

## Session Continuity

Last session: 2026-02-18
Stopped at: Milestone v3.0 initialization — defining requirements
Resume file: None
