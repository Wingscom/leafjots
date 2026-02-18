# Architecture Research: Parser Diagnostics, New Protocol Parsers, Multi-Chain Registry

**Domain:** DeFi tax accounting parser system -- extension of existing architecture
**Researched:** 2026-02-18
**Confidence:** HIGH (core patterns from codebase analysis), MEDIUM (protocol specifics from training data + legacy code)

---

## Standard Architecture (Current State)

### System Overview

```
                         Bookkeeper (orchestrator)
                              |
                    +---------+---------+
                    |                   |
              ParserRegistry       AccountMapper
                    |                   |
     +--------------+--------+         |
     |              |        |         |
  Specific     GenericSwap  GenericEVM |
  Parsers      Parser       Parser    |
  (Aave,Uni,                          |
   Curve,PCS)                         |
     |              |        |         |
     +------+-------+--------+         |
            |                          |
    TransactionContext                 |
    (transfers + events)               |
            |                          |
            v                          v
       ParsedSplit[] ----------> JournalEntry + JournalSplits
                                       |
                                 ParseErrorRecord (on failure)
```

### Current Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| `Bookkeeper` | Orchestrates TX -> parse -> journal creation, error recording | ParserRegistry, AccountMapper, PriceService |
| `ParserRegistry` | Maps `(chain, address)` to ordered parser list with fallback chain | All parsers |
| `BaseParser` | Interface: `can_parse()` + `parse()` returning `ParsedSplit[]` | TransactionContext |
| `EventDrivenParser` | Declarative `EVENT_HANDLERS` dict dispatching to handler methods | TransactionContext |
| `TransactionContext` | Mutable working set: pop_transfer/pop_event consumption model | Parsers consume from it |
| `AccountMapper` | Lazy get-or-create accounts by hierarchical label key, session-cached | DB (Account model) |
| `ParseErrorRecord` | Records error_type + message for Error Dashboard | Bookkeeper writes it |

### Current Gaps

1. **No diagnostic data capture** -- Bookkeeper records pass/fail but not _why_ a parser was selected, what it consumed, or what remained unconsumed
2. **Registry is chain-agnostic** -- works for multi-chain addresses already but protocol address constants are hardcoded per file
3. **ParseErrorRecord too simple** -- has error_type + message but no structured diagnostic payload (remaining transfers, attempted parser, consumed events)
4. **No protocol enum for new parsers** -- Protocol enum only has: UNKNOWN, GENERIC, AAVE_V3, UNISWAP_V3, PANCAKESWAP, CURVE

---

## Recommended Architecture (Extended)

### Extended System Overview

```
                         Bookkeeper (orchestrator)
                              |
               +--------------+--------------+
               |              |              |
         ParserRegistry  AccountMapper  DiagnosticCollector
               |              |              |
     +---------+-------+      |              |
     |         |       |      |              |
  Protocol  Generic  Generic  |              |
  Parsers   Swap     EVM     |              |
     |         |       |      |              |
     +---------+-------+      |              |
               |              |              |
       TransactionContext     |              |
       (transfers + events)   |              |
               |              |              |
               v              v              v
          ParsedSplit[] -> JournalEntry  ParseDiagnostic
                                              |
                                    ParseErrorRecord (enriched)
```

### New/Modified Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| `DiagnosticCollector` | Captures parser selection trace, transfer consumption log, remaining unconsumed items, timing | Bookkeeper reads, stored in ParseDiagnostic |
| `ParseDiagnostic` (new model) | Structured diagnostic payload per parse attempt | Stored alongside ParseErrorRecord or JournalEntry |
| `ProtocolAddressConfig` (new) | Centralized multi-chain address registry loaded from config | ParserRegistry at build time |
| `LidoParser` (new) | Handles stETH submit/wrap/unwrap/withdrawal | TransactionContext, reusable handlers |
| `MorphoBlueParser` (new) | Handles supply/withdraw/borrow/repay on Morpho Blue | TransactionContext, reusable handlers |
| `PendleParser` (new) | Handles SY/PT/YT swaps and liquidity operations | TransactionContext, reusable handlers |

---

## Recommended Project Structure (Changes Only)

```
src/cryptotax/
  parser/
    generic/
      base.py              # BaseParser, EventDrivenParser (unchanged)
      evm.py               # GenericEVMParser (unchanged)
      swap.py              # GenericSwapParser (unchanged)
    defi/
      aave_v3.py           # existing
      uniswap_v3.py        # existing
      curve.py             # existing
      pancakeswap.py       # existing
      lido.py              # NEW: Lido stETH/wstETH parser
      morpho_blue.py       # NEW: Morpho Blue lending parser
      pendle.py            # NEW: Pendle PT/YT/SY parser
    cex/
      binance.py           # existing
    handlers/
      common.py            # existing (deposit, withdraw, borrow, repay, yield splits)
      wrap.py              # NEW: wrap/unwrap handler (for Lido, WETH, etc.)
    utils/
      context.py           # existing TransactionContext
      types.py             # existing (ParsedSplit, RawTransfer, EventData)
      transfers.py         # existing
      gas.py               # existing
      diagnostics.py       # NEW: DiagnosticCollector
    registry.py            # MODIFIED: uses ProtocolAddressConfig
    addresses.py           # NEW: centralized multi-chain address constants
  domain/
    enums/
      protocol.py          # MODIFIED: add LIDO, MORPHO, PENDLE
  db/
    models/
      parse_error_record.py  # MODIFIED: add diagnostic_data JSONB column
```

### Structure Rationale

- **`parser/addresses.py`:** Centralizes all protocol contract addresses in one file instead of scattering across parser modules. This is the single source of truth for multi-chain address mappings and makes adding Arbitrum/Polygon deployments trivial.
- **`parser/handlers/wrap.py`:** Wrap/unwrap is a common DeFi pattern (ETH->WETH, stETH->wstETH, SY tokens) that should be a reusable handler, not duplicated across parsers.
- **`parser/utils/diagnostics.py`:** Diagnostic collection belongs in parser utils because it tracks parser internals (what was consumed, what remains) and should not leak into the accounting layer.

---

## Architectural Patterns

### Pattern 1: Diagnostic Collector (Observer Pattern)

**What:** A lightweight observer that records what happens during parsing without changing parser logic. Parsers remain unaware of it.

**When to use:** Every parse attempt, whether successful or failed. The Bookkeeper wraps the parse call and collects diagnostics.

**Trade-offs:** Adds a small amount of overhead per TX (~1-2KB JSON). Worth it because debugging parse failures without diagnostics is extremely painful.

**Example:**
```python
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime


@dataclass
class ParseDiagnostic:
    """Structured diagnostic data for a single parse attempt."""
    tx_hash: str
    chain: str
    timestamp: datetime | None = None

    # Parser selection trace
    parsers_tried: list[str] = field(default_factory=list)
    parser_selected: str | None = None
    parser_can_parse_results: dict[str, bool] = field(default_factory=dict)

    # Transfer consumption
    transfers_input: int = 0
    transfers_consumed: int = 0
    transfers_remaining: list[dict] = field(default_factory=list)

    # Event consumption
    events_input: int = 0
    events_consumed: int = 0
    events_remaining: list[dict] = field(default_factory=list)

    # Result
    splits_produced: int = 0
    balance_check: dict[str, str] = field(default_factory=dict)  # {symbol: net_qty}
    entry_type: str | None = None
    duration_ms: float = 0.0

    def to_json(self) -> dict:
        """Serialize for JSONB storage."""
        return {
            "parsers_tried": self.parsers_tried,
            "parser_selected": self.parser_selected,
            "can_parse_results": self.parser_can_parse_results,
            "transfers": {
                "input": self.transfers_input,
                "consumed": self.transfers_consumed,
                "remaining": self.transfers_remaining,
            },
            "events": {
                "input": self.events_input,
                "consumed": self.events_consumed,
                "remaining": self.events_remaining,
            },
            "splits_produced": self.splits_produced,
            "balance_check": self.balance_check,
            "entry_type": self.entry_type,
            "duration_ms": self.duration_ms,
        }
```

**Bookkeeper integration (modified `process_transaction`):**
```python
import time

# Before parsing:
diagnostic = ParseDiagnostic(
    tx_hash=tx.tx_hash,
    chain=tx.chain,
    transfers_input=len(transfers),
    events_input=len(events),
)

# During parser selection:
for parser in parsers:
    can = parser.can_parse(tx_data, context)
    diagnostic.parsers_tried.append(parser.PARSER_NAME)
    diagnostic.parser_can_parse_results[parser.PARSER_NAME] = can
    if can:
        t0 = time.monotonic()
        parsed_splits = parser.parse(tx_data, context)
        diagnostic.duration_ms = (time.monotonic() - t0) * 1000
        diagnostic.parser_selected = parser.PARSER_NAME
        break

# After parsing:
diagnostic.transfers_remaining = [
    {"symbol": t.symbol, "from": t.from_address, "to": t.to_address, "value": str(t.value)}
    for t in context.remaining_transfers()
]
diagnostic.events_remaining = [
    {"event": e.event, "address": e.address}
    for e in context.remaining_events()
]
diagnostic.splits_produced = len(parsed_splits) if parsed_splits else 0

# Store in ParseErrorRecord or JournalEntry metadata
```

### Pattern 2: Centralized Multi-Chain Address Config

**What:** Single source of truth for all protocol contract addresses across all chains. Each protocol parser imports from this module instead of maintaining its own address dicts.

**When to use:** Always. The current pattern of each parser file having its own address constants works at 4 protocols but breaks down at 10+, especially when protocols deploy to the same set of L2s.

**Trade-offs:** Slightly more indirection (parser imports from addresses.py rather than defining locally). But the benefit of one place to add a new chain deployment vastly outweighs this.

**Example:**
```python
# parser/addresses.py

"""Centralized protocol contract addresses for all chains.

Add a new chain deployment by adding one entry here.
Parser modules import from this file instead of maintaining their own dicts.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProtocolDeployment:
    """A protocol's deployment on a specific chain."""
    chain: str
    contract_type: str  # "pool", "router", "nft_manager", "vault", etc.
    address: str


# --- Aave V3 ---
AAVE_V3: list[ProtocolDeployment] = [
    ProtocolDeployment("ethereum", "pool", "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"),
    ProtocolDeployment("arbitrum", "pool", "0x794a61358d6845594f94dc1db02a252b5b4814ad"),
    ProtocolDeployment("optimism", "pool", "0x794a61358d6845594f94dc1db02a252b5b4814ad"),
    ProtocolDeployment("polygon",  "pool", "0x794a61358d6845594f94dc1db02a252b5b4814ad"),
    ProtocolDeployment("base",     "pool", "0xa238dd80c259a72e81d7e4664a9801593f98d1c5"),
    ProtocolDeployment("avalanche","pool", "0x794a61358d6845594f94dc1db02a252b5b4814ad"),
]

# --- Lido ---
LIDO: list[ProtocolDeployment] = [
    ProtocolDeployment("ethereum", "steth",  "0xae7ab96520de3a18e5e111b5eaab095312d7fe84"),
    ProtocolDeployment("ethereum", "wsteth", "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"),
    ProtocolDeployment("ethereum", "withdrawal_queue", "0x889edc2edab5f40e902b864ad4d7ade8e412f9b1"),
    # wstETH is bridged to L2s as a regular ERC20, not a staking contract
    # No specific parser needed on L2s -- GenericSwapParser handles it
]

# --- Morpho Blue ---
MORPHO_BLUE: list[ProtocolDeployment] = [
    ProtocolDeployment("ethereum", "morpho_blue", "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb"),
    ProtocolDeployment("base",     "morpho_blue", "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb"),
]

# --- Pendle ---
PENDLE: list[ProtocolDeployment] = [
    ProtocolDeployment("ethereum", "router", "0x888888888889758f76e7103c6cbf23abbf58f946"),
    ProtocolDeployment("arbitrum", "router", "0x888888888889758f76e7103c6cbf23abbf58f946"),
]

# --- Convenience lookups ---
def get_addresses(deployments: list[ProtocolDeployment], chain: str, contract_type: str | None = None) -> list[str]:
    """Get all addresses for a protocol on a chain, optionally filtered by type."""
    return [
        d.address for d in deployments
        if d.chain == chain and (contract_type is None or d.contract_type == contract_type)
    ]

def get_address(deployments: list[ProtocolDeployment], chain: str, contract_type: str) -> str | None:
    """Get single address (first match). Returns None if not found."""
    addrs = get_addresses(deployments, chain, contract_type)
    return addrs[0] if addrs else None

def all_chains(deployments: list[ProtocolDeployment]) -> set[str]:
    """Get all chains a protocol is deployed on."""
    return {d.chain for d in deployments}
```

### Pattern 3: Function-Selector-First Parsing (for Lending Protocols)

**What:** Use the Solidity function selector (first 4 bytes of calldata) as the primary dispatch mechanism for lending protocols. This is what the existing `AaveV3Parser` already does and is the right pattern for Morpho Blue too.

**When to use:** Protocols where the function name uniquely determines the accounting treatment (supply vs borrow vs repay). Lending protocols universally fit this pattern.

**Trade-offs:** Requires maintaining a mapping of function selectors, which can break if a protocol upgrades its contracts. But in practice, function selectors are immutable for a given contract deployment, and the fallback chain (GenericSwap -> GenericEVM) catches unknown selectors.

**Example (Morpho Blue):**
```python
# Morpho Blue function selectors
SUPPLY_SELECTOR = "0x0c0a769b"           # supply(MarketParams,uint256,uint256,address,bytes)
WITHDRAW_SELECTOR = "0x5c2bea49"         # withdraw(MarketParams,uint256,uint256,address,address)
BORROW_SELECTOR = "0x50d8cd4b"           # borrow(MarketParams,uint256,uint256,address,address)
REPAY_SELECTOR = "0x20b76e81"            # repay(MarketParams,uint256,uint256,address,bytes)
SUPPLY_COLLATERAL_SELECTOR = "0x238d6579"  # supplyCollateral(MarketParams,uint256,address,bytes)
WITHDRAW_COLLATERAL_SELECTOR = "0x8720316d" # withdrawCollateral(MarketParams,uint256,address,address)
LIQUIDATE_SELECTOR = "0xd8eabcb8"        # liquidate(MarketParams,address,uint256,uint256,bytes)
```

### Pattern 4: Reusable Wrap/Unwrap Handler

**What:** A handler for the common wrap/unwrap pattern: user sends token A, receives token B at a known exchange rate (1:1 or on-chain rate). This covers ETH->WETH, stETH->wstETH, SY token wrapping, and similar patterns.

**When to use:** Lido wstETH wrapping, Pendle SY token creation, any vault deposit/withdrawal where the accounting is "swap asset for receipt token."

**Trade-offs:** Simple, but must handle both 1:1 wraps (WETH) and rate-based wraps (wstETH where 1 wstETH != 1 stETH).

**Example:**
```python
def make_wrap_splits(
    from_symbol: str,
    from_qty: Decimal,
    to_symbol: str,
    to_qty: Decimal,
    chain: str,
    protocol: str,
) -> list[ParsedSplit]:
    """Wrap: user sends from_token, receives to_token.

    For accounting, both sides are assets. The exchange rate is implicit
    in the from_qty/to_qty ratio. Price service handles USD conversion.
    """
    return [
        ParsedSplit(
            account_subtype="erc20_token",
            account_params={"chain": chain, "symbol": from_symbol},
            quantity=-from_qty,
            symbol=from_symbol,
        ),
        ParsedSplit(
            account_subtype="protocol_asset",
            account_params={"chain": chain, "protocol": protocol},
            quantity=to_qty,
            symbol=to_symbol,
        ),
    ]
```

---

## Data Flow

### Parse Flow (Extended with Diagnostics)

```
TX loaded from Etherscan/RPC
    |
    v
Bookkeeper.process_transaction(tx, wallet, entity_id)
    |
    +--- extract_all_transfers(tx_data, chain) -> list[RawTransfer]
    |         Handles: EVM native, ERC20 token_transfers, Solana SPL
    |
    +--- TransactionContext(transfers, wallet_addresses, events)
    |         Snapshot: transfers_input count, events_input count
    |
    +--- DiagnosticCollector.start(tx_hash, chain)
    |
    +--- ParserRegistry.get(chain, to_address) -> [parser1, parser2, ..., GenericEVM]
    |         For each parser:
    |           diagnostic.record_can_parse(parser.PARSER_NAME, result)
    |           If can_parse == True:
    |             diagnostic.record_selected(parser.PARSER_NAME)
    |             splits = parser.parse(tx_data, context)
    |             diagnostic.record_consumption(context)
    |             break
    |
    +--- Validate: sum(splits.quantity per symbol) == 0
    |         diagnostic.record_balance_check(by_symbol)
    |
    +--- For each ParsedSplit:
    |         AccountMapper.resolve_account(split, wallet) -> Account
    |         PriceService.price_split(symbol, qty, timestamp) -> (usd, vnd)
    |         Create JournalSplit(account_id, quantity, value_usd, value_vnd)
    |
    +--- JournalEntry created with all splits
    |         diagnostic.record_success()
    |
    +--- On error:
    |         ParseErrorRecord created with diagnostic_data JSONB
    |         diagnostic.record_failure(error_type, message)
    |
    v
  tx.status = PARSED | ERROR
```

### Multi-Chain Registry Build Flow

```
build_default_registry()
    |
    +--- For each PROTOCOL in addresses.py:
    |         For each chain with deployments:
    |           parser = ProtocolParser()
    |           For each address:
    |             registry.register(chain, address, parser)
    |
    +--- Fallback chain: [GenericSwapParser(), GenericEVMParser()]
    |
    +--- CEX chains: registry.register_chain_parsers("binance", [...])
    |
    v
  ParserRegistry ready
```

### Key Data Flows

1. **Parser Selection:** `ParserRegistry.get(chain, address)` returns ordered list. First parser where `can_parse()` returns True wins. Fallback chain ensures every TX gets _some_ parse result (even if just gas + unknown transfers).

2. **Transfer Consumption:** Parsers call `context.pop_transfer(...)` to claim transfers they account for. After parsing, `context.remaining_transfers()` shows what was not consumed. This is the most important correctness signal.

3. **Diagnostic Data:** Flows from Bookkeeper -> ParseDiagnostic -> stored as JSONB on ParseErrorRecord (for failures) or optionally on JournalEntry metadata (for debugging successful parses). The Error Dashboard reads this to show users exactly why a TX failed.

---

## Protocol-Specific Architecture

### Lido Parser Architecture

**Confidence:** MEDIUM (contract addresses and function patterns from training data, not verified against current docs)

Lido has three contract interactions relevant to tax accounting:

| Operation | Contract | Function | Accounting |
|-----------|----------|----------|------------|
| Stake ETH | stETH | `submit(address)` | native_asset(-ETH) / protocol_asset(+stETH) |
| Wrap stETH | wstETH | `wrap(uint256)` | protocol_asset(-stETH) / protocol_asset(+wstETH) |
| Unwrap wstETH | wstETH | `unwrap(uint256)` | protocol_asset(-wstETH) / protocol_asset(+stETH) |
| Request withdrawal | WithdrawalQueue | `requestWithdrawals(...)` | protocol_asset(-stETH) / protocol_asset(+withdrawal_nft) |
| Claim withdrawal | WithdrawalQueue | `claimWithdrawal(uint256)` | protocol_asset(-withdrawal_nft) / native_asset(+ETH) |
| Rebase (daily) | stETH | automatic balance change | income(-rebase_amt) / protocol_asset(+rebase_amt) |

**Key design decision:** stETH rebase is the hardest part. stETH uses a shares-based model where the balance increases daily without an explicit transfer event. The legacy code has `ERC20RebaseParser` with `_handle_stETH_rebase` and `_handle_Rebase` event handlers. For CryptoTax VN, use the `TransferShares` event (emitted on every stETH transfer) combined with periodic balance-change detection to capture rebase income.

**Parser type:** Function-selector-driven (like AaveV3Parser), because each Lido operation maps cleanly to a function call.

```python
class LidoParser(BaseParser):
    PARSER_NAME = "LidoParser"
    ENTRY_TYPE = EntryType.DEPOSIT

    def can_parse(self, tx_data, context):
        to_addr = tx_data.get("to", "").lower()
        chain = tx_data.get("chain", "ethereum")
        return to_addr in {steth_addr, wsteth_addr, withdrawal_queue_addr}.get(chain, set())

    def parse(self, tx_data, context):
        # Dispatch by function selector
        selector = tx_data.get("input", "")[:10].lower()
        if selector == SUBMIT_SELECTOR:
            return self._handle_stake(tx_data, context)
        elif selector == WRAP_SELECTOR:
            return self._handle_wrap(tx_data, context)
        # etc.
```

### Morpho Blue Parser Architecture

**Confidence:** HIGH (extensive legacy code reference in `legacy_code/v2/parser/evm/contract/morpho.py`)

Morpho Blue is a minimalist lending protocol with a single contract (`0xbbbb...`) that handles all markets. Key insight from legacy code: operations use `market_id` (bytes32) to identify which market, and the `onBehalf` parameter distinguishes the beneficiary from the caller (important for bundler patterns).

| Operation | Selector | Events | Accounting |
|-----------|----------|--------|------------|
| supply | `0x0c0a769b` | `Supply(id, caller, onBehalf, assets, shares)` | erc20(-) / protocol_asset(+) |
| withdraw | `0x5c2bea49` | `Withdraw(id, caller, onBehalf, receiver, assets, shares)` | protocol_asset(-) / erc20(+) |
| borrow | `0x50d8cd4b` | `Borrow(id, caller, onBehalf, receiver, assets, shares)` | protocol_debt(-) / erc20(+) |
| repay | `0x20b76e81` | `Repay(id, caller, onBehalf, assets, shares)` | erc20(-) / protocol_debt(+) |
| supplyCollateral | `0x238d6579` | `SupplyCollateral(id, caller, onBehalf, assets)` | erc20(-) / protocol_asset(+) |
| withdrawCollateral | `0x8720316d` | `WithdrawCollateral(id, caller, onBehalf, receiver, assets)` | protocol_asset(-) / erc20(+) |
| liquidate | `0xd8eabcb8` | `Liquidate(...)` | complex, similar to Aave liquidation |

**Key complexity:** Morpho has a Bundler (multicall wrapper) that batches multiple operations. The legacy code handles this via `MorphoBundlerParser` extending `DefaultMulticallProxyParser`. For CryptoTax VN's simpler architecture, handle the Morpho Blue contract directly using function selectors and use `GenericSwapParser` as fallback for bundler interactions that produce the same net flows.

**Parser type:** Function-selector-driven. Reuse existing `make_deposit_splits`, `make_withdrawal_splits`, `make_borrow_splits`, `make_repay_splits` from `handlers/common.py`.

### Pendle Parser Architecture

**Confidence:** LOW (limited legacy code, no direct parser found in legacy. Training data only for contract details.)

Pendle is the most complex of the three new protocols. Its token model has three layers:

```
Underlying Yield Token (e.g., stETH, sUSDe)
    |
    v
SY (Standardized Yield) -- wrapper, 1:1 with underlying
    |
    +--- PT (Principal Token) -- fixed yield, tradeable
    |
    +--- YT (Yield Token) -- variable yield, tradeable
```

Key operations:

| Operation | Contract | Accounting |
|-----------|----------|------------|
| Mint SY | SY contract | underlying(-) / sy_asset(+) |
| Redeem SY | SY contract | sy_asset(-) / underlying(+) |
| Swap exact token for PT | Router | token(-) / pt_asset(+) (swap) |
| Swap exact PT for token | Router | pt_asset(-) / token(+) (swap) |
| Add liquidity (PT+SY) | Router/Market | pt(-) / sy(-) / lp_asset(+) |
| Remove liquidity | Router/Market | lp_asset(-) / pt(+) / sy(+) |
| Redeem PT at maturity | Router | pt(-) / underlying(+) |
| Claim YT rewards | YT contract | income(-) / token(+) |

**Key design decision:** For CryptoTax VN, treat Pendle Router swaps via `GenericSwapParser` initially (which will correctly capture token A -> token B net flows), and only build a specific Pendle parser for LP operations and yield claiming where the accounting differs from a simple swap.

**Parser type:** Hybrid. Router swaps can fall through to GenericSwapParser. LP operations need specific handling similar to UniswapV3Parser's `_handle_lp_add`/`_handle_lp_remove`. Yield claiming needs a `make_yield_splits` handler (already exists in `handlers/common.py`).

---

## Multi-Chain Registry Architecture

### Current State

The `ParserRegistry` already supports multi-chain: `register(chain, address, parser)`. The `EtherscanClient` already supports all target chains via `CHAIN_IDS` dict. The `Chain` enum already includes ARBITRUM and POLYGON.

### What Needs to Change

1. **Parser address registration** must be extended to include Arbitrum and Polygon deployments for all existing protocols (Aave V3, Uniswap V3, Curve already have some L2 addresses)
2. **Gas fee calculation** already handles L2 l1Fee (Optimism, Base, Arbitrum) -- no changes needed
3. **Native symbol mapping** already covers all chains (`NATIVE_SYMBOLS` dict in `gas.py`) -- no changes needed
4. **No new infrastructure needed** -- EVMTxLoader + EtherscanClient work for any EVM chain already

### Registry Build Pattern (Extended)

```python
# In registry.py, modified build_default_registry():

def build_default_registry() -> ParserRegistry:
    from cryptotax.parser.addresses import (
        AAVE_V3, LIDO, MORPHO_BLUE, PENDLE,
        UNISWAP_V3_ROUTERS, UNISWAP_V3_NFT, CURVE_POOLS,
        PANCAKESWAP_ROUTERS,
        get_addresses, get_address, all_chains,
    )

    registry = ParserRegistry()

    # Aave V3 -- all chains
    aave_parser = AaveV3Parser()
    for chain in all_chains(AAVE_V3):
        pool_addr = get_address(AAVE_V3, chain, "pool")
        if pool_addr:
            registry.register(chain, pool_addr, aave_parser)

    # Lido -- Ethereum only for staking contracts
    lido_parser = LidoParser()
    for contract_type in ["steth", "wsteth", "withdrawal_queue"]:
        addr = get_address(LIDO, "ethereum", contract_type)
        if addr:
            registry.register("ethereum", addr, lido_parser)

    # Morpho Blue -- Ethereum + Base
    morpho_parser = MorphoBlueParser()
    for chain in all_chains(MORPHO_BLUE):
        addr = get_address(MORPHO_BLUE, chain, "morpho_blue")
        if addr:
            registry.register(chain, addr, morpho_parser)

    # Pendle -- Ethereum + Arbitrum
    pendle_parser = PendleParser()
    for chain in all_chains(PENDLE):
        for addr in get_addresses(PENDLE, chain, "router"):
            registry.register(chain, addr, pendle_parser)

    # ... existing Uniswap, Curve, PancakeSwap registrations (refactored to use addresses.py)

    return registry
```

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 wallets | Current architecture works fine. Single-threaded Bookkeeper processes TXs sequentially per wallet. |
| 10-100 wallets | Celery workers process wallets in parallel. ParserRegistry is stateless and can be shared across workers. TransactionContext is per-TX so no contention. |
| 100+ wallets | Consider batch-loading protocol addresses from a config table instead of hardcoded dicts. DiagnosticCollector data may need retention policy (delete after 30 days for parsed TXs, keep for errors). |

### Scaling Priorities

1. **First bottleneck:** Etherscan API rate limits (5 calls/second free tier). Already handled by `RateLimitedClient`. Solution: use paid API keys or switch to direct RPC node for high-volume.
2. **Second bottleneck:** Sequential TX processing within a wallet (must be chronological for FIFO). This is inherently serial. Parallelism comes from processing different wallets simultaneously.

---

## Anti-Patterns

### Anti-Pattern 1: Mutating ENTRY_TYPE on Parser Instance

**What people do:** The existing AaveV3Parser, UniswapV3Parser, CurvePoolParser all mutate `self.ENTRY_TYPE` during `parse()`:
```python
self.ENTRY_TYPE = EntryType.DEPOSIT  # BAD: mutates shared instance
```

**Why it's wrong:** Parser instances are shared across transactions in the registry. If two Celery workers process different TXs using the same parser instance, the ENTRY_TYPE from one TX could leak into another. Even without concurrency, it violates the principle that parsers should be stateless.

**Do this instead:** Return the entry type alongside the splits, or include it in a result dataclass:
```python
@dataclass
class ParseResult:
    splits: list[ParsedSplit]
    entry_type: EntryType
    parser_name: str
```
This is a **pre-existing issue** in the codebase that should be fixed before adding more parsers.

### Anti-Pattern 2: Deep Inheritance for Protocol Parsers

**What people do:** Legacy code has 5+ levels: RootParser -> EVMParser -> EVMContractParser -> EventDrivenParser -> ExtEventDrivenParser -> ProtocolParser.

**Why it's wrong:** Fragile base class problem. Changes to any intermediate level can break all descendants. Hard to test in isolation.

**Do this instead:** The current codebase already does this correctly with max 2 levels (BaseParser -> ProtocolParser). Keep it this way. Use composition (handlers) for shared accounting logic, not inheritance.

### Anti-Pattern 3: Storing Raw TX Data as Single JSON Blob

**What people do:** `tx_data = json.dumps(raw)` stores the entire Etherscan response as a single text field.

**Why it's wrong for diagnostics:** When a parse fails, you need to inspect specific parts of the TX data (transfers, events, function input). Parsing the JSON blob every time is wasteful, and the structure varies by chain.

**Do this instead:** Keep the JSON blob for completeness but add structured columns for commonly queried fields: `from_addr`, `to_addr`, `value_wei`, `gas_used`, `block_number`, `status` (which already exist on the Transaction model). For diagnostics, extract and store `token_transfers` count and `input` selector separately. The current model already has some of these -- extend with `function_selector VARCHAR(10)` and `transfer_count INT` columns.

---

## Integration Points

### External Services

| Service | Integration Pattern | Multi-Chain Notes |
|---------|---------------------|-------------------|
| Etherscan v2 API | `EtherscanClient` with chainid param | Already supports all target chains. Single API key. |
| CoinGecko | `PriceService` for USD/VND pricing | Chain-agnostic (prices by symbol). No changes for multi-chain. |
| RPC nodes | Not yet used (Etherscan handles TX loading) | Needed for on-chain balance verification (reconciliation feature). |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Bookkeeper <-> ParserRegistry | Direct method call `registry.get(chain, addr)` | Stateless. Registry is shared singleton. |
| Bookkeeper <-> AccountMapper | Async method calls, session-scoped | AccountMapper caches per session. New session = new cache. |
| Bookkeeper <-> DiagnosticCollector | Bookkeeper owns collector, passes data | No DB interaction in collector itself -- just data aggregation. |
| ParserRegistry <-> addresses.py | Import at `build_default_registry()` time | addresses.py is pure data, no side effects. |
| Parser <-> handlers/common.py | Direct function calls returning `list[ParsedSplit]` | Handlers are pure functions. No state. |
| Parser <-> TransactionContext | Mutable interaction (pop_transfer, pop_event) | Context is per-TX. Parser must not hold reference across TXs. |

---

## Build Order (Dependencies)

```
Phase A: Foundation (no external dependencies)
  1. ParseDiagnostic dataclass + DiagnosticCollector
  2. Extend ParseErrorRecord with diagnostic_data JSONB column
  3. Fix ENTRY_TYPE mutation anti-pattern (ParseResult dataclass)
  4. addresses.py centralized address config

Phase B: Diagnostic Integration (depends on A)
  5. Modify Bookkeeper.process_transaction to collect diagnostics
  6. Extend Error Dashboard API to return diagnostic data
  7. Frontend: show diagnostic details on error view

Phase C: New Protocol Parsers (depends on A.4 for addresses)
  8. handlers/wrap.py (reusable wrap/unwrap handler)
  9. LidoParser (simplest: stake + wrap/unwrap)
  10. MorphoBlueParser (supply/withdraw/borrow/repay -- familiar pattern)
  11. PendleParser (most complex: SY/PT/YT, defer to GenericSwap where possible)

Phase D: Multi-Chain Extension (depends on A.4)
  12. Extend addresses.py with all Arbitrum + Polygon deployments
  13. Refactor build_default_registry() to use addresses.py
  14. Test with Arbitrum/Polygon wallets (EVM loader already works)

Phase E: Protocol Enum + Dashboard Updates
  15. Add LIDO, MORPHO, PENDLE to Protocol enum
  16. Parser stats breakdown by protocol in dashboard
```

**Critical path:** A.3 (ENTRY_TYPE fix) should happen first because all new parsers will inherit from BaseParser and we do not want them repeating the mutation anti-pattern. A.4 (addresses.py) is needed before both C and D.

---

## Sources

- **Codebase analysis (HIGH confidence):** Direct reading of all parser source files in `d:/work/crytax/src/cryptotax/parser/`, bookkeeper, registry, account mapper, transaction models, API schemas
- **Legacy code analysis (HIGH confidence for patterns, MEDIUM for protocol specifics):** `d:/work/crytax/legacy_code/v2/parser/evm/contract/morpho.py` (extensive Morpho Blue implementation), `d:/work/crytax/docs/reference/Parser_Patterns.md` (distilled legacy reference)
- **Protocol contracts (MEDIUM confidence):** Lido contract addresses and function signatures from training data. Morpho Blue addresses confirmed via legacy code. Pendle router address from training data. All should be verified against current deployments before implementation.
- **Multi-chain addresses (HIGH confidence for Aave/Uniswap, MEDIUM for others):** Aave V3 and Uniswap V3 L2 addresses already in codebase and verified. Morpho Blue on Base address from legacy code patterns. Pendle on Arbitrum from training data.

### Validation Flags

- [ ] **Lido contract addresses** -- Verify stETH, wstETH, WithdrawalQueue addresses on Ethereum mainnet
- [ ] **Morpho Blue function selectors** -- Verify against deployed contract ABI (selectors from training data)
- [ ] **Pendle Router address** -- Verify current v5 router address on Ethereum and Arbitrum
- [ ] **Pendle SY/PT/YT accounting** -- Verify tax treatment of PT maturity (is it a disposal event for VN tax?)

---
*Architecture research for: CryptoTax Vietnam -- Parser Extension Milestone*
*Researched: 2026-02-18*
