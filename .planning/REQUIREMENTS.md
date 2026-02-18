# Requirements: CryptoTax Vietnam — Milestone v2.0

**Defined:** 2026-02-18
**Core Value:** Correctly parse any DeFi transaction into balanced double-entry journal entries. If parsing is wrong, everything downstream (gains, tax, reports) is wrong.

## v1 Requirements

Requirements for milestone v2.0: Parser Diagnostics, Protocol Expansion, Multi-Chain.

### Parser Foundation

- [ ] **PFND-01**: ENTRY_TYPE class variable mutation bug is fixed — parsers return entry_type via ParseResult dataclass instead of mutating self.ENTRY_TYPE
- [ ] **PFND-02**: ParseResult dataclass replaces mutable ENTRY_TYPE pattern across all existing parsers (GenericEVM, GenericSwap, AaveV3, UniswapV3, Curve, PancakeSwap, Binance)
- [ ] **PFND-03**: Internal transactions loaded from Etherscan API during TX sync (native ETH from contract calls is currently missing)
- [ ] **PFND-04**: Protocol contract addresses centralized in addresses.py with ProtocolDeployment dataclass (replaces per-file hardcoded address dicts)
- [ ] **PFND-05**: Reusable wrap/unwrap handler created for token wrapping patterns (wstETH, SY tokens, etc.)

### Parser Diagnostics

- [ ] **DIAG-01**: ParseErrorRecord stores contract_address and function_selector for failed TXs
- [ ] **DIAG-02**: ParseErrorRecord stores detected_transfers (JSON) — all transfers found in the TX
- [ ] **DIAG-03**: ParseErrorRecord stores detected_events (JSON) — all decoded events found in the TX
- [ ] **DIAG-04**: ParseErrorRecord stores parsers_attempted (JSON) — list of parser names + match/decline reasons
- [ ] **DIAG-05**: Alembic migration adds diagnostic_data JSONB + contract_address + function_selector columns to parse_error_records table
- [ ] **DIAG-06**: Bookkeeper collects diagnostic data during parse attempt and stores it on error records
- [ ] **DIAG-07**: Function selector displayed as decoded function name in error and parser debug views (e.g., "0x617ba037 → supply()")

### Error Page & Grouping

- [ ] **ERRP-01**: Errors page loads without crashing (fix schema mismatch between backend ErrorSummaryResponse and frontend ErrorSummary)
- [ ] **ERRP-02**: Error summary shows counts by error type, resolved count, and unresolved count
- [ ] **ERRP-03**: Errors can be grouped by contract address (turns 500 errors into "3 contracts need parsers")
- [ ] **ERRP-04**: Errors can be grouped by function selector within a contract
- [ ] **ERRP-05**: Bulk retry endpoint re-parses all TXs matching a contract_address + function_selector filter
- [ ] **ERRP-06**: Expanded error detail shows transfer summary, event summary, and parsers attempted
- [ ] **ERRP-07**: GenericEVMParser ERC20 counterpart uses actual counterpart address instead of hardcoded "unknown"

### Morpho Protocol Parser

- [ ] **MRPH-01**: MorphoBlueParser handles supply and withdraw operations with correct journal entries
- [ ] **MRPH-02**: MorphoBlueParser handles borrow and repay operations with correct journal entries
- [ ] **MRPH-03**: MorphoBlueParser handles supplyCollateral and withdrawCollateral operations
- [ ] **MRPH-04**: MetaMorpho vault parser handles ERC-4626 deposit/withdraw
- [ ] **MRPH-05**: MORPHO added to Protocol enum
- [ ] **MRPH-06**: Morpho contract addresses registered in addresses.py (Ethereum mainnet)
- [ ] **MRPH-07**: Real TX test fixtures for Morpho Blue operations

### Lido Protocol Parser

- [ ] **LIDO-01**: LidoParser handles ETH staking via submit() → stETH
- [ ] **LIDO-02**: LidoParser handles wstETH wrap/unwrap (or verify GenericSwapParser handles it correctly)
- [ ] **LIDO-03**: LIDO added to Protocol enum
- [ ] **LIDO-04**: Lido contract addresses registered in addresses.py (Ethereum + L2s)
- [ ] **LIDO-05**: Real TX test fixtures for Lido staking and wstETH operations

### Multi-Chain Support

- [ ] **MCHN-01**: Arbitrum TX loading works via existing Etherscan v2 client (integration tested with real TXs)
- [ ] **MCHN-02**: Polygon TX loading works via existing Etherscan v2 client (integration tested with real TXs)
- [ ] **MCHN-03**: Arbitrum gas fee calculation is correct (including L1 data posting fee)
- [ ] **MCHN-04**: Polygon gas fee calculation is correct (MATIC/POL symbol verified)
- [ ] **MCHN-05**: Existing protocol parsers (Aave V3, Uniswap V3) work on Arbitrum and Polygon
- [ ] **MCHN-06**: Canonical token mapping (TokenRegistry) maps (chain, token_address) → canonical_symbol for cross-chain FIFO correctness

### Pendle Protocol Parser

- [ ] **PNDL-01**: PendleParser handles router swaps (PT↔token, YT↔token) with correct journal entries
- [ ] **PNDL-02**: PendleParser handles SY mint/redeem (standardized yield wrapping)
- [ ] **PNDL-03**: PendleParser handles YT yield claiming as income
- [ ] **PNDL-04**: PT/YT token identification registry maps Pendle token addresses to underlying symbols for pricing
- [ ] **PNDL-05**: PENDLE added to Protocol enum
- [ ] **PNDL-06**: Pendle contract addresses registered in addresses.py
- [ ] **PNDL-07**: Real TX test fixtures for Pendle operations

### Dashboard Polish

- [ ] **DASH-01**: Missing parser detection heatmap shows ranked view of unparsed contracts by TX count
- [ ] **DASH-02**: Parser coverage breakdown by protocol in Parser Debug stats
- [ ] **DASH-03**: Chain-specific block explorer links in TX detail view (Arbiscan, Polygonscan)

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Lido Extended

- **LIDO-V2-01**: stETH rebase yield tracking (detect balance changes from rebasing, record as income)
- **LIDO-V2-02**: Lido withdrawal queue parser (requestWithdrawals, claimWithdrawals)
- **LIDO-V2-03**: wstETH token mapping on L2s (Arbitrum/Polygon bridged addresses)

### Morpho Extended

- **MRPH-V2-01**: Morpho bundler v2/v3 multicall decoding
- **MRPH-V2-02**: Morpho MORPHO token rewards claiming parser

### Pendle Extended

- **PNDL-V2-01**: Pendle LP add/remove liquidity operations
- **PNDL-V2-02**: Pendle yield decomposition (PT vs YT tax treatment)
- **PNDL-V2-03**: PT maturity tracking and redemption accounting

### Advanced Diagnostics

- **DIAG-V2-01**: Live parse comparison mode (run multiple parsers, compare results side-by-side)
- **DIAG-V2-02**: Suggested parser for unknown contracts based on transfer pattern analysis
- **DIAG-V2-03**: Full 4-byte function selector dictionary (50K+ entries from 4byte.directory)

### Multi-Chain Extended

- **MCHN-V2-01**: Cross-chain position reconciliation (bridge TX detection)
- **MCHN-V2-02**: BSC chain support
- **MCHN-V2-03**: Base chain support

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-generate parsers from ABI | ABIs show function signatures, not accounting semantics. Would produce silently wrong journal entries. |
| Real-time parse-on-ingest | Parsing needs all related data loaded first (internal TXs, ERC20 transfers). Two-phase approach is correct. |
| AI-powered TX classification | LLMs hallucinate accounting entries. A wrong journal entry is worse than no entry. |
| stETH rebase from genesis | Historical backfill requires thousands of snapshots. Only track from wallet addition. |
| Per-chain separate parser registries | Most protocols deploy identical contracts across chains. One parser class, chain-specific addresses. |
| Mobile app | Web-first local tool. |
| Multi-user auth | Single-user local tool. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PFND-01 | Phase 1 | Pending |
| PFND-02 | Phase 1 | Pending |
| PFND-03 | Phase 1 | Pending |
| PFND-04 | Phase 1 | Pending |
| PFND-05 | Phase 1 | Pending |
| DIAG-01 | Phase 1 | Pending |
| DIAG-02 | Phase 1 | Pending |
| DIAG-03 | Phase 1 | Pending |
| DIAG-04 | Phase 1 | Pending |
| DIAG-05 | Phase 1 | Pending |
| DIAG-06 | Phase 2 | Pending |
| DIAG-07 | Phase 2 | Pending |
| ERRP-01 | Phase 2 | Pending |
| ERRP-02 | Phase 2 | Pending |
| ERRP-03 | Phase 2 | Pending |
| ERRP-04 | Phase 2 | Pending |
| ERRP-05 | Phase 2 | Pending |
| ERRP-06 | Phase 2 | Pending |
| ERRP-07 | Phase 2 | Pending |
| MRPH-01 | Phase 3 | Pending |
| MRPH-02 | Phase 3 | Pending |
| MRPH-03 | Phase 3 | Pending |
| MRPH-04 | Phase 3 | Pending |
| MRPH-05 | Phase 3 | Pending |
| MRPH-06 | Phase 3 | Pending |
| MRPH-07 | Phase 3 | Pending |
| LIDO-01 | Phase 4 | Pending |
| LIDO-02 | Phase 4 | Pending |
| LIDO-03 | Phase 4 | Pending |
| LIDO-04 | Phase 4 | Pending |
| LIDO-05 | Phase 4 | Pending |
| MCHN-01 | Phase 4 | Pending |
| MCHN-02 | Phase 4 | Pending |
| MCHN-03 | Phase 4 | Pending |
| MCHN-04 | Phase 4 | Pending |
| MCHN-05 | Phase 4 | Pending |
| MCHN-06 | Phase 4 | Pending |
| PNDL-01 | Phase 5 | Pending |
| PNDL-02 | Phase 5 | Pending |
| PNDL-03 | Phase 5 | Pending |
| PNDL-04 | Phase 5 | Pending |
| PNDL-05 | Phase 5 | Pending |
| PNDL-06 | Phase 5 | Pending |
| PNDL-07 | Phase 5 | Pending |
| DASH-01 | Phase 6 | Pending |
| DASH-02 | Phase 6 | Pending |
| DASH-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0

---
*Requirements defined: 2026-02-18*
*Last updated: 2026-02-18 after initial definition*
