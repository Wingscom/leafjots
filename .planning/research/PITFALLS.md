# Pitfalls Research

**Domain:** DeFi tax accounting -- protocol parsers, multi-chain support, parser diagnostics
**Researched:** 2026-02-18
**Confidence:** HIGH (codebase evidence + legacy reference docs) / MEDIUM (protocol-specific claims from training data)

---

## Critical Pitfalls

### Pitfall 1: Class-Level Mutable State on Singleton Parsers (CONFIRMED BUG)

**What goes wrong:**
Parser instances are created once at registry build time (`build_default_registry()`) and reused for every transaction. When a parser mutates `self.ENTRY_TYPE` during `parse()`, that mutation persists across subsequent transactions. The next TX inherits the ENTRY_TYPE from the previous TX's last code path.

This bug already exists in GenericEVMParser (lines 90-92), AaveV3Parser (lines 59, 63, 67, 68), UniswapV3Parser (lines 95, 98, 107), and CurvePoolParser (lines 64, 67, 69). Every protocol-specific parser added will inherit this pattern unless the base architecture changes.

**Why it happens:**
The pattern `self.ENTRY_TYPE = EntryType.SWAP` looks correct in isolation. Developers copy the pattern from existing parsers. Python class variables on instances create per-instance state, but since parsers are singletons in the registry, "per-instance" means "global mutable state."

**How to avoid:**
Return ENTRY_TYPE from `parse()` instead of mutating self. Two approaches:

Option A (minimal change): Return a `ParseResult` dataclass instead of `list[ParsedSplit]`:
```python
@dataclass
class ParseResult:
    splits: list[ParsedSplit]
    entry_type: EntryType
    parser_name: str
```

Option B (defensive): Make ENTRY_TYPE a class constant and determine entry type in the Bookkeeper from the function selector or from a separate `classify()` method.

Option A is recommended -- smaller refactor, immediately fixes the bug, and naturally prevents new parsers from falling into the same trap.

**Warning signs:**
- Intermittent wrong `entry_type` values in the journal table
- A gas-only TX followed by a swap shows the swap as `GAS_FEE`
- Different results when processing TXs in different orders
- Test passes in isolation but fails when run after other tests

**Phase to address:**
Diagnostics milestone, before adding new parsers. Every new parser will copy the broken pattern otherwise. Fix the base abstraction FIRST.

---

### Pitfall 2: Rebasing Token Accounting (Lido stETH)

**What goes wrong:**
Lido stETH is a rebasing token -- its balance increases daily without any Transfer event. If you track stETH as a normal ERC20, you see deposits and withdrawals but never capture the yield. The user's stETH balance grows but no journal entry records the income. This means:
1. Balances drift from on-chain reality
2. Yield income goes unreported (tax evasion risk)
3. FIFO cost basis is wrong because acquired quantity != current quantity

wstETH (wrapped stETH) does NOT rebase -- it appreciates in value instead. But many users hold stETH directly, and Lido transactions often involve both tokens.

**Why it happens:**
Parsers track discrete events (Transfer, Deposit, Withdraw). Rebasing is a continuous process with no event. The standard approach of "parse TX events into journal entries" fundamentally cannot capture rebasing yield.

**How to avoid:**
Two-pronged approach for Lido:

1. For stETH: Implement periodic balance reconciliation that creates "yield income" journal entries for the difference between expected balance (from journal) and actual on-chain balance. Run this as a nightly job or on-demand from the dashboard.

2. For wstETH: Treat as a vault token. Price wstETH via the stETH/wstETH exchange rate. No rebasing journal entries needed -- the value change is captured at FIFO lot matching time.

3. Parser for Lido must handle: `submit()` (ETH -> stETH), `wrap()` (stETH -> wstETH), `unwrap()` (wstETH -> stETH), `requestWithdrawals()`, `claimWithdrawal()`. The stETH <-> wstETH conversions are NOT swaps -- they're wrapping operations where the underlying value is identical.

**Warning signs:**
- Account balances in the journal slowly diverge from on-chain balances
- No income entries for stETH holders
- Reconciliation page shows persistent mismatches that grow over time

**Phase to address:**
Lido parser milestone. Must design the reconciliation mechanism before writing the parser. This is not just a parser -- it requires a new accounting pattern.

**Confidence:** MEDIUM -- architecture for rebasing tokens is well-understood in the DeFi accounting space (training data), but the specific Lido contract interfaces should be verified against current docs before implementation.

---

### Pitfall 3: Pendle PT/YT/SY Token Complexity

**What goes wrong:**
Pendle splits yield-bearing assets into three components:
- SY (Standardized Yield): wrapper around the underlying yield-bearing asset
- PT (Principal Token): represents the principal, trades at a discount to underlying
- YT (Yield Token): represents the right to receive yield until maturity

This creates several accounting nightmares:
1. Minting SY from underlying, then splitting SY into PT+YT is NOT two swaps -- it's a decomposition. The sum of PT+YT value must equal SY value at minting time.
2. PT appreciates toward face value as maturity approaches. This is NOT income -- it's the discount unwinding.
3. YT generates claimable yield. This IS income.
4. At maturity, PT redeems 1:1 for underlying. YT becomes worthless.
5. Pendle AMM uses custom math (LogitNormal curve), making LP position pricing non-trivial.

If you parse PT/YT trades as simple swaps, you get wrong cost basis because the PT was acquired at a discount. The "gain" at maturity is really the yield the user paid for upfront.

**Why it happens:**
Developers treat all DeFi operations as variations of swap/deposit/withdraw. Pendle's tokenization model is genuinely novel and doesn't map cleanly to these primitives.

**How to avoid:**
1. Model PT/YT as protocol positions, not standalone tokens:
   - `protocol_asset:pendle:PT:stETH-DEC2026` for principal
   - `protocol_asset:pendle:YT:stETH-DEC2026` for yield token
2. Treat SY -> PT+YT split as a single journal entry with three legs (not two separate swaps)
3. Track maturity dates as metadata on the account
4. For YT yield claims, use the existing `make_yield_splits` handler
5. Defer Pendle LP to a later phase -- the AMM math is complex

**Warning signs:**
- PT "gains" that don't match actual economic reality
- Journal entries that fail balance validation when splitting SY into PT+YT
- Missing yield income from YT tokens

**Phase to address:**
Pendle parser milestone. This needs dedicated research into current Pendle V2 contract interfaces. Flag as HIGH research need -- do not attempt without reading the actual contract ABIs.

**Confidence:** MEDIUM -- Pendle's model is well-documented in their docs, but contract-level details (event names, function selectors) need verification against current deployment.

---

### Pitfall 4: Multi-Chain Address Collisions and Cross-Chain Identity

**What goes wrong:**
When adding Arbitrum and Polygon support:
1. Same contract address on different chains means different protocols. Aave V3 Pool on Arbitrum (`0x794a...`) is also Aave V3 Pool on Polygon and Optimism (same address, different chains). The registry handles this correctly via chain+address keys.
2. But: same WALLET address on different chains is the SAME user (for EVM chains). The account mapper currently uses `{chain}:{address}:...` as the key, creating separate accounts per chain. This is correct for balance tracking but WRONG for FIFO if using GLOBAL_FIFO mode -- because VN tax law requires global FIFO across all wallets.
3. Token symbol collisions: "USDC" on Ethereum is a different contract than "USDC" on Arbitrum. They're fungible in reality but have different token_address values. If the FIFO calculator treats them as different symbols, you get separate lot queues per chain -- violating global FIFO.

**Why it happens:**
Multi-chain is deceptively simple at the TX loading level but creates subtle issues at the accounting level. The per-chain data model (correct) conflicts with the cross-chain accounting model (also correct but different).

**How to avoid:**
1. Canonical symbol mapping: Create a `TokenRegistry` that maps `(chain, token_address)` to a canonical symbol. USDC on any chain maps to canonical "USDC". This already partially exists via the `symbol` field on RawTransfer, but needs to be formalized.
2. FIFO calculator must operate on canonical symbols, not per-chain symbols.
3. The tax engine should aggregate across chains when computing the 0.1% transfer tax and VND 20M exemption.
4. Add a `chain` column awareness to the accounts tree view in the UI so users can see cross-chain positions.

**Warning signs:**
- Different FIFO results when processing chains in different order
- "USDC" lots on Ethereum not matching against "USDC" sales on Arbitrum
- Tax totals that change when adding a new chain

**Phase to address:**
Multi-chain milestone (Arbitrum/Polygon). The canonical token mapping MUST be designed before adding the second EVM chain. If postponed, the FIFO results will be wrong and require a full reprocessing.

**Confidence:** HIGH -- this is a well-known problem in multi-chain accounting. The current codebase shows the chain-prefixed account keys that will cause this issue.

---

### Pitfall 5: Internal Transactions and Native Token Completeness

**What goes wrong:**
The current EVM TX loader fetches normal transactions (`txlist`) and ERC20 transfers (`tokentx`), but does NOT fetch internal transactions (`txlistinternal`). Internal transactions are created by smart contracts calling other contracts and transferring native ETH in the process. Without them:
1. ETH received from contract calls (e.g., unwrapping WETH, claiming ETH from a protocol) is missing
2. Multi-hop operations where ETH moves through intermediary contracts lose value
3. Balances undercount actual ETH received

The Etherscan client already has `get_internal_transactions()` but it's not called in `EVMTxLoader._do_load()`.

**Why it happens:**
Internal transactions are an afterthought. The basic TX + ERC20 transfer pair handles 80% of cases. But for DeFi users, internal transactions are common (unwrapping WETH, protocol withdrawals to ETH, flash loan repayments).

**How to avoid:**
Add internal transaction fetching to `EVMTxLoader._do_load()`:
```python
internal_txs = await self._etherscan.get_internal_transactions(wallet.address, from_block, to_block)
internal_by_hash: dict[str, list[dict]] = defaultdict(list)
for itx in internal_txs:
    internal_by_hash[itx.get("hash", "").lower()].append(itx)
```
Then include these in the stored `tx_data["internal_transfers"]` and update `extract_all_transfers()` to consume them.

**Warning signs:**
- ETH balance in journal is lower than on-chain balance
- Certain protocol withdrawal TXs show 0 value received
- "Missing funds" in reconciliation that correspond to contract-to-wallet ETH transfers

**Phase to address:**
Multi-chain milestone or diagnostics milestone. Should be fixed before adding Arbitrum/Polygon (where internal TXs are even more common due to L2 bridge operations).

**Confidence:** HIGH -- verified by reading the codebase. The `get_internal_transactions()` method exists but is not called by the loader.

---

### Pitfall 6: Morpho Vault Accounting -- Layered Positions

**What goes wrong:**
Morpho Blue is a lending protocol that sits ON TOP of other protocols (like Aave or Compound). When parsing Morpho transactions:
1. A Morpho supply creates a position in a Morpho market, which itself lends to an underlying protocol
2. The user does not directly interact with Aave -- Morpho does. So the user's TX events only show Morpho events, not the underlying Aave events.
3. If you track both Morpho and Aave positions for the same user, you might double-count: the user has a Morpho position, and Morpho has an Aave position on behalf of the user.
4. Morpho vaults (MetaMorpho) add another layer: User -> MetaMorpho Vault -> Morpho Markets -> Underlying Protocol.

**Why it happens:**
Protocol composability means positions are layered. Each layer emits its own events. If your parser handles each layer independently, positions get double or triple counted.

**How to avoid:**
1. Parse Morpho at the user's interaction level only. If a user deposits USDC into a MetaMorpho vault, create ONE journal entry: `erc20_token:USDC(-) / protocol_asset:morpho:USDC(+)`. Do NOT also create an Aave position entry.
2. Use Morpho's own events (Supply, Withdraw, Borrow, Repay, SupplyCollateral, WithdrawCollateral) from the Morpho Blue contract.
3. For MetaMorpho vaults, treat like ERC-4626: deposit/withdraw the vault shares, track as protocol_asset.
4. Price Morpho positions using the Morpho rate (shares -> assets conversion), not by looking at underlying protocol positions.

**Warning signs:**
- Same underlying asset appears in both Morpho and Aave positions
- Balance sheet total is larger than actual portfolio value
- Withdrawal from Morpho creates negative Aave position (impossible)

**Phase to address:**
Morpho parser milestone. Research Morpho Blue contract events (supply, borrow, liquidate, etc.) before starting. The MetaMorpho (vault) layer should be Phase 2 of Morpho support.

**Confidence:** MEDIUM -- Morpho Blue architecture is understood from training data but specific contract ABIs and event names should be verified against deployed contracts.

---

### Pitfall 7: L2 Gas Fee Miscalculation (Arbitrum/Polygon)

**What goes wrong:**
L2 chains have fundamentally different gas fee structures:
1. **Arbitrum**: Uses `gasUsed * effectiveGasPrice`, but some older TXs report L1 fees differently. Post-ArbOS 20 (Dencun), L1 data costs changed from calldata-based to blob-based pricing.
2. **Polygon**: Uses `gasUsed * gasPrice` like L1, but the native token is MATIC (or POL after the migration). Gas prices are in Gwei of MATIC, not ETH.
3. **Optimism/Base**: L1 fee component (`l1Fee`) exists in receipt data but the calculation changed after Ecotone upgrade (post-Dencun).

The current `calculate_gas_fee_wei()` handles L2 `l1Fee` via a simple addition (line 44-48), but this only works for pre-Dencun Optimism/Base. For Arbitrum, the `l1Fee` field doesn't exist -- the fee is fully captured in `gasUsed * gasPrice`.

**Why it happens:**
Each L2 has a unique gas model that evolves with upgrades. Developers test on Ethereum mainnet and assume the same gas calculation works everywhere.

**How to avoid:**
1. Create chain-specific gas calculation functions:
```python
GAS_CALCULATORS = {
    "ethereum": _calc_evm_gas,
    "arbitrum": _calc_arbitrum_gas,
    "optimism": _calc_op_gas,
    "base": _calc_op_gas,  # Same model as Optimism
    "polygon": _calc_evm_gas,  # Standard EVM model
    "bsc": _calc_evm_gas,
}
```
2. For Optimism/Base, handle both pre-Ecotone (`l1Fee` field) and post-Ecotone (fee included in `gasPrice`).
3. For all L2s, verify gas calculations against known transactions by comparing calculated fee with actual balance change.
4. Use the correct native token symbol per chain (already handled by `native_symbol()`, but verify MATIC vs POL on Polygon).

**Warning signs:**
- Gas expense totals that don't match actual native token balance decreases
- Zero gas fees on L2 transactions (means the l1Fee wasn't captured)
- Absurdly high gas fees on L2 (means l1Fee was double-counted)

**Phase to address:**
Multi-chain milestone (Arbitrum/Polygon). Should be researched and tested with real L2 transactions before deployment.

**Confidence:** MEDIUM -- L2 gas models are known from training data, but post-Dencun changes (2024) mean specifics should be verified against current Etherscan API responses for each chain.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded contract addresses in parser files | Quick to add new protocol | Address changes on upgrades, new deployments not auto-discovered, sprawling constants | Acceptable for MVP; migrate to DB/config for production |
| Using `dict` for tx_data throughout the pipeline | No schema enforcement, flexible | Runtime KeyError on missing fields, impossible to know what fields are available | Never -- should have a typed `TransactionData` model. Current approach is the #1 source of parser bugs. |
| `"unknown"` as ERC20 counterpart in GenericEVMParser (line 83) | Avoids crash on unknown transfers | Creates "unknown" accounts in the journal, makes reconciliation impossible for these TXs | Fix before diagnostics phase -- parser should attempt to find counterpart from transfer data |
| Single wallet_addresses set in TransactionContext | Simple API | Cannot distinguish between multiple tracked wallets in the same TX (e.g., user sends from wallet A to wallet B, both tracked) | Acceptable until multi-wallet-per-entity is implemented |
| Storing full tx_data as JSON blob | Flexible, future-proof | Large DB rows, no indexed queries on tx_data fields, migration pain if format changes | Acceptable -- but consider extracting key fields (chain, to, from, value) into indexed columns (already partially done) |
| `pop_transfer()` with loose matching (no token_address filter in many callers) | Simpler handler code | Consumes wrong transfer when TX has multiple ERC20 transfers of same type (e.g., flash loan TX with multiple USDC transfers) | Fix in protocol parsers that handle complex TXs (Aave, Morpho) |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Etherscan API | Using different API keys per chain (Arbiscan, Polygonscan, etc.) | Etherscan v2 unified API uses ONE api key + chainid parameter. Already correctly implemented in `etherscan_client.py`. |
| Etherscan API | Not handling the 10K result limit | Already handled via recursive splitting. But: the split bias is fixed at 50% -- for heavily skewed block ranges (e.g., one block with 5K TXs), this can cause redundant splitting. Low priority. |
| CoinGecko API | Looking up price by symbol instead of coingecko_id | Symbols are not unique (there are hundreds of tokens named "USDC" forks). Always resolve to coingecko_id first. Current `coingecko.py` should be checked for this. |
| Solana RPC | Fetching all signatures without limit | Public RPCs rate-limit aggressively. The current `_fetch_all_signatures()` has no delay between pages and will hit rate limits on public endpoints. Already partially mitigated by skipping without Helius key, but should add exponential backoff. |
| Etherscan for L2s | Assuming internal transactions work the same on L2 | Some L2 Etherscan APIs have incomplete internal TX data or different field names. Test with real data before relying on it. |
| Price APIs | Querying historic prices for tokens that didn't exist yet | CoinGecko returns 0 or errors for timestamps before a token's listing date. Handle gracefully -- mark price as "unavailable" not "zero." A zero price would make the tax calculation wrong. |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| AccountMapper issues N+1 queries per transaction | Each `_get_or_create` hits DB even with in-memory cache | Cache persists only per Bookkeeper instance. For bulk processing, ensure single Bookkeeper instance processes all TXs in a wallet. Already done correctly in `process_wallet()`. | N/A -- already mitigated |
| Sequential TX processing in `process_wallet()` | Slow for wallets with 10K+ transactions | Process in batches with periodic session flush/commit. Current code flushes per-TX which is fine for < 5K TXs. | > 5K TXs per wallet (~30min processing time) |
| Etherscan fetching all ERC20 transfers for entire block range | Downloads ALL token transfers even for blocks with no normal TXs | This is correct behavior -- you need token transfers for TXs that appear as contract interactions. But for very active wallets, this can be 100K+ records. Consider filtering by TX hash after fetch. | > 50K ERC20 transfers per wallet |
| Full `tx_data` JSON blob stored per transaction | 5-50KB per TX, reasonable | For a whale wallet with 100K TXs, this is 500MB-5GB of JSON blobs in the DB. | > 100K TXs (whale wallets) |
| Solana `_extract_sol_transfers` N*M matching | Creates transfers by matching all senders with all receivers | For complex TXs with many participants, this produces O(N*M) transfers, most of which are spurious. | Complex Solana TXs with 20+ accounts |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing API keys in tx_data JSON | Etherscan API key appears in request params, if raw request data is stored | Ensure only response data (not request params) is stored. Current code stores Etherscan response items, not request -- OK. |
| Exposing wallet addresses in error messages to frontend | Privacy leak -- wallet addresses are quasi-public but shouldn't be broadcast | Sanitize error messages. Current error schema includes `message` and `stack_trace` which could contain addresses. Consider stripping addresses from stack traces. |
| No validation on user-submitted TX hashes for "test parse" | A malicious TX hash could trigger expensive API calls or parse processing | Rate limit the `/api/parse/test` endpoint. Already a local app, but good practice. |
| Trusting token symbols from Etherscan/RPC without validation | Fake tokens can have misleading symbols (e.g., a scam token named "USDC") | Use canonical token registry with verified contract addresses. Don't trust `tokenSymbol` from API responses blindly. |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing parse errors without actionable context | User sees "TxParseError: list index out of range" and has no idea what to do | Show: TX hash (linked to explorer), what parser was tried, what transfers were found, and a suggested action (retry, classify manually, or report bug) |
| Parser stats showing "89% parsed" without explaining what the 11% are | User assumes 11% are lost/broken | Break down: X% parsed by generic, Y% by protocol, Z% unknown (with categories: pure approvals, dust, spam tokens, genuinely unknown) |
| Reconciliation showing discrepancies without explaining causes | User panics seeing -0.0001 ETH discrepancy | Categorize: gas rounding, rebasing token yield, internal TX not loaded, price approximation. Show which are expected vs concerning. |
| Tax report showing transfers in USD without VND conversion context | User files in VND, needs to understand the VND amounts | Always show dual currency. USD for reference, VND for filing. Show the exchange rate used. |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Protocol parser "works":** Often missing edge cases -- test with: multi-hop swaps, flash loans, liquidations, multicall batches, and transactions that fail after partial execution (reverted internal calls)
- [ ] **Multi-chain support "added":** Often missing: canonical token mapping, cross-chain FIFO, chain-specific gas calculation, internal transaction loading for the new chain
- [ ] **Parser diagnostics "complete":** Often missing: the ability to manually classify unknown TXs and have that classification persist on re-parse, parser version tracking (which version parsed which TX), and re-parse idempotency (re-parsing same TX produces identical results)
- [ ] **Lido parser "handles stETH":** Often missing: rebasing yield accounting, wstETH wrapping/unwrapping vs swap distinction, withdrawal queue handling (requestWithdrawals -> claimWithdrawal can take days)
- [ ] **Error dashboard "shows all errors":** Often missing: the distinction between "parser bug" (should be fixed in code) vs "unsupported operation" (needs new parser) vs "data quality issue" (Etherscan returned bad data) -- these need different actions
- [ ] **Balance validation "passes":** Often missing: validation against on-chain balances at specific block heights, not just sum-to-zero within journal entries. The journal can be internally consistent but still wrong if transfers were missed.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| ENTRY_TYPE mutation bug corrupted journal entry_types | LOW | Add a migration script that re-derives entry_type from parser + function selector for all existing journal entries. No data loss -- entry_type is metadata, not accounting data. |
| Wrong FIFO results from per-chain symbol separation | HIGH | Must invalidate all capital gains snapshots, recreate canonical token mapping, re-run FIFO from scratch. Design canonical mapping correctly before this becomes a problem. |
| Missing internal transactions | MEDIUM | Re-sync affected wallets (delete TXs after last_block_loaded, re-load with internal TX support). Then re-parse all affected TXs. |
| Rebasing token balance drift | MEDIUM | Implement reconciliation job, create catch-up journal entries for yield income. Calculate difference at hourly/daily checkpoints. |
| Double-counted Morpho + underlying positions | MEDIUM | Delete journal entries for the double-counted TXs, re-parse with corrected Morpho parser. Requires identifying which TXs were double-counted (query for same wallet + same timestamp + both Morpho and Aave entries). |
| L2 gas miscalculation | LOW | Re-parse affected TXs with corrected gas calculation. Gas is a separate split pair, so only gas expense accounts are affected. |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| ENTRY_TYPE class variable mutation | Parser diagnostics (FIRST priority) | Unit test: parse 100 TXs with same parser instance, verify no state leakage between TXs |
| `"unknown"` ERC20 counterpart | Parser diagnostics | Query: `SELECT COUNT(*) FROM accounts WHERE label LIKE '%unknown%'` should be near zero |
| Rebasing token (Lido stETH) | Lido parser milestone | Reconciliation check: journal balance vs on-chain balance for stETH holders within 0.1% tolerance |
| Pendle PT/YT complexity | Pendle parser milestone | Manual verification of 5+ real Pendle TXs against Pendle UI/etherscan |
| Multi-chain address collision | Multi-chain milestone (design canonical token map BEFORE adding second chain) | FIFO test: same token sold on chain B uses lots acquired on chain A |
| Internal TX completeness | Multi-chain milestone or diagnostics | Reconciliation check: ETH balance matches on-chain within gas-rounding tolerance |
| Morpho layered positions | Morpho parser milestone | No duplicate accounts: `SELECT symbol, COUNT(DISTINCT protocol) FROM accounts WHERE symbol='USDC' AND subtype='protocol_asset' GROUP BY wallet_id` should show Morpho OR Aave, not both for same underlying |
| L2 gas miscalculation | Multi-chain milestone | Gas expense for 10 known L2 TXs matches actual balance change within 1 wei |
| Untyped tx_data dict | Technical debt -- address incrementally | Introduce `TransactionData` Pydantic model alongside existing dict; migrate parsers one at a time |
| Loose pop_transfer matching | Protocol parser milestones | Test with flash loan TXs (multiple same-token transfers in one TX) |

---

## Protocol-Specific Pitfall Matrix

Quick reference for each new protocol parser being added.

| Protocol | Key Pitfall | Accounting Model | Research Needed |
|----------|------------|------------------|-----------------|
| Lido | Rebasing yield not captured by events | Periodic reconciliation + vault wrapping | HIGH -- verify stETH/wstETH contract events |
| Morpho Blue | Layered positions cause double-counting | Parse at user interaction level only | HIGH -- verify Morpho Blue event names and MetaMorpho vault interface |
| Pendle V2 | PT/YT decomposition is not a swap | Three-leg journal entries for SY split | HIGH -- verify Pendle router and market contract ABIs |
| Arbitrum | L1 gas component post-ArbOS 20 | Standard EVM gas model (L1 fee is in gasPrice) | MEDIUM -- verify against real Etherscan v2 responses |
| Polygon | MATIC -> POL migration changes native symbol | Check if MATIC or POL based on block height | MEDIUM -- verify Polygon Etherscan API native symbol |

---

## Sources

- **Codebase analysis:** Direct reading of `d:/work/crytax/src/cryptotax/parser/`, `d:/work/crytax/src/cryptotax/accounting/`, `d:/work/crytax/src/cryptotax/infra/`
- **Legacy reference docs:** `d:/work/crytax/docs/reference/Parser_Patterns.md`, `d:/work/crytax/docs/reference/Business_Logic.md`, `d:/work/crytax/docs/reference/Infrastructure_Patterns.md`
- **Known bugs from milestone context:** ENTRY_TYPE mutation, unknown counterpart, schema mismatch, Solana rate limiting, timezone mismatch
- **Domain knowledge (training data, MEDIUM confidence):** Lido rebasing mechanics, Pendle tokenization model, Morpho Blue architecture, L2 gas models
- **NOTE:** Web search was unavailable during research. Protocol-specific contract details (event names, function selectors, deployed addresses) should be verified against official documentation before implementation.

---
*Pitfalls research for: DeFi tax accounting -- protocol parsers, multi-chain support, parser diagnostics*
*Researched: 2026-02-18*
