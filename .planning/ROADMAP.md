# Roadmap: CryptoTax Vietnam -- Milestone v2.0

## Overview

Milestone v2.0 transforms CryptoTax from a working Ethereum-only parser into a diagnostic-rich, multi-protocol, multi-chain platform. The work follows a deliberate sequence: fix the parser foundation and build diagnostic observability first (Phases 1-2), then leverage that tooling to build three new protocol parsers (Morpho, Lido, Pendle) in decreasing order of confidence (Phases 3-5), with multi-chain verification running alongside Lido where the infrastructure overlap is natural (Phase 4). Dashboard polish caps the milestone (Phase 6). Every phase delivers observable capability -- no horizontal slicing.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Parser Foundation & Diagnostics Infrastructure** - Fix ENTRY_TYPE bug, introduce ParseResult dataclass, DiagnosticCollector, centralized addresses, internal TX loading, wrap handler
- [ ] **Phase 2: Diagnostic UI & Error Grouping** - Bookkeeper diagnostic integration, error grouping API, enriched Error page, function selector decoding
- [ ] **Phase 3: Morpho Blue Parser** - MorphoBlueParser + MetaMorpho vault parser with real TX test fixtures
- [ ] **Phase 4: Lido wstETH & Multi-Chain Verification** - LidoParser, Arbitrum/Polygon integration testing, TokenRegistry for cross-chain FIFO
- [ ] **Phase 5: Pendle Parser** - PendleParser for router swaps, SY mint/redeem, YT yield claiming, PT/YT token identification
- [ ] **Phase 6: Dashboard Polish & Extended Features** - Missing parser heatmap, coverage stats by protocol, chain-specific explorer links

## Phase Details

### Phase 1: Parser Foundation & Diagnostics Infrastructure
**Goal**: Parsers produce structured results without mutable state bugs, and every parse failure captures rich diagnostic context (contract, function, transfers, events, parsers tried)
**Depends on**: Nothing (first phase)
**Requirements**: PFND-01, PFND-02, PFND-03, PFND-04, PFND-05, DIAG-01, DIAG-02, DIAG-03, DIAG-04, DIAG-05
**Success Criteria** (what must be TRUE):
  1. All existing parsers return a ParseResult dataclass instead of mutating self.ENTRY_TYPE -- running the full test suite confirms no ENTRY_TYPE class variable mutation
  2. When a TX fails to parse, the resulting ParseErrorRecord contains the contract address, function selector, detected transfers, detected events, and list of parsers attempted with decline reasons
  3. Internal transactions (native ETH from contract calls) are loaded during TX sync and visible in the transaction detail view
  4. Protocol contract addresses for all supported protocols are defined in a single addresses.py file and no parser file contains hardcoded address dictionaries
  5. A reusable wrap/unwrap handler exists that can produce correct journal entries for any token wrapping pattern (tested with at least one wrapping scenario)
**Plans**: TBD

Plans:
- [ ] 01-01: TBD
- [ ] 01-02: TBD

### Phase 2: Diagnostic UI & Error Grouping
**Goal**: Developers can see exactly why any TX failed to parse, group errors by contract/function to prioritize parser work, and bulk-retry after fixes
**Depends on**: Phase 1
**Requirements**: DIAG-06, DIAG-07, ERRP-01, ERRP-02, ERRP-03, ERRP-04, ERRP-05, ERRP-06, ERRP-07
**Success Criteria** (what must be TRUE):
  1. The Errors page loads without crashing and displays error summary counts (by type, resolved, unresolved)
  2. Errors can be grouped by contract address, revealing which contracts need parsers (e.g., "500 errors" becomes "3 contracts need parsers")
  3. Drilling into a contract group shows errors grouped by function selector, with decoded function names (e.g., "0x617ba037 -> supply()")
  4. Expanding a single error shows transfer summary, event summary, and the list of parsers that attempted and declined with reasons
  5. Bulk retry re-parses all TXs matching a contract+function filter, and re-parsed TXs move out of the error list if successful
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Morpho Blue Parser
**Goal**: Morpho Blue lending and MetaMorpho vault transactions produce correct double-entry journal entries
**Depends on**: Phase 1 (addresses.py, ParseResult pattern)
**Requirements**: MRPH-01, MRPH-02, MRPH-03, MRPH-04, MRPH-05, MRPH-06, MRPH-07
**Success Criteria** (what must be TRUE):
  1. A Morpho Blue supply TX produces journal entries that move tokens from the user's asset account to a Morpho protocol account, and the entry sums to zero
  2. Morpho Blue borrow, repay, supplyCollateral, and withdrawCollateral each produce correctly balanced journal entries following the same accounting patterns as the existing Aave V3 parser
  3. A MetaMorpho vault deposit/withdraw (ERC-4626 pattern) produces correct journal entries distinguishing vault shares from underlying tokens
  4. MORPHO appears in the Protocol enum and Morpho contract addresses are registered in addresses.py
  5. Each Morpho operation type has at least one real TX test fixture that passes end-to-end (load TX, parse, verify journal balance)
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Lido wstETH & Multi-Chain Verification
**Goal**: Lido staking/wrapping transactions parse correctly, and existing parsers work on Arbitrum and Polygon with correct gas fees and cross-chain FIFO
**Depends on**: Phase 1 (addresses.py, wrap handler), Phase 3 (validates multi-protocol pattern)
**Requirements**: LIDO-01, LIDO-02, LIDO-03, LIDO-04, LIDO-05, MCHN-01, MCHN-02, MCHN-03, MCHN-04, MCHN-05, MCHN-06
**Success Criteria** (what must be TRUE):
  1. An ETH staking TX via Lido submit() produces a journal entry converting ETH to stETH in the user's asset accounts
  2. wstETH wrap/unwrap produces correct journal entries (either via LidoParser or verified GenericSwapParser with protocol attribution)
  3. Arbitrum TXs load via Etherscan v2 and parse with existing parsers (Aave V3, Uniswap V3), with L1 data posting fee included in gas calculation
  4. Polygon TXs load via Etherscan v2 and parse with existing parsers, with correct gas token symbol (MATIC or POL)
  5. The TokenRegistry maps (chain, token_address) to canonical_symbol so that USDC on Ethereum, Arbitrum, and Polygon all resolve to the same symbol for FIFO lot matching
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Pendle Parser
**Goal**: Pendle router swaps, SY operations, and YT yield claiming produce correct journal entries with proper PT/YT token identification
**Depends on**: Phase 1 (addresses.py, ParseResult), Phase 2 (diagnostics for debugging novel parser)
**Requirements**: PNDL-01, PNDL-02, PNDL-03, PNDL-04, PNDL-05, PNDL-06, PNDL-07
**Success Criteria** (what must be TRUE):
  1. A Pendle router swap (PT or YT traded for underlying token) produces a correctly balanced journal entry with the Pendle protocol identified
  2. SY mint (deposit underlying to get SY token) and SY redeem (burn SY to get underlying) produce correct wrap/unwrap-style journal entries
  3. YT yield claiming produces a journal entry recognizing the claimed amount as income
  4. PT and YT token addresses are mapped to their underlying symbols so the price service can value them correctly
  5. Each Pendle operation type has at least one real TX test fixture that passes end-to-end
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

### Phase 6: Dashboard Polish & Extended Features
**Goal**: The dashboard surfaces parser coverage gaps and supports multi-chain navigation
**Depends on**: Phase 2 (error data), Phase 4 (multi-chain data)
**Requirements**: DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. A heatmap/ranked view on the Parser Debug page shows unparsed contracts ordered by TX count, making it obvious which contract to build a parser for next
  2. Parser Debug stats break down parsed TX counts by protocol (Generic, Aave, Uniswap, Morpho, Lido, Pendle, etc.)
  3. TX detail view shows chain-appropriate block explorer links (Etherscan for Ethereum, Arbiscan for Arbitrum, Polygonscan for Polygon)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Parser Foundation & Diagnostics Infrastructure | 0/0 | Not started | - |
| 2. Diagnostic UI & Error Grouping | 0/0 | Not started | - |
| 3. Morpho Blue Parser | 0/0 | Not started | - |
| 4. Lido wstETH & Multi-Chain Verification | 0/0 | Not started | - |
| 5. Pendle Parser | 0/0 | Not started | - |
| 6. Dashboard Polish & Extended Features | 0/0 | Not started | - |
