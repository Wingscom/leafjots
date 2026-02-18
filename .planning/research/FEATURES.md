# Feature Research

**Domain:** DeFi tax accounting -- parser diagnostics, protocol parsing (Lido/Morpho/Pendle), multi-chain (Arbitrum/Polygon)
**Researched:** 2026-02-18
**Confidence:** MEDIUM (protocol details from training data + legacy code analysis; no live web verification available)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must exist or the diagnostic/parser/multi-chain systems are fundamentally broken.

#### A. Parser Diagnostics

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Rich error context on parse failure** | Current `ParseErrorRecord` stores only `message` and `stack_trace`. When a TX fails, devs see "No parser produced splits" with zero context about what the TX actually was -- no contract address, no function selector, no transfers detected, no events found. This is unusable for debugging. | MEDIUM | Add `contract_address`, `function_selector`, `detected_transfers` (JSON), `detected_events` (JSON), `parsers_attempted` (JSON list of parser names + reasons they declined) to the error record. |
| **Parser attempt trail** | The bookkeeper iterates parsers but discards which ones were tried and why each said `can_parse=False`. Without this trail, you cannot tell if a TX failed because no parser matched the contract, or because a parser matched but crashed. | MEDIUM | Each parser's `can_parse` should return a reason string alongside the bool. Store the trail: `[{"parser": "AaveV3Parser", "matched": false, "reason": "to_addr not Aave pool"}, {"parser": "GenericSwapParser", "matched": false, "reason": "no swap pattern detected"}]`. |
| **Function selector display** | Users pasting a TX hash into Parser Debug see "ERROR" with no indication of what the TX was trying to do. Showing the 4-byte function selector (and ideally the decoded function name) tells devs instantly what operation failed. | LOW | Extract `input[:10]` from `tx_data`. Optionally look up in a local 4-byte mapping table or external API. |
| **Transfer and event summary in error view** | When a parse fails, devs need to see: "This TX had 3 ERC20 transfers and 2 events (Supply, Transfer). GenericSwapParser saw no swap pattern. GenericEVMParser produced unbalanced splits." This is the core of diagnostic value. | MEDIUM | Compute and store at error time. Display in the Errors page expanded view alongside the stack trace. |
| **Error grouping by contract address** | When 500 errors all come from the same unrecognized contract `0xabc...`, they should group together, not show as 500 individual errors. Grouping reveals "you need a parser for contract X" instantly. | MEDIUM | Add `contract_address` to `ParseErrorRecord`. Group-by query endpoint. Frontend aggregation view. |
| **Error grouping by function selector** | Same contract can have multiple unhandled functions. Group errors by `(contract_address, function_selector)` to show "Morpho Blue: supply=handled, liquidate=unhandled (23 TXs)". | LOW | Piggybacks on the contract_address + selector fields above. Aggregate query. |
| **Bulk retry for error group** | After adding a new parser, users need to re-parse all TXs that failed for a specific contract. Current retry is one-by-one. | LOW | Endpoint: `POST /api/errors/retry-group` with filter params (contract_address, function_selector). Loops internally. |

#### B. Protocol Parsing -- Lido stETH

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **wstETH wrap/unwrap parsing** | wstETH is the most common liquid staking token. Wrap (stETH->wstETH) and unwrap (wstETH->stETH) are simple token swaps at a ratio. Failing to parse these means broken journals for any DeFi user who holds wstETH. | LOW | wstETH contract: `wrap()` and `unwrap()` functions. Produces ERC20 transfers that GenericSwapParser can already handle as swap pattern (stETH out, wstETH in). May only need to add wstETH contract addresses to registry for protocol attribution. |
| **stETH rebasing accounting** | stETH is a rebase token -- balance increases daily without explicit transfers. This creates "phantom income" that has no on-chain TX. Must be tracked as yield income. Legacy code has `ERC20RebaseParser` with `stETHRebase` event handler. | HIGH | Two approaches: (1) Track `TransferShares` events on stETH contract which fire on every holder interaction, calculate rebase diff. (2) Snapshot stETH balance periodically and compute yield as delta. Option 2 is simpler but requires balance snapshots infrastructure. Recommend deferring full rebase tracking to v2 and handling wrap/unwrap first. |
| **Lido withdrawal queue** | Users who unstake go through a withdrawal request/claim flow via `WithdrawalQueueERC721`. Creates an NFT ticket, later claimed for ETH. Two-step process needs two journal entries: request (stETH -> withdrawal_pending) and claim (withdrawal_pending -> ETH). | MEDIUM | Specific parser for WithdrawalQueue contract. Function selectors: `requestWithdrawals`, `claimWithdrawals`. Events: `WithdrawalRequested`, `WithdrawalClaimed`. |
| **wstETH on L2s** | wstETH is bridged to Arbitrum, Polygon, Optimism, Base. Must recognize the L2 wstETH token addresses and map them correctly to the same symbol. | LOW | Add L2 wstETH token addresses to a token mapping table. Arbitrum: `0x5979d7b546e38e414f7e9822514be443a4800529`. Polygon: `0x03b54a6e9a984069379fae1a4fc4dbae93b3bccd`. (Confidence: MEDIUM -- addresses from training data, verify before use.) |

#### C. Protocol Parsing -- Morpho

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Morpho Blue supply/withdraw/borrow/repay** | Morpho Blue is a major lending protocol. The legacy codebase has a full `MorphoBlueFunctionalParser` with handlers for all core operations. Must port. Core events: `Supply`, `Withdraw`, `Borrow`, `Repay`, `SupplyCollateral`, `WithdrawCollateral`. | MEDIUM | Port from legacy `MorphoBlueFunctionalParser`. Key difference from Aave: Morpho uses market IDs (bytes32 hash) instead of reserve addresses. Each market has a loan token and collateral token. Function-driven approach works well (same as current Aave parser pattern). |
| **Morpho vault (MetaMorpho / ERC-4626) deposit/withdraw** | MetaMorpho vaults wrap Morpho Blue markets in ERC-4626 interface. Users interact with vaults, not raw Morpho Blue. Deposit gives vault shares, withdraw burns shares for underlying. Legacy has `MetaMorphoParser` and `_handle_M636_deposit/redeem`. | MEDIUM | ERC-4626 `deposit()/withdraw()/mint()/redeem()` functions. Need to track vault share token as protocol_asset and underlying token. Transfer pattern: user sends underlying -> vault mints shares to user. |
| **Morpho bundler/adapter multicall** | Many Morpho interactions go through a bundler contract that batches operations (approve + supply, borrow + withdraw collateral). Legacy code has `MorphoBundlerParser` and `MorphoBundler3Parser` for bundler v2 and v3. This is where most real Morpho TXs happen. | HIGH | Multicall decoding is complex. Each call in the bundle is a separate function that needs its own handler. The bundler acts as intermediary, so transfer patterns differ (wallet -> bundler -> Morpho, not wallet -> Morpho directly). Legacy code handles this with `transfer_source_is_caller` flag. |
| **Morpho rewards claiming** | Morpho distributes MORPHO token rewards. Legacy `MorphoRewardsParser` handles `Claimed` event from `UniversalRewardsDistributor`. | LOW | Standard claim pattern: reward token transferred from distributor to user. Income journal entry. |

#### D. Protocol Parsing -- Pendle

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Pendle swap (PT/YT trading)** | Pendle's core product is trading yield. Users swap between PT (Principal Token), YT (Yield Token), and SY (Standardized Yield). These are AMM swaps on Pendle's custom market contract. | MEDIUM | Pendle Router contract: `swapExactPtForToken()`, `swapExactTokenForPt()`, `swapExactYtForToken()`, etc. At the transfer level, these look like normal swaps (token A out, token B in) and GenericSwapParser may already handle many of them. Protocol-specific parser adds correct attribution and entry typing. |
| **Pendle mint/redeem SY** | SY (Standardized Yield) wraps yield-bearing assets. Minting SY from underlying (e.g., stETH -> SY-stETH) and redeeming back. | LOW | Standard wrap pattern. Transfer: underlying out, SY in. Similar to wstETH wrap. |
| **Pendle add/remove liquidity** | Adding liquidity to Pendle pools (PT + SY -> LP token). Removing gets back PT + SY. | MEDIUM | Two-token LP pattern. Similar to Uniswap V3 LP but with PT and SY tokens. Router functions: `addLiquiditySinglePt()`, `addLiquiditySingleToken()`, `removeLiquiditySinglePt()`, etc. |
| **Pendle YT yield claiming** | YT holders earn yield over time. `redeemDueInterestAndRewards()` distributes accrued yield. | LOW | Standard claim/income pattern. SY tokens transferred to user as yield. Map to income account. |
| **PT/YT token identification** | Pendle creates new PT and YT tokens for each market and expiry. Names like "PT-stETH-26DEC2026". Need to map these to their underlying for price lookups. | MEDIUM | Pendle markets have `readTokens()` that returns (SY, PT, YT). Need a token registry that maps PT/YT addresses to their underlying asset symbol for pricing. Without this, price lookups fail for all Pendle tokens. |

#### E. Multi-Chain -- Arbitrum + Polygon

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Arbitrum TX loading** | Etherscan v2 API already supports Arbitrum (chainid=42161) in the current `EtherscanClient`. Chain enum already has `ARBITRUM`. Gas utils handle L2 `l1Fee`. Protocol parsers (Aave, Uniswap, Curve) already have Arbitrum addresses registered. This should "just work". | LOW | Verify: (1) etherscan_client.py has chainid 42161 -- YES. (2) aave_v3.py has arbitrum pool -- YES. (3) uniswap_v3.py has arbitrum routers -- YES. (4) gas.py maps arbitrum to ETH -- YES. Main work: test with real Arbitrum TXs, handle any edge cases. |
| **Polygon TX loading** | Same as Arbitrum. Etherscan v2 supports Polygon (chainid=137). Chain enum has `POLYGON`. Uniswap V3 has Polygon routers. Aave V3 has Polygon pool. | LOW | Gas: Polygon uses MATIC (now POL) for gas. `gas.py` already maps polygon -> "MATIC". Verify POL rebranding does not affect gas symbol. L2 fee: Polygon does NOT have l1Fee (not a rollup). Simpler than Arbitrum. |
| **L2 gas fee calculation (Arbitrum specifics)** | Arbitrum gas has L1 data posting component. Current `calculate_gas_fee_wei` handles `l1Fee` field. | LOW | Already implemented in `gas.py`. Arbitrum TX receipts from Etherscan include `l1Fee` when applicable. Verify with real TXs. |
| **Polygon gas token naming (MATIC vs POL)** | Polygon rebranded MATIC to POL in 2024. Price feeds may use either symbol. Need consistent mapping. | LOW | Add symbol alias: POL = MATIC in price service. Gas symbol stays "MATIC" for consistency with existing data, but price lookups should try both. |
| **Chain-specific block explorer links** | Dashboard TX detail should link to correct explorer per chain. Currently only Etherscan? Need Arbiscan, Polygonscan links. | LOW | Map chain -> explorer URL prefix. Arbitrum: `arbiscan.io`. Polygon: `polygonscan.com`. Display in TX detail view. |
| **Chain-specific token address mapping** | Same token (USDC, WETH) has different contract addresses on each chain. Token registry must be chain-aware. | MEDIUM | Current parser uses `symbol` from transfers. Need a `(chain, token_address) -> canonical_symbol` mapping for price lookups. Especially important for bridged tokens that might have different names. |

---

### Differentiators (Competitive Advantage)

Features that set this diagnostic/parser system apart from manual debugging or basic error logs.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **"Missing parser" detection with contract frequency analysis** | Automatically identify the top contracts causing parse failures, ranked by TX count. "You need a parser for contract 0xabc (Morpho Blue) -- 342 failed TXs" vs "contract 0xdef (unknown) -- 2 failed TXs". This is the top differentiator over raw error logs. | MEDIUM | Aggregate query on `ParseErrorRecord` grouped by `contract_address`, joined with a known-contracts table for name resolution. Frontend: ranked bar chart or table showing "top unparsed contracts". |
| **Function selector dictionary with auto-resolution** | When displaying errors, automatically decode the 4-byte selector to a human-readable function name. "0x617ba037" -> "supply(address,uint256,address,uint16)". Huge DX improvement. | MEDIUM | Two approaches: (1) Ship a local SQLite/JSON of common 4-byte selectors (~50K entries from 4byte.directory). (2) Compute keccak256 of known ABI functions from registered parsers. Option 1 gives broader coverage; option 2 is zero-dependency. Recommend both: local table for known parsers + optional API fallback. |
| **Parser coverage heatmap by protocol** | Visual breakdown: "Aave V3: 98% parsed. Uniswap V3: 95%. Unknown contracts: 60% parsed (generic only)." Shows exactly where to invest parser development effort. | LOW | Query: group TXs by `(to_addr, status)`. Join with a protocol-address mapping. Frontend: stacked bar chart per protocol. |
| **"Suggested parser" for unknown contracts** | When a contract has many failed TXs, analyze its transfer patterns to suggest what parser type it needs. "Contract 0xabc has supply/withdraw/borrow patterns -- likely a lending protocol. Consider using the LendingProtocolParser template." | HIGH | Pattern matching on aggregated transfer + event data across failed TXs for a contract. Look for deposit/withdraw patterns (token out + protocol token in), swap patterns (token A out + token B in), claim patterns (token in from fixed source). This is genuinely differentiating but complex. |
| **Live parse comparison** | Parse a TX with multiple parsers and show side-by-side results. "GenericSwapParser produced: [...]. AaveV3Parser produced: [...]. Which is correct?" Useful when adding new parsers. | LOW | Run all matching parsers (not just first match) and return all results. Frontend: tabbed comparison view. Non-destructive (no DB writes in comparison mode). |
| **stETH rebase yield tracking** | Automatically detect stETH balance changes from rebasing and record as yield income. Most tax tools miss this entirely, meaning users underreport income. | HIGH | Requires balance snapshots or event-based tracking. Not a standard TX parse -- it is a periodic job. Schedule: daily or on each stETH interaction. Compute yield = current_balance - (last_known_balance + deposits - withdrawals). Record as income journal entry. |
| **Pendle yield decomposition** | Break down Pendle positions into principal vs yield components for tax purposes. PT = fixed income, YT = variable yield. Different tax treatments may apply. | HIGH | Requires understanding Pendle market mechanics: PT trades at discount to underlying, converging to 1:1 at expiry. YT value = underlying_value - PT_value. Need per-market tracking of PT/YT minting and expiry. |
| **Cross-chain position reconciliation** | For tokens bridged across chains (e.g., USDC on Ethereum deposited to Aave on Arbitrum), track the bridge transfer and link positions across chains. | HIGH | Bridge TX detection is complex (each bridge has different contracts and patterns). Defer to future milestone. But the architecture should support chain-aware position tracking from the start. |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Auto-generate parsers from ABI** | "If we have the ABI, just auto-create a parser" | ABIs tell you function signatures, not accounting semantics. `supply()` in Morpho means deposit, but `supply()` in a different protocol might mean something else. Transfer patterns differ between direct calls and bundler/proxy calls. Auto-generated parsers would produce incorrect journal entries silently. | Provide parser templates/scaffolds that fill in the function signatures from ABI, but require human review of accounting logic. Show the ABI info in diagnostics to help devs write the parser faster. |
| **Real-time parse-on-ingest** | "Parse every TX as it is loaded" | Parsing depends on having all related TXs loaded first (e.g., internal transactions, ERC20 transfers). If you parse before all data is loaded, you miss transfers and produce wrong results. Also, parse errors during loading create confusing mixed states. | Keep the current two-phase approach: Load all TXs first, then parse as a separate step. This is already the correct architecture. |
| **Universal protocol auto-detection** | "Detect any protocol automatically using on-chain metadata" | Contract metadata is unreliable. Proxy contracts hide the actual implementation. Same bytecode can be different protocols. Even if you identify "this is a lending protocol," you still need protocol-specific accounting rules. | Use the generic parsers (GenericEVM/GenericSwap) as fallback, show diagnostic info for unrecognized contracts, and let devs add specific parsers when accuracy matters. The current horizontal-first strategy is correct. |
| **Full stETH rebase tracking from genesis** | "Track all historical stETH rebases" | stETH has been rebasing since 2020. Backfilling requires thousands of balance snapshots. Processing time is enormous. Most users only need current tax year. | Track rebase yield only from the point the wallet is added to the system. For historical data, allow manual yield entry with a note. |
| **AI-powered transaction classification** | "Use LLM to classify unknown transactions" | LLMs hallucinate accounting entries. A wrong journal entry is worse than no journal entry -- it silently corrupts the books. Classification confidence is hard to calibrate. | Use AI to suggest classification (display in UI as "suggested: swap"), but require human confirmation before writing to journal. Flag AI-classified entries distinctly. |
| **Per-chain separate parser registries** | "Each chain should have its own completely independent parser set" | Most DeFi protocols deploy identical contracts across chains. Aave V3 on Arbitrum works the same as on Ethereum. Maintaining separate parser instances per chain multiplies code and testing. | Current architecture is correct: one parser class, registered with chain-specific addresses. `AAVE_V3_POOL` dict maps chain->address. Same parser handles all chains. Only add chain-specific logic when protocols genuinely differ. |

---

## Feature Dependencies

```
[Rich error context]
    |-- requires --> [contract_address + function_selector in ParseErrorRecord]
    |                    |-- enables --> [Error grouping by contract]
    |                    |-- enables --> [Error grouping by selector]
    |                    |-- enables --> [Missing parser detection]
    |                    |-- enables --> [Function selector dictionary]
    |                    |-- enables --> [Bulk retry for error group]
    |
    |-- requires --> [detected_transfers + detected_events in error record]
    |                    |-- enables --> [Transfer/event summary in error view]
    |                    |-- enables --> [Suggested parser for unknown contracts]

[Parser attempt trail]
    |-- requires --> [can_parse returns reason alongside bool]
    |-- enables --> [Live parse comparison]

[Morpho Blue parser]
    |-- requires --> [Function selector detection (already exists)]
    |-- requires --> [Protocol enum extension (add MORPHO)]
    |-- enables --> [Morpho vault parser] (uses Morpho Blue internally)
    |-- enables --> [Morpho bundler parser] (wraps Morpho Blue calls)

[Morpho bundler parser]
    |-- requires --> [Morpho Blue parser]
    |-- requires --> [Multicall decoding capability]

[Pendle swap parser]
    |-- requires --> [PT/YT token identification]
    |-- enables --> [Pendle LP parser]
    |-- enables --> [Pendle yield claiming parser]

[PT/YT token identification]
    |-- requires --> [Chain-specific token address mapping]
    |-- enables --> [Price lookups for Pendle tokens]
    |-- enables --> [Pendle yield decomposition]

[Arbitrum support]
    |-- requires --> [Etherscan v2 Arbitrum chainid] (ALREADY EXISTS)
    |-- requires --> [L2 gas fee calculation] (ALREADY EXISTS)
    |-- requires --> [Protocol addresses for Arbitrum] (ALREADY EXISTS for Aave, Uniswap)
    |-- enables --> [wstETH on Arbitrum]
    |-- enables --> [Morpho on Arbitrum] (Morpho Blue deployed on Arbitrum)

[Polygon support]
    |-- requires --> [Etherscan v2 Polygon chainid] (ALREADY EXISTS)
    |-- requires --> [MATIC/POL gas symbol mapping] (ALREADY EXISTS, verify POL)
    |-- requires --> [Protocol addresses for Polygon] (ALREADY EXISTS for Aave, Uniswap)
    |-- enables --> [wstETH on Polygon]

[wstETH wrap/unwrap]
    |-- independent (GenericSwapParser may already handle)
    |-- enables --> [stETH rebase tracking] (needs wstETH<->stETH ratio)

[Chain-specific token address mapping]
    |-- required by --> [PT/YT token identification]
    |-- required by --> [wstETH on L2s]
    |-- required by --> [Polygon gas token naming]
```

### Dependency Notes

- **Rich error context requires schema migration:** Adding fields to `ParseErrorRecord` needs an Alembic migration. Do this first since it is the foundation for all diagnostic features.
- **Morpho bundler requires Morpho Blue:** The bundler delegates to Morpho Blue handlers internally. Build and test Morpho Blue direct-call parser first, then wrap with bundler multicall support.
- **PT/YT token identification is a cross-cutting concern:** It affects price lookups, token display, and parser behavior. Implement the token registry enhancement early since Pendle features depend on it.
- **Arbitrum/Polygon are low-effort because infrastructure exists:** The Etherscan client, chain enum, gas calculation, and protocol addresses already support both chains. The work is primarily testing with real TXs and fixing edge cases.

---

## MVP Definition

### Launch With (v1) -- This Milestone

- [x] **Rich error context** -- Add contract_address, function_selector, detected_transfers, detected_events, parsers_attempted to ParseErrorRecord. This is the single most impactful change for parser development velocity.
- [x] **Parser attempt trail** -- Modify `can_parse` to return `(bool, str)` tuples. Store in error record.
- [x] **Error grouping by contract/selector** -- Aggregate endpoint + frontend grouped view. Turns 500 individual errors into "3 contracts need parsers."
- [x] **Bulk retry for error group** -- After adding a parser, re-parse all affected TXs in one click.
- [x] **Morpho Blue supply/withdraw/borrow/repay** -- Port from legacy. Direct-call parser for the core lending operations.
- [x] **Morpho vault (MetaMorpho) deposit/withdraw** -- ERC-4626 pattern. Most users interact via vaults, not raw Morpho Blue.
- [x] **wstETH wrap/unwrap** -- Verify GenericSwapParser handles it; add protocol attribution if not.
- [x] **Arbitrum TX loading + parsing verification** -- Infrastructure exists. Integration test with real Arbitrum TXs.
- [x] **Polygon TX loading + parsing verification** -- Infrastructure exists. Integration test with real Polygon TXs.
- [x] **Function selector display in error/debug views** -- Show `0x617ba037 (supply)` in the UI.

### Add After Validation (v1.x)

- [ ] **Morpho bundler v2/v3 multicall** -- Add when users have bundler TXs that fail parsing. Complex multicall decoding.
- [ ] **Morpho rewards claiming** -- Add when MORPHO reward distribution becomes common.
- [ ] **Pendle swap parser** -- Add when Pendle TXs appear in user wallets. GenericSwapParser may already cover basic swaps.
- [ ] **Pendle SY mint/redeem** -- Standard wrap pattern, low complexity.
- [ ] **Pendle LP add/remove** -- Two-token LP, medium complexity.
- [ ] **PT/YT token identification registry** -- Needed for correct pricing of Pendle positions.
- [ ] **Lido withdrawal queue parser** -- Add when users unstake ETH via Lido.
- [ ] **wstETH on L2s token mapping** -- Add L2 token addresses for wstETH.
- [ ] **Missing parser detection heatmap** -- Ranked view of unparsed contracts.
- [ ] **Live parse comparison mode** -- Side-by-side multi-parser results.
- [ ] **Chain-specific block explorer links** -- Small UX improvement, add when multi-chain is live.

### Future Consideration (v2+)

- [ ] **stETH rebase yield tracking** -- Requires balance snapshot infrastructure. Significant new subsystem.
- [ ] **Pendle yield decomposition** -- Complex per-market tracking. Needs Pendle-specific price oracle.
- [ ] **Suggested parser for unknown contracts** -- Pattern analysis on failed TX aggregates. Interesting but high effort.
- [ ] **Cross-chain position reconciliation** -- Bridge detection. Very complex, defer.
- [ ] **Function selector dictionary (full 50K entries)** -- Ship local DB of common selectors. Nice but not critical if known-parser selectors are covered.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Rich error context (schema + storage) | HIGH | MEDIUM | P1 |
| Parser attempt trail | HIGH | LOW | P1 |
| Error grouping by contract | HIGH | LOW | P1 |
| Function selector display | HIGH | LOW | P1 |
| Transfer/event summary in error view | HIGH | LOW | P1 |
| Bulk retry for error group | HIGH | LOW | P1 |
| Morpho Blue core parser | HIGH | MEDIUM | P1 |
| Morpho vault (MetaMorpho) parser | HIGH | MEDIUM | P1 |
| wstETH wrap/unwrap verification | MEDIUM | LOW | P1 |
| Arbitrum verification | MEDIUM | LOW | P1 |
| Polygon verification | MEDIUM | LOW | P1 |
| Missing parser detection heatmap | HIGH | LOW | P2 |
| Parser coverage heatmap by protocol | MEDIUM | LOW | P2 |
| Morpho bundler multicall | MEDIUM | HIGH | P2 |
| Morpho rewards claiming | LOW | LOW | P2 |
| Pendle swap parser | MEDIUM | MEDIUM | P2 |
| PT/YT token identification | MEDIUM | MEDIUM | P2 |
| Lido withdrawal queue | LOW | MEDIUM | P2 |
| wstETH on L2s | LOW | LOW | P2 |
| Live parse comparison | MEDIUM | LOW | P2 |
| Chain-specific explorer links | LOW | LOW | P2 |
| Pendle LP add/remove | MEDIUM | MEDIUM | P3 |
| Pendle YT yield claiming | LOW | LOW | P3 |
| stETH rebase yield tracking | MEDIUM | HIGH | P3 |
| Pendle yield decomposition | LOW | HIGH | P3 |
| Suggested parser detection | MEDIUM | HIGH | P3 |
| Cross-chain reconciliation | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for this milestone
- P2: Should have, add as users encounter specific protocols
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Koinly | TokenTax | CoinTracker | Our Approach |
|---------|--------|----------|-------------|--------------|
| Parser error diagnostics | Basic error list, no grouping | Minimal -- "unsupported transaction" | Error categories but no contract-level analysis | **Rich diagnostics with contract grouping, parser trail, transfer/event context. Competitive edge for DeFi-heavy users.** |
| Morpho support | Partial (basic transfers) | None | None | Full Morpho Blue + MetaMorpho vault parsing. Port from proven legacy code. |
| Lido stETH | wstETH transfers only | wstETH transfers only | wstETH + basic rebase | wstETH wrap/unwrap now, rebase tracking in v2. |
| Pendle | None | None | None | Pendle swap/SY/LP parsing. First mover advantage for VN users using Pendle. |
| Multi-chain | Arbitrum + Polygon supported | Limited L2 | Arbitrum + Polygon | Arbitrum + Polygon (infrastructure already built). Same parser architecture across all chains. |
| Error recovery UX | Re-sync wallet | Manual re-import | Basic retry | Bulk retry per contract group. One-click re-parse after adding parser. |

**Confidence: LOW** -- Competitor feature details are from training data. Competitor capabilities may have changed.

---

## Protocol Technical Details (for Implementation Reference)

### Lido stETH/wstETH Contracts

**Confidence: MEDIUM** (training data, verify addresses before use)

| Contract | Chain | Address | Key Functions |
|----------|-------|---------|---------------|
| stETH | Ethereum | `0xae7ab96520de3a18e5e111b5eaab095312d7fe84` | `submit()` (stake ETH) |
| wstETH | Ethereum | `0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0` | `wrap()`, `unwrap()` |
| wstETH | Arbitrum | `0x5979d7b546e38e414f7e9822514be443a4800529` | ERC20 (bridged) |
| wstETH | Polygon | `0x03b54a6e9a984069379fae1a4fc4dbae93b3bccd` | ERC20 (bridged) |
| WithdrawalQueue | Ethereum | `0x889edc2edab5f40e902b864ad4d7ade8e412f9b1` | `requestWithdrawals()`, `claimWithdrawals()` |

Key events: `Submitted` (stake), `TransferShares` (rebase accounting), `WithdrawalRequested`, `WithdrawalClaimed`.

### Morpho Blue Contracts

**Confidence: MEDIUM** (from legacy code analysis + training data)

| Contract | Chain | Address | Notes |
|----------|-------|---------|-------|
| Morpho Blue | Ethereum | `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb` | Core singleton |
| Morpho Blue | Base | `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb` | Same address |

Key events: `Supply`, `Withdraw`, `Borrow`, `Repay`, `SupplyCollateral`, `WithdrawCollateral`, `Liquidate`, `CreateMarket`, `AccrueInterest`.

Key functions (from legacy `FUNC_HANDLERS`): `supply`, `withdraw`, `supplyCollateral`, `withdrawCollateral`, `borrow`, `repay`, `liquidate`, `flashLoan`, `multicall`.

Ignored functions (from legacy): `setAuthorizationWithSig`, `morphoFlashLoanCallback`, `createMarket`, `accrueInterest`, `setAuthorization`, `setFee`, `enableIrm`, `enableLltv`, `setFeeRecipient`.

### Pendle Contracts

**Confidence: LOW** (training data only, no legacy parser to reference)

| Contract | Purpose | Key Functions |
|----------|---------|---------------|
| PendleRouter | Swap/LP routing | `swapExactPtForToken()`, `swapExactTokenForPt()`, `addLiquiditySingleToken()`, `removeLiquiditySinglePt()` |
| PendleMarket | AMM pool (PT + SY) | `swap()`, `mint()`, `burn()` |
| SY (Standardized Yield) | Yield wrapper | `deposit()`, `redeem()` |
| YieldContractFactory | Create PT/YT | `createYieldContract()` |

Pendle is deployed on: Ethereum, Arbitrum, BSC, Optimism, Mantle. (Confidence: LOW -- verify deployment chains.)

---

## Sources

- **Codebase analysis:** `d:/work/crytax/src/cryptotax/parser/` (registry, base parsers, protocol parsers, bookkeeper)
- **Codebase analysis:** `d:/work/crytax/src/cryptotax/api/errors.py` and `d:/work/crytax/src/cryptotax/api/parser.py` (current diagnostic endpoints)
- **Codebase analysis:** `d:/work/crytax/src/cryptotax/db/models/parse_error_record.py` (current error schema -- identified missing fields)
- **Codebase analysis:** `d:/work/crytax/web/src/pages/Errors.tsx` and `d:/work/crytax/web/src/pages/ParserDebug.tsx` (current frontend diagnostic views)
- **Legacy code:** `d:/work/crytax/legacy_code/v2/parser/evm/contract/morpho.py` (full Morpho Blue + MetaMorpho + Bundler parser patterns, 1056 lines)
- **Legacy code:** `d:/work/crytax/legacy_code/v2/balance/morpho.py` (Morpho balance reconciliation with shares-to-assets conversion)
- **Legacy code:** `d:/work/crytax/legacy_code/v2/parser/evm/contract/token.py` (ERC20RebaseParser with stETHRebase handler)
- **Legacy code:** `d:/work/crytax/legacy_code/v2/dapp/pendle/provider.py` (Pendle map provider, no parser exists)
- **Reference doc:** `d:/work/crytax/docs/reference/Parser_Patterns.md` (ported patterns, handler architecture)
- **Current infrastructure:** `d:/work/crytax/src/cryptotax/infra/blockchain/evm/etherscan_client.py` (already supports Arbitrum chainid=42161, Polygon chainid=137)
- **Current config:** `d:/work/crytax/src/cryptotax/parser/utils/gas.py` (native symbols for Arbitrum->ETH, Polygon->MATIC)
- **Current config:** `d:/work/crytax/src/cryptotax/domain/enums/chain.py` (Arbitrum + Polygon already in Chain enum)
- **Current config:** `d:/work/crytax/src/cryptotax/parser/defi/aave_v3.py` (Aave V3 pool addresses include Arbitrum + Polygon)
- **Current config:** `d:/work/crytax/src/cryptotax/parser/defi/uniswap_v3.py` (Uniswap V3 router addresses include Arbitrum + Polygon)

**Note:** Protocol contract addresses and event signatures sourced from training data (cutoff May 2025) and legacy code analysis. These MUST be verified against current mainnet deployments before implementation. Confidence: MEDIUM for Morpho (corroborated by legacy code), LOW for Pendle and Lido L2 addresses.

---
*Feature research for: DeFi tax accounting -- parser diagnostics, Lido/Morpho/Pendle parsing, Arbitrum/Polygon multi-chain*
*Researched: 2026-02-18*
