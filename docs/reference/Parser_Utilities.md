# Parser Utilities -- Distilled Reference

> Distilled from Pennyworks/ChainCPA legacy code (`v2/parser/evm/generic_utils.py`,
> `v2/util.py`, `v2/types.py`, `v2/settings.py`, `v2/registry.py`,
> `v2/chain_info_provider.py`, `analysis/*.py`, `common/*.py`).
> Source: ~421 files, ~50K LOC. This document extracts portable patterns and domain
> knowledge for CryptoTax Vietnam.

---

## Patterns -- Design Patterns, Why Good

### 1. Transfer Type Hierarchy (generic_utils.py)

The legacy code defines a layered transfer abstraction that normalizes all on-chain
value movements into a common interface:

```
Raw Log Data
  -> Transfer (namedtuple: chain, token_addr, from_addr, to_addr, value, block_number)
  -> NativeTransfer (NamedTuple: from_addr, to_addr, value)
  -> NFTTransfer (NamedTuple: chain, token_addr, token_id, from_addr, to_addr, block_number)
  -> ERC1155Transfer (NamedTuple: chain, token_addr, token_id, from_addr, to_addr, value, block_number)
  -> AnyTokenTransfer (class: token, from_addr, to_addr, amount as Decimal)
     -> TokenTransfer (ERC20 with metadata)
     -> NFTTokenTransfer (NFT with metadata)
     -> Erc1155HashTransferByTokenTransfer (ERC1155 with metadata)
```

**Why good:** Raw transfers use integer wei values and raw addresses. "Upcasted"
transfers (AnyTokenTransfer and subclasses) carry resolved token metadata and decimal
amounts. This two-tier system lets the parser work with raw data first (fast, no
lookups) and resolve token metadata only when needed.

**Port this pattern.** Use Pydantic models instead of namedtuples for validation.

### 2. TransactionContext -- Mutable Working Set (generic_utils.py)

`TransactionContext` is the central data object passed through parser pipelines.
It collects all extracted data from a transaction and provides peek/pop/yield
operations for consuming transfers and events:

```
TransactionContext
  .contract_events: List[EventData]        # decoded smart contract events
  .token_transfers: List[Transfer]         # ERC20 Transfer events
  .native_transfers: List[Transfer]        # ETH/native value + internal txs
  .nft_transfers: List[NFTTransfer]        # ERC721 transfers
  .erc1155_transfers: List[ERC1155Transfer] # ERC1155 transfers
  ._map: ParserMap                         # wallet/account lookup
```

Operations follow a **consume-as-you-go** pattern:
- `peek_*()` -- find matching transfers without removing them (returns list of (index, transfer))
- `pop_*()` -- find and remove the first matching transfer (raises if not found)
- `yield_*()` -- generator that yields and removes all matching transfers
- `find_event()` / `pop_event()` / `yield_events()` / `filter_events()` -- same for events

**Why good:** Parsers claim the transfers they handle by popping them. After all
parsers run, any remaining (unconsumed) transfers are "unknown" and can be flagged.
This is a natural way to track parser coverage.

**Why broken in legacy:** The class conflates raw and upcasted transfers, has
duplicate method signatures, mixes class-level and instance-level state, and the
deprecated `TransferManager` / `EventManager` create unnecessary adaptor layers.

**Port the concept, rewrite the implementation.** Clean separation of raw vs.
resolved transfers. Single unified API surface.

### 3. GenericMethod -- Stateless Utility Class (generic_utils.py)

`GenericMethod` collects reusable functions that don't belong to any specific parser.
Functions include:
- `get_all_related_transfers()` -- collect all transfers related to our wallets
- `get_contract_events()` -- decode events from ABI
- `load_all_events()` -- decode events with ABI fallback enrichment
- `get_fast_transfers_from_log()` -- optimized ERC20 transfer extraction using hardcoded ABI topic
- `get_fast_nft_transfers_from_log()` -- optimized NFT/ERC1155 transfer extraction
- `find_swap_flows()` -- detect inflow/outflow pairs for swap journaling
- `check_same_symbol_fees()` -- detect single-token fee transfers

**Why good:** Separates generic reusable logic from protocol-specific parsers. Any
parser can call these without inheritance coupling.

**Why broken in legacy:** It's a class with only @classmethod methods (should be a
module of functions), has duplicate method names, and implicit dependencies.

**Port as a module of pure functions.**

### 4. Fast Log Decoding with Hardcoded Topics (generic_utils.py)

Instead of loading full contract ABIs to decode Transfer events, the legacy code
hardcodes the well-known event topic signatures and uses the ABI decoder directly:

```python
ERC20_TRANSFER_TOPIC = "0xddf252ad..."  # Transfer(address,address,uint256)
ERC1155_TRANSFER_SINGLE = "0xc3d58168..."
ERC1155_TRANSFER_BATCH = "0x4a39dc06..."
NFT_TRANSFER_TOPIC = "0xddf252ad..."  # Same hash, differentiated by topic count
```

Differentiation between ERC20 Transfer and ERC721 Transfer (same topic hash):
- ERC20: 3 topics (from, to indexed) + 32-byte data (value)
- ERC721: 4 topics (from, to, tokenId all indexed) + 0-byte data

**Why good:** Avoids ABI loading for the most common event types. Very fast.

**Port this pattern directly.** These topic hashes are universal EVM constants.

### 5. Net Transfer Calculation (generic_utils.py)

`net_transfers_by_addr()` aggregates all transfers into a `{address: {token: net_amount}}`
map. Zero-value entries are filtered out. This enables:
- Detecting net-zero transfers (spam, internal routing)
- Finding the wallet's net position change from a transaction
- Simplifying complex multi-hop swaps into simple in/out pairs

**Port this directly.** Essential for generic swap detection.

### 6. Override System (analysis/override_utils.py)

The override system uses Pydantic models to validate and apply runtime overrides
for parsers and tokens without modifying persistent configuration:

```
OverrideConfig
  .parsers: List[ParserOverride]   # chain + address + parser_class + params
  .tokens: List[TokenOverride]     # chain + address + symbol + decimals + vault fields

Sources (merged with priority):
  1. --override-file (JSON file)
  2. --override-parsers (inline JSON CLI arg)
  3. --override-tokens (inline JSON CLI arg)
  Inline overrides take precedence over file overrides for same address.
```

Applied via `apply_overrides(config, token_map, contract_map)` which calls
`apply_token_overrides()` and `apply_parser_overrides()` separately.

**Why good:** Enables testing new parsers on specific transactions without
deploying them. Essential for development workflow: decode a failing TX, write
a parser, test with override, then register permanently.

**Port this pattern.** Simplify by using Pydantic v2 natively (legacy already uses it).

### 7. Registry / Singleton Factory (registry.py)

Uses `@lru_cache` to create singleton services:

```python
@lru_cache
def get_ref_api():
    from settings import settings
    return ReferenceAPI(settings.reference_api_url)
```

Documentation warns against three anti-patterns:
1. DO NOT import the function and cache result at module scope
2. DO NOT use `from registry import get_ref_api` (breaks monkeypatching)
3. ALWAYS call the factory at the point of use

**Do NOT port this pattern.** Use dependency-injector instead. The lru_cache
singleton approach breaks testability and makes DI impossible. The legacy
documentation itself admits the pattern is fragile.

### 8. Chain Info Provider (chain_info_provider.py)

`ChainInfoProvider` provides chain metadata via a cached class method:

```python
class ChainInfo(NamedTuple):
    id: str
    name: str
    decimals: int        # native token decimals (18 for ETH, 8 for BTC)
    evm_id: int | None   # EVM chain ID (1 for mainnet, 137 for polygon)
    avg_block_time: float | None
    native_symbol: str   # ETH, AVAX, MATIC, etc.
    url_tx_template: str # block explorer URL template
```

**Port the data model.** Use a config-driven approach (JSON/DB) instead of API calls
to a reference service. The ChainInfo fields are exactly what we need for multi-chain
support.

### 9. Event Decoder / Call Tree Analysis (analysis/decode_events.py)

The `EventDecoder` class provides transaction debugging by:
1. Decoding the full call tree (including multicalls at any depth)
2. Computing a "multicall hash" (MD5 of parser:function sequence) to identify
   unique transaction patterns
3. Enriching events with ABIs from external sources when the parser's ABI
   doesn't cover all contracts in the transaction
4. Writing decoded calls and events to files for analysis

The multicall hash is used to group transactions by their execution pattern,
enabling batch analysis of similar transactions.

**Port the concept.** The parser debug page in our dashboard needs exactly this:
decode a TX, show which parser handled it, show the call tree, show events.

### 10. Error Resolution Tracking (analysis/error_resolution_tracker.py)

Tracks parse errors with resolution status:

```python
ErrorResolutionTracker
  .mark_fixed(error_id, action, person, notes)
  .mark_all_fixed_by_contract(contract_address, action, error_type, ...)
  .mark_skipped(error_id, reason)
  .get_pending_errors(error_type)
  .get_summary() -> {pending: N, fixed: N, skipped: N}
  .generate_resolution_report() -> formatted string
```

**Port the concept into the DB/API.** Our Error Dashboard page needs similar
functionality: list errors, mark resolved, track who fixed what.

### 11. VCR-Based Test Recording (common/vcr_handler.py)

Uses vcrpy to record and replay HTTP interactions for tests:
- CI mode: `RecordMode.NONE` (no network access, fail if cassette missing)
- Local mode: `RecordMode.ONCE` (record new cassettes, replay existing)
- Filters sensitive data: API keys, cookies, authorization headers
- Normalizes request URIs for reproducibility

**Port this pattern.** Essential for testing blockchain RPC and price API calls
without hitting real networks. Ensures tests are deterministic.

### 12. Request Counting (common/requests_count.py)

Context manager that monkey-patches `requests.Session.send` to count HTTP requests:

```python
with patch_count_request() as result:
    # ... code that makes HTTP requests ...
    assert result["request_count"] <= 5  # verify no excessive API calls
```

**Nice to have.** Useful for monitoring API rate limit compliance in tests.

---

## Key Interfaces -- Abstract Classes, Signatures

### Transfer Types (to rewrite as Pydantic models)

```python
# Raw transfer (from log parsing, before token resolution)
class RawTransfer(BaseModel):
    chain: Chain
    token_address: str | None     # None for native transfers
    from_address: str
    to_address: str
    value: int                    # raw wei/smallest unit
    block_number: int | None

# Resolved transfer (after token metadata lookup)
class ResolvedTransfer(BaseModel):
    token: Token                  # includes symbol, decimals, etc.
    from_address: str
    to_address: str
    amount: Decimal               # human-readable amount

# Transfer types enum
class TransferType(str, Enum):
    NATIVE = "native"
    INTERNAL = "internal"
    ERC20 = "erc20"
    NFT = "nft"
    ERC1155 = "erc1155"
```

### TransactionContext Interface (to rewrite)

```python
class TransactionContext:
    """Mutable working set of transfers and events for a transaction."""

    # Factory
    @classmethod
    def from_transaction(cls, tx, parser, chain) -> "TransactionContext": ...

    # Transfer operations (peek = read, pop = read + remove, yield = iterate + remove)
    def peek_transfers(self, type, *, from_addr, to_addr, token_addr, value) -> list: ...
    def pop_transfer(self, type, *, from_addr, to_addr, token_addr, value) -> Transfer: ...
    def yield_transfers(self, type, *, from_addr, to_addr, token_addr) -> Iterator: ...

    # Event operations
    def find_event(self, *, event_name, address, args) -> EventData | None: ...
    def pop_event(self, *, event_name, address, args) -> EventData: ...
    def yield_events(self, *, event_name, address, args) -> Iterator[EventData]: ...
    def filter_events(self, *, event_name, address, args) -> list[EventData]: ...

    # Aggregate operations
    def get_related_transfers(self, types: set[TransferType]) -> list[ResolvedTransfer]: ...
    def net_transfers_by_address(self) -> dict[str, dict[str, Decimal]]: ...
```

### ChainInfo Interface

```python
class ChainInfo(BaseModel):
    chain_id: str
    name: str
    native_decimals: int
    evm_chain_id: int | None
    avg_block_time_seconds: float | None
    native_symbol: str
    explorer_tx_url_template: str   # e.g., "https://etherscan.io/tx/{hash}"

class ChainRegistry:
    def get(self, chain: Chain) -> ChainInfo: ...
    def all_chains(self) -> dict[Chain, ChainInfo]: ...
```

### Settings Interface

```python
class Settings(BaseSettings):
    # Database
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str

    # API keys (all optional, loaded from .env)
    alchemy_api_key: str = ""
    etherscan_api_key: str = ""
    coingecko_api_key: str = ""

    # Rate limits
    etherscan_api_max_rate_per_min: float = 120.0

    # Computed
    @property
    def database_url(self) -> str: ...

    class Config:
        env_file = ".env"
```

### Gas Fee Calculation (pure function, port directly)

```python
def calculate_gas_fee_wei(tx_data: dict, chain: Chain | None = None) -> int:
    """
    Calculate gas fee in wei from transaction receipt.
    Formula: gasUsed * effectiveGasPrice + l1Fee (for L2 chains)

    Handles:
    - Optimism-specific fallback for effectiveGasPrice
    - L1 fee for L2 chains (Optimism, Base, Arbitrum)
    - Hex-encoded l1Fee values
    """

def calculate_gas_fee_decimal(tx_data: dict, chain: Chain) -> Decimal:
    """Convert gas fee to native token units (ETH, AVAX, etc.)."""
```

### Override System Interface

```python
class ParserOverride(BaseModel):
    chain: str
    address: str           # contract address
    parser_class: str      # parser class name
    params: dict | None    # optional parser init params

class TokenOverride(BaseModel):
    chain: str
    address: str           # token contract address
    symbol: str
    decimals: int | None
    type: str | None       # "vault", "custom_vault"
    protocol: str | None
    conversion_func_name: str | None  # for vault tokens

class OverrideConfig(BaseModel):
    parsers: list[ParserOverride]
    tokens: list[TokenOverride]

    @staticmethod
    def load_from_file(path: str) -> "OverrideConfig": ...
    @staticmethod
    def merge(file_config, inline_parsers, inline_tokens) -> "OverrideConfig": ...
```

### Test Schemas

```python
class Split(BaseModel):
    amount: str
    value_in_currency: str
    currency: str
    symbol: str
    auto_label: str   # account label (e.g., "Asset:ETH", "Expense:Gas")

class SerializableJournalEntry(BaseModel):
    timestamp: int
    description: str
    splits: list[Split]

class TransactionData(BaseModel):
    timestamp: int
    block_num: int
    wallet_data: WalletData
    tx_data: dict[str, Any]
```

---

## Domain Rules -- Business/Accounting Rules

### 1. Transfer Filtering -- "Related" Transfers

A transfer is "related" if **at least one** of `from_addr` or `to_addr` belongs
to a tracked wallet. Transfers between two unrelated addresses are ignored.
Zero-value transfers are always filtered out.

### 2. Transfer Upcasting

Raw `Transfer` (integer wei values) must be "upcasted" to `TokenTransfer`
(decimal amounts with token metadata) before journal entry creation. The token
lookup requires `(chain, token_address)` and optionally `block_number` for
vault tokens whose conversion rate changes over time.

### 3. Gas Fee Handling

Gas fees are separated from protocol fees:
- Blockchain gas fee = `gasUsed * effectiveGasPrice + l1Fee`
- Protocol fees (LP fees, bridge fees) use same account labels but different amounts
- When filtering gas from journal splits, match on expected gas fee amount to avoid
  accidentally filtering protocol fees

### 4. Net-Zero Transfer Detection

If all transfers of a token sum to zero for a given address, the token transfers
are "net-zero" and can be eliminated (internal routing, flash loans, etc.). This
is done per-address, per-token.

### 5. Swap Detection Pattern

A swap is detected when the wallet has:
- Exactly one outflow (token A leaves the wallet)
- Exactly one inflow (token B enters the wallet)
- These may be across different addresses (DEX router)

The `find_swap_flows()` function searches for this pattern and creates balanced
journal splits.

### 6. Same-Symbol Fee Detection

When all journal splits in a transaction involve the same token, and the net
amount is non-zero, the difference is treated as a fee. This handles cases like
"send 1 ETH, receive 0.999 ETH back, 0.001 ETH is protocol fee."

### 7. Timestamp Normalization

The legacy codebase normalizes timestamps consistently:
- Pure dates (YYYY-MM-DD) map to 23:59:59 UTC (end of day)
- Datetime without timezone assumed UTC
- All stored as Unix seconds (int)
- Conversion: `date -> pd.Timestamp(date, tz="UTC").replace(23:59:59).timestamp()`

### 8. Event Matching Rules

Events are matched by:
- `event_name` (required) -- exact string match
- `address` (optional) -- case-insensitive address comparison
- `args` (optional) -- dictionary of argument key-value pairs, all must match

### 9. Token Type Resolution

ERC20 vs ERC721 Transfer events share the same topic hash (`0xddf252ad...`).
Differentiation:
- ERC20: `len(topics) == 3` and `len(data) == 32` (value in data)
- ERC721: `len(topics) == 4` and `len(data) == 0` (tokenId in third topic)

### 10. Vault Token Resolution

Vault tokens (aUSDC, yvDAI, etc.) need special handling:
- `conversion_func_name` -- smart contract function to call (e.g., "convertToAssets")
- `vault_token_decimals` -- decimals of the vault token itself
- Resolution requires `block_number` because the conversion rate changes over time
- The `min_timestamp` field prevents lookups before the vault was deployed

---

## What to Port

### Port directly (rewrite in clean Python)

- [x] **Transfer type hierarchy** -- Rewrite as Pydantic models. Use `RawTransfer`
      and `ResolvedTransfer` instead of the confusing named tuple hierarchy.
- [x] **TransactionContext peek/pop/yield pattern** -- Core parsing abstraction.
      Clean up: single API surface, no deprecated wrappers, no duplicate methods.
- [x] **Gas fee calculation** -- `calculate_gas_fee_wei()` is a pure function.
      Port directly including L2 fee handling.
- [x] **Fast log decoding** -- Hardcoded topic hashes for Transfer, ERC1155, NFT.
      Port the topic constants and the decoding logic.
- [x] **Net transfer calculation** -- `net_transfers_by_addr()` is essential for
      generic swap detection and spam filtering.
- [x] **Event matching** -- `_event_matches()` logic (name + address + args matching).
- [x] **ChainInfo data model** -- The fields are exactly what we need.
- [x] **Timestamp utilities** -- `chunkit()`, `date_to_timestamp()`,
      `timestamp_to_int()`, `str_to_timestamp_seconds()`.
- [x] **Swap flow detection** -- `find_swap_flows()` pattern.
- [x] **Test assertion utilities** -- `assert_journal_structure()` comparing splits
      by amount/symbol/account without checking prices. Critical for parser tests.
- [x] **Test data loading** -- `load_params_standalone()` for per-file test cases.
- [x] **VCR test recording** -- Port the VCR handler pattern for deterministic
      blockchain API tests. Filter API keys, normalize URIs.
- [x] **Override system** -- `OverrideConfig`, `ParserOverride`, `TokenOverride`.
      Essential for development/debugging workflow.

### Port the concept (redesign implementation)

- [x] **Error resolution tracking** -- Move into database models and API endpoints
      instead of CSV files. Concept of pending/fixed/skipped is good.
- [x] **Error reporting** -- Move from Excel sheets to dashboard pages. The
      categorization (UnknownContract, UnknownToken, UnhandledFunction) is good.
- [x] **EventDecoder / call tree** -- Parser debug page needs this. Redesign
      as an API endpoint that returns JSON instead of printing to console.
- [x] **Multicall hash** -- Good for grouping similar transactions. Port the
      concept of hashing the parser:function call sequence.
- [x] **Token validation workflow** -- `check_valid_token()` and
      `register_new_token_asset()` pattern. Port as API endpoints.

### Do NOT port

- [ ] **Registry singleton pattern** -- Use dependency-injector instead.
- [ ] **TransferManager / EventManager** -- Deprecated wrappers around
      TransactionContext. Already marked TODO:Deprecated in legacy code.
- [ ] **CombinedList** -- Clever but unnecessary complexity. Use simple list
      concatenation.
- [ ] **Settings with Hatchet/GCS/ReferenceAPI config** -- Our config is simpler.
- [ ] **ErrorReport Excel writer** -- We use a web dashboard, not Excel reports
      for errors.
- [ ] **Spam detection** -- Incomplete in legacy. Design from scratch if needed.
- [ ] **BlockchainAddress union type** -- Over-engineered. Start with EVM only
      (Web3Address = str), add others when needed.

---

## Clean Examples

### Example 1: Gas Fee Calculation (port directly)

```python
from decimal import Decimal
from enum import Enum

class Chain(str, Enum):
    ETHEREUM = "ETHEREUM"
    OPTIMISM = "OPTIMISM"
    ARBITRUM = "ARBITRUM"
    BASE = "BASE"
    # ...

def calculate_gas_fee_wei(tx_data: dict, chain: Chain | None = None) -> int:
    """Calculate gas fee in wei from transaction receipt data.

    Formula: gasUsed * effectiveGasPrice + l1Fee (for L2 chains)
    """
    receipt = tx_data.get("receipt", {})
    gas_used = receipt.get("gasUsed")
    if gas_used is None:
        return 0

    # Optimism uses gasPrice as fallback when effectiveGasPrice is missing
    if chain == Chain.OPTIMISM:
        gas_price = receipt.get("effectiveGasPrice", tx_data.get("gasPrice", 0))
    else:
        gas_price = receipt.get("effectiveGasPrice", 0)

    if gas_price is None:
        return 0

    gas_fee = gas_price * gas_used

    # L2 chains include an L1 data posting fee
    if "l1Fee" in receipt:
        l1_fee = receipt["l1Fee"]
        if isinstance(l1_fee, str):
            l1_fee = int(l1_fee, 16)
        gas_fee += l1_fee

    return gas_fee


def calculate_gas_fee_decimal(tx_data: dict, chain: Chain, native_decimals: int = 18) -> Decimal:
    """Calculate gas fee as Decimal in native token units."""
    gas_wei = calculate_gas_fee_wei(tx_data, chain)
    return Decimal(gas_wei) / Decimal(10 ** native_decimals)
```

### Example 2: TransactionContext Pattern (clean rewrite)

```python
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Iterator

from pydantic import BaseModel


class RawTransfer(BaseModel):
    chain: str
    token_address: str | None  # None for native
    from_address: str
    to_address: str
    value: int
    block_number: int | None = None
    transfer_type: str = "erc20"  # native, internal, erc20, nft, erc1155


class TransactionContext:
    """Mutable working set of transfers and events from a single transaction."""

    def __init__(
        self,
        transfers: list[RawTransfer],
        events: list[dict],
        wallet_addresses: set[str],
    ):
        self._transfers = list(transfers)
        self._events = list(events)
        self._wallet_addresses = {a.lower() for a in wallet_addresses}

    def pop_transfer(
        self,
        *,
        from_address: str | None = None,
        to_address: str | None = None,
        token_address: str | None = None,
        transfer_type: str | None = None,
        raise_if_none: bool = True,
    ) -> RawTransfer | None:
        """Find and remove the first matching transfer."""
        for i, tf in enumerate(self._transfers):
            if self._transfer_matches(tf, from_address, to_address, token_address, transfer_type):
                return self._transfers.pop(i)
        if raise_if_none:
            raise ValueError(f"No transfer found matching criteria")
        return None

    def pop_event(
        self,
        *,
        event_name: str,
        address: str | None = None,
        args: dict | None = None,
        raise_if_none: bool = True,
    ) -> dict | None:
        """Find and remove the first matching event."""
        for i, event in enumerate(self._events):
            if self._event_matches(event, event_name, address, args):
                return self._events.pop(i)
        if raise_if_none:
            raise ValueError(f"No event '{event_name}' found")
        return None

    def remaining_transfers(self) -> list[RawTransfer]:
        """Transfers not consumed by any parser (unknown/unhandled)."""
        return list(self._transfers)

    def is_related(self, address: str) -> bool:
        """Check if address belongs to a tracked wallet."""
        return address.lower() in self._wallet_addresses

    @staticmethod
    def _transfer_matches(tf, from_addr, to_addr, token_addr, tf_type) -> bool:
        if from_addr and tf.from_address.lower() != from_addr.lower():
            return False
        if to_addr and tf.to_address.lower() != to_addr.lower():
            return False
        if token_addr and (tf.token_address or "").lower() != token_addr.lower():
            return False
        if tf_type and tf.transfer_type != tf_type:
            return False
        return True

    @staticmethod
    def _event_matches(event, event_name, address, args) -> bool:
        if event.get("event") != event_name:
            return False
        if address and event.get("address", "").lower() != address.lower():
            return False
        if args:
            event_args = event.get("args", {})
            for key, value in args.items():
                if key not in event_args or event_args[key] != value:
                    return False
        return True
```

### Example 3: Net Transfer Aggregation (port directly)

```python
from collections import defaultdict
from decimal import Decimal


def net_transfers_by_address(
    transfers: list[RawTransfer],
    token_resolver,  # callable: (chain, token_addr, block_num) -> (symbol, decimals)
) -> dict[str, dict[str, Decimal]]:
    """Aggregate transfers into net position changes per address per token.

    Returns:
        {address: {token_symbol: net_decimal_amount}}
        Zero-value entries are filtered out.
    """
    result: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for tf in transfers:
        symbol, decimals = token_resolver(tf.chain, tf.token_address, tf.block_number)
        amount = Decimal(tf.value) / Decimal(10 ** decimals)

        result[tf.from_address][symbol] -= amount
        result[tf.to_address][symbol] += amount

    # Filter zero values
    return {
        addr: {sym: amt for sym, amt in tokens.items() if amt != 0}
        for addr, tokens in result.items()
        if any(amt != 0 for amt in tokens.values())
    }
```

### Example 4: Timestamp Utilities (port directly)

```python
from datetime import date, datetime, timezone


def date_to_end_of_day_timestamp(d: date) -> int:
    """Convert date to Unix timestamp at 23:59:59 UTC."""
    dt = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    return int(dt.timestamp())


def str_to_timestamp(raw: str) -> int:
    """Normalize string timestamp input to Unix seconds.

    Rules:
    - Pure dates (YYYY-MM-DD) -> end of day UTC
    - Datetime without tz -> assumed UTC
    - Numeric strings -> Unix seconds
    """
    value = raw.strip()

    # Numeric shortcut
    try:
        return int(float(value))
    except ValueError:
        pass

    # Pure date
    if "T" not in value and ":" not in value and " " not in value:
        d = date.fromisoformat(value)
        return date_to_end_of_day_timestamp(d)

    # Datetime
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def chunked(lst: list, size: int):
    """Yield successive chunks of given size from list."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
```

### Example 5: ERC20 Transfer Topic Constants

```python
from hexbytes import HexBytes

# ERC20 Transfer(address indexed from, address indexed to, uint256 value)
# Also matches ERC721 Transfer but differentiated by topic count
TRANSFER_TOPIC = HexBytes("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")

# ERC1155 TransferSingle(address operator, address from, address to, uint256 id, uint256 value)
ERC1155_TRANSFER_SINGLE_TOPIC = HexBytes("0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62")

# ERC1155 TransferBatch(address operator, address from, address to, uint256[] ids, uint256[] values)
ERC1155_TRANSFER_BATCH_TOPIC = HexBytes("0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb")


def is_erc20_transfer(log: dict) -> bool:
    """Check if log is an ERC20 Transfer event (not ERC721)."""
    topics = log.get("topics", [])
    return (
        len(topics) == 3
        and HexBytes(topics[0]) == TRANSFER_TOPIC
        and len(HexBytes(log.get("data", "0x"))) == 32
    )


def is_erc721_transfer(log: dict) -> bool:
    """Check if log is an ERC721 Transfer event (not ERC20)."""
    topics = log.get("topics", [])
    return (
        len(topics) == 4
        and HexBytes(topics[0]) == TRANSFER_TOPIC
    )
```

### Example 6: Test Case Assertion (port directly)

```python
from pydantic import BaseModel


class ExpectedSplit(BaseModel):
    amount: str
    symbol: str
    account_label: str


class ExpectedJournalEntry(BaseModel):
    timestamp: int
    description: str
    splits: list[ExpectedSplit]


def assert_journal_matches(actual_entry, expected: ExpectedJournalEntry):
    """Assert journal entry structure matches expected output.

    Compares amounts, symbols, and account labels.
    Intentionally does NOT compare prices (test separately).
    """
    assert actual_entry.timestamp == expected.timestamp, (
        f"timestamp: {actual_entry.timestamp} != {expected.timestamp}"
    )
    assert actual_entry.description == expected.description, (
        f"description: {actual_entry.description!r} != {expected.description!r}"
    )
    assert len(actual_entry.splits) == len(expected.splits), (
        f"split count: {len(actual_entry.splits)} != {len(expected.splits)}"
    )

    for i, (actual, exp) in enumerate(zip(actual_entry.splits, expected.splits)):
        assert str(actual.amount) == exp.amount, f"split[{i}] amount: {actual.amount} != {exp.amount}"
        assert actual.symbol == exp.symbol, f"split[{i}] symbol: {actual.symbol} != {exp.symbol}"
        assert actual.account_label == exp.account_label, (
            f"split[{i}] label: {actual.account_label} != {exp.account_label}"
        )
```

---

## Source File Index

| File | LOC | What it provides |
|------|-----|-----------------|
| `v2/parser/evm/generic_utils.py` | ~1930 | Transfer types, TransactionContext, GenericMethod, TransferManager, EventManager, CombinedList |
| `v2/util.py` | ~121 | Timestamp conversion, chunking |
| `v2/types.py` | ~18 | BlockchainAddress union type |
| `v2/settings.py` | ~166 | Pydantic settings, config file paths, DB URL |
| `v2/registry.py` | ~38 | Singleton factory with lru_cache |
| `v2/chain_info_provider.py` | ~60 | ChainInfo NamedTuple, ChainInfoProvider |
| `analysis/detection.py` | ~151 | Vault info extraction, balance reconciliation, safe detection |
| `analysis/parse_utils.py` | ~918 | parse_single_tx, parse_multiple_tx, format_journal_entry, token validation/registration |
| `analysis/decode_events.py` | ~503 | EventDecoder, call tree decoding, multicall hash |
| `analysis/error_report.py` | ~211 | Error report Excel writer, ErrorReport class |
| `analysis/error_resolution_tracker.py` | ~264 | ErrorResolutionTracker with pending/fixed/skipped states |
| `analysis/testing.py` | ~465 | TestCaseCollectorService, wallet extraction, protocol detection |
| `analysis/override_utils.py` | ~496 | ParserOverride, TokenOverride, OverrideConfig, apply/merge logic |
| `analysis/spam.py` | ~61 | Spam detection (incomplete) |
| `common/test_utils.py` | ~185 | Journal assertion helpers, test data loading, serialization |
| `common/test_schemas.py` | ~201 | Pydantic schemas for test data (Split, SerializableJournalEntry, TransactionData, CEX schemas) |
| `common/vcr_handler.py` | ~96 | VCR HTTP recording for tests |
| `common/requests_count.py` | ~21 | HTTP request counter context manager |
