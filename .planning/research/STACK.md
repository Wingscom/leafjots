# Stack Research: Parser Diagnostics, New Protocols, Multi-Chain

**Domain:** DeFi TX parsing diagnostics, protocol expansion, multi-chain support
**Researched:** 2026-02-18
**Confidence:** MEDIUM (web search unavailable; based on training data + existing codebase + legacy code analysis)

> **Note:** WebSearch and WebFetch were unavailable during this research session.
> All version numbers and API details are from training data (cutoff May 2025)
> and the existing codebase. Flag specific versions for validation before implementation.

---

## Existing Stack (Already Installed -- DO NOT re-add)

These are already in `pyproject.toml` and working with 341 tests:

| Technology | Version | Role |
|------------|---------|------|
| Python | >=3.11 | Runtime |
| FastAPI | >=0.115 | API framework |
| SQLAlchemy[asyncio] | >=2.0 | ORM + async DB |
| asyncpg | >=0.30 | PostgreSQL driver |
| Alembic | >=1.14 | Migrations |
| Pydantic | >=2.10 | Data validation |
| pydantic-settings | >=2.7 | Config |
| dependency-injector | >=4.43 | DI container |
| web3 | >=7.6 | EVM blockchain interaction |
| Celery[redis] | >=5.4 | Task queue |
| Redis | >=5.2 | Caching/broker |
| httpx | >=0.28 | HTTP client |
| tenacity | >=9.0 | Retry logic |
| openpyxl | >=3.1 | Excel output |
| cryptography | >=43.0 | Encryption |

---

## NEW Dependencies for This Milestone

### 1. Parser Diagnostics -- No New Libraries Needed

Parser diagnostics is an **architecture concern, not a library concern**. The existing
stack has everything needed:

| Concern | How to Solve | Library |
|---------|-------------|---------|
| Rich error context on parse failure | Extend `ParseErrorRecord` model + `TransactionContext` | SQLAlchemy (existing) |
| Structured error payloads in API | Expand Pydantic schemas in `api/schemas/errors.py` | Pydantic (existing) |
| Parse attempt trace/timeline | Add `parse_diagnostics` JSONB column to `ParseErrorRecord` | PostgreSQL JSONB (existing) |
| Frontend diagnostic UI | Expand Errors page with detail panels | React (existing) |
| Remaining transfers/events after parse | `TransactionContext.remaining_transfers()` already exists | -- |

**Why no new library:** The existing `ParseErrorRecord` stores `error_type`, `message`,
and `stack_trace`. The gap is not tooling but **data richness** -- we need to capture
which parser was tried, what transfers remained, which events were unrecognized, and
what context led to the failure. This is a schema + code change, not a dependency change.

**Specific additions to the data model:**

```python
# New columns on ParseErrorRecord (via Alembic migration)
parser_attempted: str           # Which parser was tried (e.g., "AaveV3Parser")
diagnostics: dict               # JSONB: structured diagnostic info
    # {
    #     "parsers_tried": ["GenericSwapParser", "GenericEVMParser"],
    #     "selected_parser": "GenericEVMParser",
    #     "remaining_transfers": [...],
    #     "remaining_events": [...],
    #     "unconsumed_count": 3,
    #     "balance_check": {"passed": false, "imbalance": {"ETH": "0.001"}},
    #     "function_selector": "0x617ba037",
    #     "decoded_function": "supply(address,uint256,address,uint16)",
    #     "tx_to_address": "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2",
    #     "chain": "ethereum"
    # }
```

**Confidence:** HIGH -- no external verification needed, purely internal architecture.

---

### 2. Lido stETH/wstETH Protocol Parser -- No New Libraries

| Concern | Status | Notes |
|---------|--------|-------|
| Lido contract interaction | Already covered by web3.py | Use function selectors like existing parsers |
| stETH Transfer events | Standard ERC20 Transfer events | Already captured by `extract_erc20_transfers` |
| wstETH wrap/unwrap | Function selector dispatch | Same pattern as AaveV3Parser |
| Rebase tracking | **Architecture concern** | See details below |

**Lido Architecture Details (MEDIUM confidence -- training data):**

Lido stETH is a **rebasing token** -- holder balances change daily without Transfer events.
This is the single biggest accounting challenge for Lido support.

Key contracts (Ethereum mainnet):
- **stETH (Lido):** `0xae7ab96520de3a18e5e111b5eaab095312d7fe84`
- **wstETH:** `0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0`

Key function selectors to handle:
```
submit(address _referral)     -> stake ETH, receive stETH
wrap(uint256 _stETHAmount)    -> wrap stETH to wstETH
unwrap(uint256 _wstETHAmount) -> unwrap wstETH to stETH
```

Key events:
```
Submitted(address sender, uint256 amount, address referral)  -- staking
TransferShares(address from, address to, uint256 sharesValue)  -- share-based transfer
TokenRebased(...)  -- daily rebase event (oracle report)
```

**Accounting pattern for Lido:**

| Operation | From Account | To Account |
|-----------|-------------|------------|
| ETH -> stETH (submit) | native_asset ETH (-) | erc20_token stETH (+) |
| stETH -> wstETH (wrap) | erc20_token stETH (-) | erc20_token wstETH (+) |
| wstETH -> stETH (unwrap) | erc20_token wstETH (-) | erc20_token stETH (+) |
| Rebase yield | income (-) | erc20_token stETH (+) |

**Critical: Rebase yield tracking.** stETH balance increases daily via oracle reports
(TransferShares events with `from=0x0000`). Two approaches:

1. **Track wstETH only (RECOMMENDED):** wstETH does NOT rebase. Its value increases
   relative to stETH. This means yield is realized only on unwrap or sale, making it
   a standard token. Much simpler accounting.

2. **Track stETH rebases:** Requires watching `TokenRebased` or `TransferShares`
   events from the Lido contract, computing daily yield. Complex and high-volume.

**Recommendation:** Treat wstETH as a standard ERC20 token. When user wraps stETH to
wstETH, record as a swap. Yield is implicitly captured in wstETH's increasing USD value.
This avoids the rebase accounting problem entirely. Only if user holds raw stETH do we
need rebase tracking (Phase 2 of Lido support).

Multi-chain addresses (MEDIUM confidence):
- **Arbitrum wstETH:** `0x5979d7b546e38e414f7e9822514be443a4800529`
- **Polygon wstETH:** `0x03b54a6e9a984069379fae1a4fc4dbae93b3bccd`
- **Optimism wstETH:** `0x1f32b1c2345538c0c6f582fcb022739c4a194ebb`

**Confidence:** MEDIUM for contract addresses (training data, verify before hardcoding).

---

### 3. Morpho Protocol Parser -- No New Libraries

The legacy codebase (`legacy_code/v2/parser/evm/contract/morpho.py`) contains extensive
Morpho parsing logic that maps directly to our parser architecture.

**Morpho Architecture (from legacy code analysis + training data):**

Morpho has evolved through multiple versions:
- **Morpho Blue:** Singleton lending market with market IDs (current focus)
- **MetaMorpho (ERC-4626 Vaults):** Wrapper vaults over Morpho Blue markets
- **Bundler/Adapter:** Multicall proxy for batched operations

Key contracts (MEDIUM confidence):
- **Morpho Blue (Ethereum):** `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb`
- **Morpho Blue (Base):** `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb` (same address)
- **General Adapter (Ethereum):** Varies, check deployment
- **Universal Rewards Distributor:** Protocol-specific per deployment

Key function selectors from legacy code:
```
supply(MarketParams,uint256,uint256,address,bytes)
withdraw(MarketParams,uint256,uint256,address,address)
supplyCollateral(MarketParams,uint256,address,bytes)
withdrawCollateral(MarketParams,uint256,address,address)
borrow(MarketParams,uint256,uint256,address,address)
repay(MarketParams,uint256,uint256,address,bytes)
liquidate(MarketParams,address,uint256,uint256,bytes)
```

Key events from legacy code:
```
Supply(bytes32 id, address caller, address onBehalf, uint256 assets, uint256 shares)
Withdraw(bytes32 id, address caller, address onBehalf, address receiver, uint256 assets, uint256 shares)
SupplyCollateral(bytes32 id, address caller, address onBehalf, uint256 assets)
WithdrawCollateral(bytes32 id, address caller, address onBehalf, address receiver, uint256 assets)
Borrow(bytes32 id, address caller, address onBehalf, address receiver, uint256 assets, uint256 shares)
Repay(bytes32 id, address caller, address onBehalf, uint256 assets, uint256 shares)
```

**Accounting patterns (from legacy code):**

| Operation | Pattern | Notes |
|-----------|---------|-------|
| supply | token_asset(-) / protocol_asset(+) | Same as Aave deposit |
| withdraw | protocol_asset(-) / token_asset(+) | Same as Aave withdraw |
| supplyCollateral | token_asset(-) / protocol_asset(+) | Collateral variant |
| withdrawCollateral | protocol_asset(-) / token_asset(+) | Collateral variant |
| borrow | protocol_debt(-) / token_asset(+) | Same as Aave borrow |
| repay | token_asset(-) / protocol_debt(+) | Same as Aave repay |
| ERC-4626 deposit (MetaMorpho) | token_asset(-) / erc20_token(+) (vault shares) | Swap underlying for vault token |
| ERC-4626 redeem (MetaMorpho) | erc20_token(-) (vault shares) / token_asset(+) | Swap vault token for underlying |
| rewards claim | income(-) / token_asset(+) | Via Universal Rewards Distributor |

**Complexity note:** Morpho uses a **Bundler** pattern where multiple operations are
batched via `multicall`. The legacy code handles this with `MorphoBundlerParser` that
delegates to the base `MorphoBlueFunctionalParser`. Our parser needs to handle:

1. **Direct calls** to Morpho Blue (simple case)
2. **Bundler calls** (multicall wrapping multiple operations)
3. **MetaMorpho vault** deposits/withdrawals (ERC-4626)

**Recommendation:** Start with direct Morpho Blue calls (supply/withdraw/borrow/repay/collateral).
Add Bundler support in a second pass. MetaMorpho vaults may be handled generically by
GenericSwapParser since they just appear as token swaps (underlying -> vault shares).

**Confidence:** MEDIUM -- legacy code provides concrete patterns, but contract addresses
and exact ABI details should be verified against current deployments.

---

### 4. Pendle Finance Parser -- No New Libraries, but HIGH Complexity

**Pendle Architecture (MEDIUM confidence -- training data):**

Pendle tokenizes yield into two components:
- **SY (Standardized Yield):** Wrapper around yield-bearing tokens (e.g., SY-stETH)
- **PT (Principal Token):** Represents the principal, trades at a discount before maturity
- **YT (Yield Token):** Represents the yield claim, decays to zero at maturity

Key contracts (MEDIUM confidence):
- **PendleRouter (Ethereum):** `0x888888888889758F76e7103c6CbF23ABbF58F946` (v4)
- **PendleRouter (Arbitrum):** `0x888888888889758F76e7103c6CbF23ABbF58F946`

Key operations:
```
mintSyFromToken(...)           -- wrap token into SY
redeemSyToToken(...)           -- unwrap SY to token
mintPyFromSy(...)              -- split SY into PT + YT
redeemPyToSy(...)              -- merge PT + YT back to SY (at maturity)
swapExactTokenForPt(...)       -- buy PT using token (via router)
swapExactPtForToken(...)       -- sell PT for token
addLiquiditySingleToken(...)   -- LP with single token
removeLiquiditySingleToken(...) -- Remove LP to single token
claimRewards(...)              -- claim YT yield + incentives
```

**Accounting patterns:**

| Operation | Pattern | Notes |
|-----------|---------|-------|
| Mint SY | token_asset(-) / erc20_token SY(+) | Standard wrap |
| Redeem SY | erc20_token SY(-) / token_asset(+) | Standard unwrap |
| Mint PT+YT | erc20_token SY(-) / erc20_token PT(+) + erc20_token YT(+) | Split |
| Redeem PT+YT | erc20_token PT(-) + erc20_token YT(-) / erc20_token SY(+) | Merge (at maturity) |
| Swap for PT | token_asset(-) / erc20_token PT(+) | Effectively a swap |
| Claim YT yield | income(-) / token_asset(+) | Yield income |
| LP add | token_asset(-) / protocol_asset(+) | Standard LP deposit |
| LP remove | protocol_asset(-) / token_asset(+) | Standard LP withdrawal |

**Why Pendle is complex:**
1. **Three token types** (SY, PT, YT) per market per maturity date
2. **Router uses multicall** for complex operations (wrap + split + LP in one TX)
3. **Maturity mechanics:** PT converges to underlying value at expiry
4. **YT accrued yield** must be tracked separately from YT token value
5. **Multiple underlying assets:** Each market wraps a different yield source (stETH, GLP, etc.)

**Recommendation:** Start with GenericSwapParser coverage (which will catch most Pendle
operations as token swaps) and build specific parser only for:
1. YT yield claims (income recognition)
2. PT+YT minting/redeeming (for correct 3-way split accounting)

Many Pendle router operations appear as simple token swaps at the transfer level,
so GenericSwapParser will handle ~60% of Pendle TXs correctly without a specific parser.

**Confidence:** MEDIUM -- Pendle's protocol design is stable but contract addresses
update with router versions. Verify v4 router address before implementation.

---

### 5. Multi-Chain Support (Arbitrum, Polygon) -- No New Libraries

**The existing codebase already supports Arbitrum and Polygon.** Evidence:

1. `CHAIN_IDS` in `etherscan_client.py` already includes:
   - `"arbitrum": 42161`
   - `"polygon": 137`

2. `Chain` enum already includes `ARBITRUM`, `POLYGON`

3. `NATIVE_SYMBOLS` in `gas.py` already maps `"polygon": "MATIC"`

4. Protocol parsers already register Arbitrum/Polygon addresses:
   - Aave V3: `"arbitrum"` and `"polygon"` pool addresses
   - Uniswap V3: `"arbitrum"` and `"polygon"` router addresses
   - Curve: `"arbitrum"` and `"polygon"` pool addresses

5. **Etherscan v2 API** (`api.etherscan.io/v2/api` with `chainid` param) is already
   implemented and handles all EVM chains with a single API key.

**What's actually needed for multi-chain is NOT stack changes but:**

| Need | What to Build | Library |
|------|--------------|---------|
| Chain selection in wallet creation | UI: chain dropdown in Wallets page | React (existing) |
| Per-chain EtherscanClient factory | Container creates client per chain | dependency-injector (existing) |
| Chain-aware sync orchestration | Celery tasks route to correct chain loader | Celery (existing) |
| L2 gas fee handling | `calculate_gas_fee_wei` already handles L1+L2 fees | -- |
| MATIC native token for gas | `NATIVE_SYMBOLS["polygon"] = "MATIC"` already set | -- |

**Polygon-specific note (MEDIUM confidence):** Polygon migrated from MATIC to POL
as the native gas token in September 2024. The Etherscan API still returns values in
MATIC/wei units. The symbol may need to be `"POL"` for newer transactions. Verify
this against current Polygonscan behavior.

**Arbitrum-specific note:** Arbitrum uses ETH for gas but has an L1 fee component
(`l1Fee` in transaction receipts). The existing `calculate_gas_fee_wei` already handles
this via the `l1_fee` field check.

**Confidence:** HIGH for existing support. MEDIUM for Polygon MATIC->POL transition.

---

### 6. ABI Decoding Enhancement -- eth-abi (Already Installed via web3)

For richer parser diagnostics, we need to decode function calls and events from raw
transaction data. The `eth-abi` library is already installed as a dependency of `web3.py`.

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| eth-abi | >=5.0 | ABI encoding/decoding | Already installed (web3 dependency) |
| eth-utils | >=4.0 | keccak, address utils | Already installed (web3 dependency) |
| eth-typing | >=4.0 | Type definitions | Already installed (web3 dependency) |

**Usage for diagnostics:**
```python
from eth_abi import decode
from eth_utils import function_signature_to_4byte_selector

# Decode function call from input data
selector = input_data[:10]  # "0x617ba037"
params = decode(['address', 'uint256', 'address', 'uint16'], bytes.fromhex(input_data[10:]))
```

**Confidence:** HIGH -- these are already in the dependency tree.

---

## Recommended Stack (NEW additions only)

### Core Technologies -- NONE NEW

No new core technologies are needed. The existing stack covers all requirements.

### Supporting Libraries -- NONE NEW

All required functionality exists in current dependencies or as architecture changes.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Alembic migration | Add JSONB `diagnostics` column to `parse_error_records` | Use existing Alembic setup |
| pytest fixtures | Add real TX fixtures for Lido/Morpho/Pendle testing | Store in `tests/fixtures/protocol_txs/` |

---

## Installation

```bash
# No new packages needed!
# The existing pyproject.toml already has everything required.

# If you want to verify eth-abi is available (it's a web3 dependency):
python -c "import eth_abi; print(eth_abi.__version__)"
```

---

## Alternatives Considered

| Category | Decision | Alternative | Why Not |
|----------|----------|-------------|---------|
| ABI decoding | Use eth-abi (via web3) | Manually decode with struct | eth-abi handles all Solidity types correctly |
| Rebase tracking | Track wstETH only (non-rebasing) | Track stETH rebases daily | Massive complexity for marginal accuracy gain |
| Morpho bundler | Start with direct calls only | Full bundler/multicall from day 1 | Bundler adds 3x complexity; handle 80% case first |
| Pendle parser | GenericSwap + targeted specific parser | Full protocol-specific parser for all operations | Most Pendle TXs look like swaps at transfer level |
| Multi-chain RPC | Continue with Etherscan v2 only | Add direct RPC via web3.py | Etherscan v2 already works for all target chains |
| Parse diagnostic storage | JSONB column | Separate diagnostic table | JSONB keeps data co-located with error record; simpler queries |
| Error categorization | Extend existing enum | New error taxonomy | Build on what works; extend ParseErrorType enum |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Brownie / Ape framework | Heavy DeFi development frameworks, overkill for parsing | web3.py + eth-abi directly |
| Forta / Tenderly SDK | Monitoring tools, not accounting tools | Custom parser with Etherscan data |
| thegraph / subgraph queries | Adds external dependency, can be unreliable, rate-limited | Etherscan v2 API for all TX data |
| Dune Analytics API | Analytics, not real-time TX loading | Etherscan v2 for TX data |
| Custom ABI decoder | Fragile, incomplete Solidity type handling | eth-abi (battle-tested, handles tuples, arrays, etc.) |
| Separate diagnostic service | Over-architecture for this scale | JSONB column in existing table |
| External error tracking (Sentry) | Overkill for local tool, adds external dependency | Structured error records in PostgreSQL |

---

## Stack Patterns by Protocol

### If adding a lending protocol (Morpho, Compound, Euler):
- Follow `AaveV3Parser` pattern: function selector dispatch
- Use existing `make_deposit_splits`, `make_borrow_splits`, etc. from `handlers/common.py`
- Register contract addresses per chain in `build_default_registry()`

### If adding a swap/DEX protocol:
- GenericSwapParser handles ~80% of cases via net-flow analysis
- Only add specific parser if GenericSwap misclassifies or misses protocol attribution
- Follow `UniswapV3Parser` pattern for complex cases (multicall, LP)

### If adding a yield protocol (Lido, Pendle):
- Yields that appear as token transfers: handled by existing infrastructure
- Rebasing tokens: use non-rebasing wrapped version (wstETH > stETH)
- Yield claims: use `make_yield_splits` from `handlers/common.py`

### If adding parser diagnostics:
- Capture diagnostic data in `TransactionContext` during parsing
- Store as JSONB in `ParseErrorRecord.diagnostics`
- Expose via API schema expansion
- Display in frontend Error detail panel

---

## Version Compatibility

| Existing Package | Compatible With | Notes |
|------------------|-----------------|-------|
| web3>=7.6 | eth-abi>=5.0, eth-utils>=4.0 | Already resolved in dependency tree |
| SQLAlchemy>=2.0 | PostgreSQL JSONB columns | Use `mapped_column(JSON)` for diagnostics |
| Pydantic>=2.10 | dict fields for JSONB data | Use `dict[str, Any]` in schemas |
| FastAPI>=0.115 | Pydantic v2 response models | Existing pattern works |

---

## Key Architecture Decisions (Not Libraries, But Critical)

### 1. ParseDiagnosticContext -- New Internal Class

```python
@dataclass
class ParseDiagnosticContext:
    """Captures diagnostic information during parsing for error analysis."""
    parsers_tried: list[str] = field(default_factory=list)
    selected_parser: str | None = None
    function_selector: str | None = None
    decoded_function: str | None = None
    remaining_transfers_count: int = 0
    remaining_events_count: int = 0
    remaining_transfers: list[dict] = field(default_factory=list)  # serialized
    remaining_events: list[dict] = field(default_factory=list)     # serialized
    balance_check: dict | None = None
    error_chain: list[str] = field(default_factory=list)  # ordered list of errors from each parser

    def to_dict(self) -> dict:
        return asdict(self)
```

### 2. Protocol Address Registry -- Config-Driven

For new protocols, use a centralized address config rather than hardcoding in each parser:

```python
PROTOCOL_ADDRESSES: dict[str, dict[str, dict[str, str]]] = {
    "lido": {
        "ethereum": {
            "steth": "0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
            "wsteth": "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0",
        },
        "arbitrum": {
            "wsteth": "0x5979d7b546e38e414f7e9822514be443a4800529",
        },
        "polygon": {
            "wsteth": "0x03b54a6e9a984069379fae1a4fc4dbae93b3bccd",
        },
    },
    "morpho": {
        "ethereum": {
            "blue": "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb",
        },
        "base": {
            "blue": "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb",
        },
    },
    "pendle": {
        "ethereum": {
            "router_v4": "0x888888888889758F76e7103c6CbF23ABbF58F946",
        },
        "arbitrum": {
            "router_v4": "0x888888888889758F76e7103c6CbF23ABbF58F946",
        },
    },
}
```

### 3. Enhanced ParseErrorType Enum

```python
class ParseErrorType(str, Enum):
    # Existing
    TX_PARSE_ERROR = "TxParseError"
    INTERNAL_PARSE_ERROR = "InternalParseError"
    HANDLER_PARSE_ERROR = "HandlerParseError"
    UNHANDLED_FUNCTION_ERROR = "UnhandledFunctionError"
    UNKNOWN_CHAIN_ERROR = "UnknownChainError"
    UNKNOWN_CONTRACT_ERROR = "UnknownContractError"
    UNKNOWN_TOKEN_ERROR = "UnknownTokenError"
    UNKNOWN_TRANSACTION_INPUT_ERROR = "UnknownTransactionInputError"
    UNSUPPORTED_EVENTS_ERROR = "UnsupportedEventsError"
    MISSING_PRICE_ERROR = "MissingPriceError"
    BALANCE_ERROR = "BalanceError"

    # New for diagnostics
    UNCONSUMED_TRANSFERS = "UnconsumedTransfers"         # Transfers left after parsing
    UNCONSUMED_EVENTS = "UnconsumedEvents"               # Events left after parsing
    PARSER_SELECTION_FAILED = "ParserSelectionFailed"     # No parser could handle TX
    MULTICALL_DECODE_ERROR = "MulticallDecodeError"       # Failed to decode bundler TX
    REBASE_TRACKING_ERROR = "RebaseTrackingError"         # stETH rebase issue
    MATURITY_CALCULATION_ERROR = "MaturityCalcError"      # Pendle PT/YT maturity issue
```

---

## Sources

- **Existing codebase analysis** (HIGH confidence):
  - `src/cryptotax/infra/blockchain/evm/etherscan_client.py` -- confirms Etherscan v2 with chainid
  - `src/cryptotax/domain/enums/chain.py` -- confirms Arbitrum/Polygon already in enum
  - `src/cryptotax/parser/defi/aave_v3.py` -- confirms parser pattern and multi-chain addresses
  - `src/cryptotax/parser/registry.py` -- confirms registry architecture
  - `src/cryptotax/db/models/parse_error_record.py` -- confirms current error model
  - `src/cryptotax/parser/utils/gas.py` -- confirms L2 gas handling and native symbols

- **Legacy code analysis** (MEDIUM confidence):
  - `legacy_code/v2/parser/evm/contract/morpho.py` -- Morpho Blue function handlers, events, bundler pattern
  - `legacy_code/v2/balance/morpho.py` -- Morpho Blue market position reading

- **Training data** (LOW-MEDIUM confidence, verify before implementation):
  - Lido contract addresses and events
  - Morpho Blue singleton address
  - Pendle router v4 address
  - Polygon MATIC -> POL migration status

---

*Stack research for: CryptoTax Vietnam -- Parser Diagnostics + Protocol Expansion + Multi-Chain*
*Researched: 2026-02-18*
