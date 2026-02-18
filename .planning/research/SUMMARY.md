# Project Research Summary

**Project:** CryptoTax Vietnam -- Milestone v2: Parser Diagnostics, Protocol Expansion, Multi-Chain
**Domain:** DeFi tax accounting -- parser system extension
**Researched:** 2026-02-18
**Confidence:** MEDIUM-HIGH (high for codebase-derived findings, medium for protocol specifics from training data)

## Executive Summary

This milestone extends CryptoTax Vietnam's parser system across three axes: diagnostic observability, new protocol parsers (Lido, Morpho Blue, Pendle), and multi-chain support (Arbitrum, Polygon). The foundational insight across all four research dimensions is that **no new libraries are needed** -- the existing stack (web3.py, SQLAlchemy, FastAPI, React) covers every requirement. The work is entirely architectural: richer data models, new parser classes following established patterns, and centralized address configuration. The existing codebase already has Arbitrum and Polygon infrastructure (Etherscan v2, Chain enum, gas utils, protocol addresses) making multi-chain the lowest-effort axis.

The recommended approach is to fix the parser base layer first (the ENTRY_TYPE mutable state bug is confirmed across 4 parser files and will propagate to every new parser if not addressed), then build diagnostic data capture into the Bookkeeper, then add protocol parsers in order of decreasing confidence: Morpho Blue (HIGH -- legacy code provides full reference), Lido wstETH (MEDIUM -- simple wrap/unwrap, defer rebasing), Pendle (LOW -- most complex, least reference material). Multi-chain verification runs in parallel with Lido since the infrastructure already exists.

The key risks are: (1) Pendle's three-token model (SY/PT/YT) does not map to standard swap/deposit/withdraw primitives -- rushing a parser will produce silently wrong accounting; (2) stETH rebasing creates income that has no on-chain transaction, requiring a fundamentally new accounting pattern beyond event-driven parsing; (3) cross-chain FIFO requires canonical token mapping before adding the second chain or capital gains calculations will be wrong. All three can be mitigated by deferring the hardest parts (stETH rebase, Pendle yield decomposition, cross-chain reconciliation) to v2 while shipping the 80% cases now.

## Key Findings

### Recommended Stack

No new dependencies. The existing `pyproject.toml` covers all requirements. `eth-abi` and `eth-utils` are already installed as `web3.py` transitive dependencies and provide ABI decoding needed for diagnostics. PostgreSQL JSONB (via SQLAlchemy `mapped_column(JSON)`) stores diagnostic payloads. The only tooling additions are Alembic migrations for new columns and pytest fixtures for real protocol transactions.

**Core technologies (all existing):**
- **SQLAlchemy JSONB columns**: Store structured diagnostic payloads alongside ParseErrorRecord -- no separate diagnostic table needed
- **eth-abi (via web3.py)**: Decode function selectors and event data for diagnostic display
- **Pydantic v2 dict fields**: Expose JSONB diagnostic data through API schemas

### Expected Features

**Must have (P1 -- this milestone):**
- Rich error context on parse failure (contract_address, function_selector, detected transfers/events, parsers attempted)
- Parser attempt trail (which parsers tried, why each declined)
- Error grouping by contract address and function selector (turns 500 errors into "3 contracts need parsers")
- Bulk retry for error groups (one-click re-parse after adding a new parser)
- Function selector display in error/debug UI
- Morpho Blue core parser (supply/withdraw/borrow/repay/collateral -- port from legacy)
- Morpho vault (MetaMorpho) deposit/withdraw (ERC-4626 pattern)
- wstETH wrap/unwrap verification (GenericSwapParser may already handle; add protocol attribution)
- Arbitrum TX loading + parsing verification (infrastructure exists)
- Polygon TX loading + parsing verification (infrastructure exists)

**Should have (P2 -- add after v1 validation):**
- Morpho bundler/multicall decoding (HIGH complexity, needed when users have bundler TXs)
- Pendle swap parser (GenericSwapParser covers basic cases; specific parser for attribution)
- PT/YT token identification registry (needed for Pendle pricing)
- Missing parser detection heatmap (ranked bar chart of unparsed contracts)
- Live parse comparison mode (run multiple parsers, compare results)
- Lido withdrawal queue parser
- wstETH on L2s token mapping
- Chain-specific block explorer links

**Defer (v2+):**
- stETH rebase yield tracking (requires balance snapshot infrastructure -- a new subsystem)
- Pendle yield decomposition (complex per-market tracking)
- Cross-chain position reconciliation (bridge detection)
- AI-powered transaction classification (hallucination risk for accounting)

### Architecture Approach

The parser system extends cleanly: a new `DiagnosticCollector` (observer pattern) captures parse metadata without modifying parser logic; a centralized `addresses.py` replaces per-file address constants for all protocol deployments; new parsers (Lido, Morpho Blue, Pendle) follow the established function-selector dispatch pattern from AaveV3Parser. The critical architectural prerequisite is introducing a `ParseResult` dataclass to replace the mutable `self.ENTRY_TYPE` pattern.

**Major components (new/modified):**
1. **DiagnosticCollector** -- Captures parser selection trace, transfer consumption log, remaining unconsumed items per parse attempt
2. **ParseDiagnostic model** -- Structured JSONB payload stored on ParseErrorRecord (and optionally on JournalEntry metadata)
3. **addresses.py (ProtocolDeployment)** -- Centralized multi-chain address registry; single source of truth for protocol contract addresses across all chains
4. **ParseResult dataclass** -- Replaces mutable self.ENTRY_TYPE; returns splits + entry_type + parser_name from parse()
5. **handlers/wrap.py** -- Reusable wrap/unwrap handler for Lido wstETH, Pendle SY, and similar patterns
6. **LidoParser, MorphoBlueParser, PendleParser** -- New protocol parsers following function-selector dispatch

### Critical Pitfalls

1. **ENTRY_TYPE mutable state on singleton parsers (CONFIRMED BUG)** -- All 4 existing protocol parsers mutate `self.ENTRY_TYPE` during `parse()`. Parsers are singletons in the registry, so this is global mutable state. Fix BEFORE adding new parsers by returning `ParseResult` dataclass. Recovery cost is LOW (entry_type is metadata, not accounting data), but prevention is far cheaper.

2. **Cross-chain FIFO with separate token identities** -- Adding Arbitrum/Polygon means "USDC" exists as different contract addresses per chain. Without a canonical token mapping, FIFO creates separate lot queues per chain, violating VN's global FIFO requirement. Design the canonical `TokenRegistry` mapping `(chain, token_address) -> canonical_symbol` BEFORE adding the second chain. Recovery cost is HIGH (full FIFO reprocessing).

3. **Internal transactions not loaded** -- `EVMTxLoader._do_load()` does not call the existing `get_internal_transactions()` method. ETH received from contract calls (protocol withdrawals, WETH unwrapping) is missing. Fix before multi-chain expansion where internal TXs are even more common.

4. **Morpho layered position double-counting** -- Morpho Blue sits on top of Aave/Compound. If both Morpho and Aave parsers fire on related events, positions get double-counted. Parse only at the user's direct interaction level.

5. **Pendle PT/YT is not a swap** -- SY -> PT+YT split is a three-leg decomposition, not two swaps. PT appreciates toward face value (not income). YT generates claimable yield (is income). Treating these as swaps produces wrong cost basis. Needs dedicated research before implementation.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Parser Foundation & Diagnostics Infrastructure

**Rationale:** Every subsequent phase depends on the diagnostic foundation (enriched error records, parser attempt trails) and the architectural fixes (ENTRY_TYPE mutation, centralized addresses). This phase has zero external dependencies and highest confidence.

**Delivers:**
- `ParseResult` dataclass replacing mutable ENTRY_TYPE (fixes confirmed bug across 4 parsers)
- `ParseDiagnostic` dataclass + `DiagnosticCollector`
- Alembic migration: `diagnostic_data` JSONB + `contract_address` + `function_selector` columns on ParseErrorRecord
- `addresses.py` centralized protocol address config with `ProtocolDeployment` dataclass
- `handlers/wrap.py` reusable handler
- Internal transaction loading in EVMTxLoader

**Addresses features:** Rich error context, parser attempt trail, function selector display
**Avoids pitfalls:** ENTRY_TYPE mutation (Pitfall 1), internal TX completeness (Pitfall 5)
**Research needed:** None -- purely internal architecture, all patterns clear from codebase

### Phase 2: Diagnostic UI & Error Grouping

**Rationale:** Depends on Phase 1 schema. Unlocks the developer experience needed to efficiently build and debug protocol parsers in subsequent phases.

**Delivers:**
- Modified Bookkeeper.process_transaction with diagnostic collection
- API endpoints: error grouping by contract, by selector, bulk retry
- Frontend: enriched Error page with diagnostic detail panels, grouped error view, transfer/event summaries
- Frontend: function selector decoding in Parser Debug page

**Addresses features:** Error grouping by contract/selector, bulk retry, transfer/event summary in error view
**Avoids pitfalls:** UX pitfall of showing errors without actionable context
**Research needed:** None -- standard API + frontend patterns

### Phase 3: Morpho Blue Parser

**Rationale:** Highest confidence among the three new protocols. Legacy code provides complete reference (`MorphoBlueFunctionalParser` with all handlers, 1056 lines). Accounting patterns are identical to existing Aave V3 parser (supply/withdraw/borrow/repay). Should be built first as the "template" for subsequent protocol parsers.

**Delivers:**
- `MorphoBlueParser` with supply/withdraw/borrow/repay/supplyCollateral/withdrawCollateral
- MetaMorpho vault parser (ERC-4626 deposit/withdraw)
- MORPHO added to Protocol enum
- Real TX test fixtures for Morpho
- Morpho contract addresses in `addresses.py` (Ethereum + Base)

**Addresses features:** Morpho Blue core parser, Morpho vault parser
**Avoids pitfalls:** Layered position double-counting (Pitfall 6 -- parse at user level only)
**Research needed:** LOW -- legacy code covers patterns. Verify function selectors against deployed ABI.

### Phase 4: Lido wstETH Parser + Multi-Chain Verification

**Rationale:** These run in parallel. Lido wstETH wrap/unwrap is simple (may already work via GenericSwapParser). Multi-chain infrastructure already exists -- this phase is primarily testing and verification. Both depend on Phase 1's addresses.py for centralized config.

**Delivers:**
- `LidoParser` for submit/wrap/unwrap (defer withdrawal queue and rebase tracking to v2)
- Arbitrum integration test suite with real TXs
- Polygon integration test suite with real TXs (verify MATIC vs POL)
- Canonical token mapping (`TokenRegistry`) for cross-chain FIFO
- Chain-specific gas calculation verification
- LIDO added to Protocol enum

**Addresses features:** wstETH wrap/unwrap, Arbitrum verification, Polygon verification
**Avoids pitfalls:** Cross-chain FIFO identity (Pitfall 4), L2 gas miscalculation (Pitfall 7), MATIC/POL naming
**Research needed:** MEDIUM -- verify Lido contract addresses on mainnet. Test with real L2 TXs to validate gas calculations and Etherscan v2 responses.

### Phase 5: Pendle Parser (Targeted)

**Rationale:** Lowest confidence, highest complexity. Depends on diagnostic infrastructure (Phase 1-2) to debug effectively and on the pattern established by Morpho (Phase 3). Deliberately scoped to what GenericSwapParser cannot handle.

**Delivers:**
- `PendleParser` for router swaps (PT/YT trading), SY mint/redeem
- YT yield claiming (income recognition)
- PT/YT token identification registry for pricing
- PENDLE added to Protocol enum
- Defer: LP operations, yield decomposition, maturity tracking

**Addresses features:** Pendle swap parser, SY mint/redeem, YT yield claiming, PT/YT token identification
**Avoids pitfalls:** Pendle PT/YT treated as simple swaps (Pitfall 3 -- use three-leg entries for SY split)
**Research needed:** HIGH -- No legacy parser exists. Verify Pendle router v4/v5 addresses, function selectors, event signatures against current deployment. Verify tax treatment of PT maturity under VN law.

### Phase 6: Dashboard Polish & Extended Features

**Rationale:** After all parsers and multi-chain are working, polish the diagnostic and monitoring experience. These are high-value, low-effort features that build on all previous phases.

**Delivers:**
- Missing parser detection heatmap (ranked unparsed contracts)
- Parser coverage breakdown by protocol
- Live parse comparison mode
- Chain-specific block explorer links
- Morpho bundler multicall support (if user demand warrants)
- Morpho rewards claiming

**Addresses features:** Differentiator features (heatmap, comparison, coverage stats)
**Research needed:** None -- standard frontend features

### Phase Ordering Rationale

- **Phases 1-2 first** because every subsequent phase benefits from diagnostic tooling. Building protocol parsers without diagnostics means debugging blind.
- **Morpho before Lido** because Morpho has the strongest reference material (legacy code) and follows the exact same pattern as the existing Aave parser. It validates the new parser architecture before tackling novel challenges.
- **Lido and multi-chain together** because they share the addresses.py dependency and multi-chain verification is low-effort (infrastructure exists). Lido wstETH on L2s naturally bridges both concerns.
- **Pendle last** because it has the lowest confidence, no legacy reference, and the most novel accounting model. By this phase, diagnostics are mature and the team has experience adding two protocol parsers.
- **Canonical token mapping in Phase 4** (not Phase 6) because delaying it past multi-chain activation corrupts FIFO results irreversibly.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Morpho):** Verify Morpho Blue function selectors and MetaMorpho vault interface against deployed contracts. Legacy code provides patterns but addresses/selectors need confirmation.
- **Phase 4 (Lido + Multi-chain):** Verify Lido contract addresses on mainnet. Test Polygon MATIC vs POL gas token behavior with real Etherscan v2 responses. Test Arbitrum gas fee calculation post-ArbOS 20.
- **Phase 5 (Pendle):** HIGH research need. No legacy parser. Must read Pendle V2 docs and deployed contract ABIs. Must resolve PT maturity tax treatment under VN law before implementing.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** All internal architecture. Patterns clear from codebase.
- **Phase 2 (Diagnostic UI):** Standard API + React patterns. No unknowns.
- **Phase 6 (Polish):** Incremental UI features on established data.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies. All requirements met by existing pyproject.toml. Verified against codebase. |
| Features | MEDIUM-HIGH | Diagnostic features and Morpho well-defined from codebase + legacy code. Pendle features less certain (no legacy reference). Competitor analysis is LOW confidence (training data only). |
| Architecture | HIGH | Patterns derived from direct codebase analysis. DiagnosticCollector, addresses.py, and ParseResult are straightforward extensions. Confirmed bug (ENTRY_TYPE mutation) across 4 files with specific line references. |
| Pitfalls | HIGH | Critical pitfalls (ENTRY_TYPE, cross-chain FIFO, internal TXs) confirmed via code inspection. Protocol-specific pitfalls (Lido rebase, Pendle PT/YT, Morpho layering) are MEDIUM confidence from domain knowledge. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Protocol contract addresses:** All Lido, Morpho, and Pendle addresses come from training data (cutoff May 2025) and must be verified against current mainnet deployments before implementation. Morpho Blue addresses are partially corroborated by legacy code.
- **Polygon MATIC to POL migration:** The native gas token may have changed. Verify against current Polygonscan API behavior and price feed symbol availability.
- **Pendle router version:** Training data references v4 router. Pendle may have deployed v5+ by now. Verify current canonical router address on Ethereum and Arbitrum.
- **VN tax treatment of PT maturity:** Is PT redemption at maturity a taxable disposal event under Law 71/2025/QH15? This affects whether Pendle needs maturity-specific accounting. Legal team should clarify.
- **L2 gas calculation post-Dencun:** Arbitrum ArbOS 20 and Optimism Ecotone changed L2 fee structures. The current `calculate_gas_fee_wei()` may not handle all post-Dencun cases. Verify with real L2 transaction data.
- **Web search unavailable:** All four research files note that web search was unavailable during research. Protocol-specific details should be validated against official documentation before implementation begins.
- **MetaMorpho vault addresses:** These are dynamically deployed (not fixed singletons like Morpho Blue). May need a discovery mechanism or user-provided addresses rather than hardcoded config.
- **Pendle market discovery:** PT/YT tokens are created per-market per-maturity. The token registry needs a mechanism to identify these tokens (potentially via Pendle's market factory events or a curated list).

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `src/cryptotax/parser/` -- registry, base parsers, all protocol parsers, bookkeeper, context, handlers
- Codebase analysis: `src/cryptotax/db/models/parse_error_record.py` -- current error schema, confirmed missing diagnostic fields
- Codebase analysis: `src/cryptotax/infra/blockchain/evm/etherscan_client.py` -- confirmed Etherscan v2 with Arbitrum (42161) and Polygon (137) chain IDs
- Codebase analysis: `src/cryptotax/parser/utils/gas.py` -- confirmed L2 gas handling and native symbol mapping
- Codebase analysis: `src/cryptotax/domain/enums/` -- confirmed Chain enum includes ARBITRUM, POLYGON; Protocol enum needs extension

### Secondary (MEDIUM confidence)
- Legacy code: `legacy_code/v2/parser/evm/contract/morpho.py` -- complete Morpho Blue + MetaMorpho + Bundler parser patterns (1056 lines)
- Legacy code: `legacy_code/v2/parser/evm/contract/token.py` -- ERC20RebaseParser with stETH handling
- Legacy code: `legacy_code/v2/balance/morpho.py` -- Morpho Blue market position reading with shares-to-assets conversion
- Reference docs: `docs/reference/Parser_Patterns.md` -- distilled legacy parser architecture
- Reference docs: `docs/reference/Business_Logic.md` -- accounting rules and FIFO logic

### Tertiary (LOW confidence -- verify before implementation)
- Lido contract addresses and event signatures (training data, cutoff May 2025)
- Pendle router v4 address and function signatures (training data only, no legacy parser reference)
- Morpho Blue function selectors (training data, partially corroborated by legacy code)
- Polygon MATIC/POL migration status (training data)
- Competitor feature analysis for Koinly/TokenTax/CoinTracker (training data, competitors may have changed)

---
*Research completed: 2026-02-18*
*Ready for roadmap: yes*
