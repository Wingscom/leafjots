# Infrastructure -- Distilled Reference

> Distilled from Pennyworks/ChainCPA v2 legacy code.
> Source files: `legacy_code/v2/http/`, `legacy_code/v2/web3/`, `legacy_code/v2/price_feed/`,
> `legacy_code/v2/tx_loader.py`, `legacy_code/v2/event_loader.py`, `legacy_code/v2/block_finder.py`

---

## Patterns -- Design Patterns, Why Good

### 1. Layered HTTP Client Hierarchy

The legacy code uses a layered client hierarchy where each blockchain explorer API
inherits from a common base `Client` class (from `pylib.http.client`):

```
Client (pylib base)
  |-- EtherscanClient      (Etherscan-compatible APIs)
  |     |-- RoutescanClient (Routescan overrides URL + rate limiting)
  |-- BlockscoutClient      (Blockscout REST API v2)
  |-- ZhartaClient          (Protocol-specific API)
  |-- ReferenceAPI          (Internal metadata service)
```

**Why good:** Each client only overrides what differs (URL, rate limits, response
parsing), keeping common HTTP/retry/pagination logic in one place. Polymorphism
allows `TxLoader` to swap providers transparently.

### 2. Rate Limiting via Transport Layer

Rate limiting is injected at the transport layer, not in business logic:

```python
# Per-second rate limit (Etherscan: 5/sec)
transport = RateLimitedTransport(max_rate=5, time_period=1, retries=5)

# Per-minute rate limit (Blockscout: 600/min)
transport = RateLimitedTransport(max_rate=600, time_period=60, retries=5)

# Legacy: simple delay between requests
adapter = ThrottledHTTPAdapter(delay_ms=200)
session.mount("http://", adapter)
```

**Why good:** Decouples rate limiting from API logic. Each client declares its
limits at construction time and never worries about timing again.

### 3. Recursive Block-Range Splitting for Etherscan 10K Limit

Etherscan returns max 10,000 results per query. The legacy code handles this by
recursively splitting the block range with adaptive bias:

```python
def _get_account_transactions(self, address, from_block, to_block, action, split_bias=0.5):
    results = fetch_range(from_block, to_block)
    if len(results) >= 10000:
        mid = start + int((end - start) * bias)
        yield from fetch_range(start, mid)      # lower half
        yield from fetch_range(mid + 1, end)     # upper half
```

**Why good:** Automatically adapts to address activity density. A whale address
with 100K TXs in 1000 blocks gets recursively narrowed down until each sub-range
has < 10K results. The split_bias parameter allows tuning for skewed distributions.

### 4. Scan Provider Abstraction

`TxLoader` selects the appropriate scan API per chain via a provider mapping:

```python
CHAIN_TO_SCAN_PROVIDER = {
    Chain.ETHEREUM: ScanProvider.ETHERSCAN,
    Chain.ARBITRUM: ScanProvider.ETHERSCAN,
    Chain.SOME_L2:  ScanProvider.BLOCKSCOUT,
    Chain.SOME_ALT: ScanProvider.ROUTESCAN,
}

match provider:
    case ScanProvider.BLOCKSCOUT:  client = blockscout_client
    case ScanProvider.ROUTESCAN:   client = routescan_client
    case _:                        client = etherscan_client
```

**Why good:** Adding a new chain only requires a mapping entry. The loading
logic stays chain-agnostic.

### 5. Composable Pricer System (Price Feed)

The price feed uses a composable DAG of pricers where each pricer declares
dependencies on other pricers:

```
ExternalSourcePricer("COINGECKO", "ethereum")     -- fetches from CoinGecko
StablePricer({"USD": Decimal("1.00")})             -- returns constant $1
RelativePricer(relation_pricer, underlying_pricer) -- A_price = ratio * B_price
CurveTokenPricer(chain, pool_address)              -- reads getVirtualPrice()
ChainPricer(chain, address)                        -- on-chain contract reads
```

All pricers implement `get_price(at_ts, in_currency) -> Decimal`.
A `PricerRegistry` manages lookup by ticker or ID.
A `ComposablePriceFeed` is the top-level coordinator.

**Why good:** Arbitrary pricing strategies compose without God classes.
Adding a new DeFi protocol price only requires a new Pricer subclass.

### 6. Block Finder -- Timestamp-to-Block Binary Search

Each chain has a `BlockFinder` that converts timestamps to block numbers
using binary search with avg_block_time as initial estimate:

```python
class BlockFinder(ABC):
    def get_block_number_by_time(self, ts) -> int:
        # Binary search: narrow [lower_bound, upper_bound] until block found
        while lower_bound + 1 < upper_bound:
            mid = (lower_bound + upper_bound) // 2
            mid_ts = self.get_block_timestamp(mid)
            if mid_ts < ts: lower_bound = mid
            else:           upper_bound = mid
        return lower_bound
```

**Why good:** Works for any chain. `@lru_cache` on `get_block_timestamp`
avoids redundant RPC calls. Each chain only implements `get_block_number()`
and `get_block_timestamp()`.

### 7. Cursor-Based Pagination (Blockscout)

Blockscout uses cursor-based pagination via `next_page_params`:

```python
class BlockscoutIterator(DataIterator):
    def fetch_page(self):
        params = {"items_count": self.items_count}
        if self.root_page_params:
            params.update(self.root_page_params)
        response_data = self.client.request("GET", self.url, params=params).json()
        next_page_params = response_data.get("next_page_params")
        if not next_page_params:
            self._has_more = False
        else:
            self.root_page_params = next_page_params
```

**Why good:** Handles any Blockscout cursor scheme (block_number + index + items_count)
without knowing the cursor internals.

### 8. Response Normalization

BlockscoutClient normalizes API responses to match Etherscan's format:

```python
def normalize(x):
    out["to"] = x.get("to", {}).get("hash", None)    # Blockscout nests addresses
    out["from"] = x.get("from", {}).get("hash", None)
    out["blockNumber"] = x.get("block_number")         # Different field name
    out["timeStamp"] = x.get("timestamp")
```

**Why good:** Downstream code only deals with one format regardless of data source.

### 9. Event-Driven Transaction Discovery (ParsedEventFinder)

`ParsedEventFinder` uses Etherscan log APIs to find events matching a topic hash,
then decodes them using a `ParsedContract`:

```python
class ParsedEventFinder:
    @classmethod
    def by_topic_name(cls, contract, topic_name, chain, address=None):
        topic_hex = contract.name_to_hex(topic_name)
        log_receipts = etherscan.get_contract_logs(address, topic0=topic_hex)
        return contract.parse_scan_logs(log_receipts, event_subset={topic_name})
```

Supports: single-topic, multi-topic with operators, cross-contract search,
indexed argument filters converted from web3 format to Etherscan format.

**Why good:** Finds protocol-specific TXs (e.g., Aave BidLocked events) without
loading all transactions. Much more efficient than full-scan approaches.

### 10. Idempotent TX Loading with Deduplication

`TxLoader` queries existing TX hashes before loading new ones:

```python
existing_tx_hashes = set(session.scalars(
    select(Transaction.hash).where(Transaction.wallet_id == wallet.id)
))
# ... fetch from API ...
if tx_hash not in existing_tx_hashes:
    new_txs.append(tx)
```

**Why good:** Safe to re-run. Resumable via `wallet.last_block_loaded`.
Block range overlap (re-fetch from last_block, not last_block+1) ensures
no TX is missed at block boundaries.

---

## Key Interfaces -- Abstract Classes, Signatures

### HTTP Clients

```python
class Client:
    """Base HTTP client (from pylib). Handles transport, timeout, retries."""
    def __init__(self, url, transport=None, timeout=60, raise_for_status=True)
    def request(method, url, params=None) -> Response
    def get(url, params=None) -> Response

class EtherscanClient(Client):
    PAGE_SIZE = 10000
    def __init__(self, chain=None, url=None, transport=None)
    def send_request(method, url, chain=None, params=None) -> Any  # returns result field
    def get_transactions_by_address(address, from_block=0, to_block=99999999) -> Iterator[Dict]
    def get_erc20_transactions_by_address(address, ...) -> Iterator[Dict]
    def get_erc1155_transactions_by_address(address, ...) -> Iterator[Dict]
    def get_internal_transactions_by_address(address, ...) -> Iterator[Dict]
    def get_internal_transactions_by_tx_hash(tx_hash) -> List[Dict]
    def get_contract_logs(address, topic0, from_block, to_block) -> List[Dict]
    def get_contract_abi(address) -> List[Dict]
    def get_contract_source(address) -> Dict
    def get_address_metadata(addresses) -> List[Dict]  # up to 100

class BlockscoutClient(Client):
    def __init__(self, chain=None, max_rate_per_min=600)
    def normalize(x) -> Dict  # normalize to Etherscan format
    def get_transactions_by_address(address) -> Iterator[Dict]
    def get_erc20_transactions(address) -> Iterator[Dict]
    def get_internal_transactions(address) -> Iterator[Dict]

class RoutescanClient(EtherscanClient):
    """Etherscan-compatible client with chain-specific URL formatting."""
    def __init__(self, chain=None)
    def _send_request(method, url, chain=None, params=None)  # overrides URL per chain
```

### Rate Limiting

```python
class RateLimitedTransport:
    """Token-bucket rate limiter at transport level (from pylib)."""
    def __init__(self, max_rate, time_period, retries)

class ThrottledHTTPAdapter(HTTPAdapter):
    """Simple delay-between-requests limiter."""
    def __init__(self, delay_ms=200)
```

### TX Loading

```python
class TxLoader:
    MIN_BLOCK_CONFIRMATIONS = 50

    def __init__(self, session: Session)
    def load_new_transactions(wallet, batch_size=None, to_ts=None)
    def load_txs_from_scan_provider(wallet, api_kwargs) -> List[Dict]
    def get_raw_tx(chain, tx_hash) -> Transaction

    # Chain-specific loaders (all follow same pattern):
    def _load_evm_txs(wallet, last_block, batch_size, to_ts)
    def _load_bitcoin_txs(wallet, last_block, to_ts)
    def _load_solana_txs(wallet, last_block, batch_size, to_ts)
    def _load_sui_txs(wallet, last_block, batch_size, to_ts)
    def _load_cardano_txs(wallet, last_block, batch_size)
    def _load_stacks_txs(wallet, last_block, batch_size, to_ts)
    def _load_algorand_txs(wallet, last_block, to_ts)

    # Exchange loaders:
    def _load_coinbase_txs(wallet, last_cursor, to_ts)
    def _load_hyperliquid_txs(wallet, last_cursor, to_ts)
```

### Block Finder

```python
class BlockFinder(ABC):
    def __init__(self, avg_block_time: float)
    def get_block_number(self) -> int            # latest block
    def get_block_timestamp(self, block: int) -> int  # block -> unix timestamp
    def get_block_number_by_time(self, ts: int) -> int  # timestamp -> block (binary search)

# Chain-specific implementations:
class EthBlockFinder(BlockFinder)    # uses Web3Provider.get_web3(chain)
class SuiBlockFinder(BlockFinder)    # uses SuiProvider RPC
class SolanaBlockFinder(BlockFinder) # uses SolanaProvider
class BitcoinBlockFinder(BlockFinder)
class CardanoBlockFinder(BlockFinder)
class StacksBlockFinder(BlockFinder)
class AlgorandBlockFinder(BlockFinder)

def get_block_finder(chain: Chain) -> BlockFinder  # factory with @lru_cache
```

### Event Loading

```python
class EventLoader:
    def __init__(self, session: Session)
    def load_new_events(entity)           # loads events for all wallets in entity
    def _load_events(status)              # dispatches to protocol-specific loader
    def _load_hashnote_vault_events(...)  # uses web3 contract.events.EventName().get_logs()
    def _load_hedron_events(...)          # uses web3 with argument_filters

class ParsedEventFinder:
    @classmethod
    def by_topic_name(ct, topic_name, chain, address=None) -> List[Dict]
    def by_topic(ct, topic_hex, chain, address=None) -> List[Dict]
    def by_all_topic(ct, chain, address=None) -> Dict[str, List[Dict]]
    def by_addr_list_topic(ct, chain, topic_name, addr_list) -> Dict[str, List[Dict]]
    def by_topic_cross_contract(ct, topic_hex, chain) -> List[Dict]  # no address filter
```

### Price Feed

```python
class AbstractPriceFeed(ABC):
    def get_price(self, at_ts: int, in_currency: Currency) -> Decimal

class Pricer(AbstractPriceFeed):
    """Composable pricer base class."""
    def __init__(self, ticker: str = None)
    def get_price(self, at_ts: int, in_currency: Currency) -> Decimal
    def get_config(self, as_reference=False) -> Dict | str
    def get_dependencies(self) -> List[Pricer]
    def set_price_feed(self, price_feed)
    @classmethod
    def from_config(cls, config: Dict, registry=None) -> Pricer

class PricerRegistry:
    def register_pricer(self, pricer: Pricer) -> str
    def get_by_ticker(self, ticker: str) -> Pricer
    def get_by_pricer_id(self, id: str) -> Pricer
    def create_pricer_from_config(cls, config: Dict) -> Pricer
    def load_config(self, config: Dict) -> Dict[str, Pricer]
    def extract_pricer_references(self, config: Dict) -> Set[str]
    def export_dag(self, filename: str)  # GraphViz DOT

class ComposablePriceFeed:
    """Top-level coordinator for pricers."""
    def __init__(self, all_configs=None)
    def register(self, pricer: Pricer) -> str
    def get_price(self, identifier: str, at_ts: int, in_currency=Currency.USD) -> Decimal
    def load_multi(self, configs: Dict) -> Dict[str, Pricer]

class PriceFeed(ComposablePriceFeed):
    """Main price feed with CoinGecko + CryptoCompare + config + cache."""
    def __init__(self, crypto_compare_api, coin_gecko_api, session, use_price_cache=True)
    def get(self, symbol, at_ts, in_currency, use_price_cache=None) -> Decimal
    def get_pricer(self, user_id: str) -> Pricer | None

# Concrete pricers:
class StablePricer(Pricer)          # constant value (e.g., USDC = $1.00)
class ExternalSourcePricer(Pricer)  # fetches from CoinGecko/CryptoCompare
class RelativePricer(Pricer)        # price_A = ratio * price_B
class CurveTokenPricer(ChainPricer) # reads getVirtualPrice() on-chain
class ChainPricer(Pricer)           # base for on-chain pricers
```

### Price APIs

```python
class CryptoCompareMinApi:
    def __init__(self, api_url, api_key, delay_ms=200)
    def get_hourly_price(self, symbol, currency, to_ts) -> Decimal
    def get_daily_prices(self, symbol, type, limit=100, to_ts=None)

class CoinGeckoApi:
    def __init__(self, api_url, api_key, delay_ms=200)
    def get_hourly_price(self, symbol, currency, to_ts) -> Decimal
    def get_hourly_price_by_id(self, id, currency, to_ts) -> Decimal
```

---

## Domain Rules -- Business/Accounting Rules in Infrastructure

### 1. Block Confirmations

Each chain type has a minimum confirmation depth before transactions are considered final:

```python
MIN_BLOCK_CONFIRMATIONS = 50   # EVM chains
MIN_BTC_BLOCK_CONFS = 4        # Bitcoin
MIN_SOL_BLOCK_CONFS = 50       # Solana
```

**Rule:** Never load transactions from blocks that are too close to the chain tip.
`to_block = latest_block - MIN_CONFIRMATIONS` ensures only finalized data enters the system.

### 2. Price Truncation to Hourly

All price lookups truncate the timestamp to the nearest hour:

```python
ts_hour = (at_ts // 3600) * 3600
```

**Rule:** Price feed queries use hourly granularity. This reduces API calls and
ensures consistent pricing across transactions in the same hour.

### 3. Price Caching in Database

Prices are cached in the database as `AssetPrice(symbol, timestamp, currency, price)`.
On subsequent lookups, the cache is checked first. This is critical for:
- Reproducibility: same price for same timestamp across re-runs
- Performance: avoid redundant API calls for the same token/hour

### 4. Vault Token Pricing

Vault tokens (e.g., Aave aTokens, ERC-4626 vaults) require special pricing:

```python
# CORRECT: get decimal amount (applies exchange rate), then multiply by UNDERLYING price
decimal_amount = token.get_decimal_amount(raw_balance, block)
price = price_feed.get(token.symbol, at_ts, in_currency)
total_value = decimal_amount * price

# WRONG: would double-count the exchange rate
vault_price = price_feed.get(vault_token.symbol, ...)
value = raw_balance * vault_price  # BUG: exchange rate applied twice
```

**Rule:** `get_token_total_value()` handles this correctly. Always use it for
vault tokens instead of manual price * balance.

### 5. Internal TX Normalization

Internal transactions from different APIs have different field formats.
All are normalized to Etherscan format before storage:

```python
def _normalize_internal_tx(x):
    out["blockNumber"] = int(x["blockNumber"])
    out["from"] = web3.to_checksum_address(x["from"])
    out["to"] = web3.to_checksum_address(x["to"])
    out["value"] = int(x["value"])
```

**Rule:** Transaction data stored in DB always uses Etherscan-compatible field names
with checksummed addresses and integer values.

### 6. NFT Symbol Pattern Matching for Pricing

NFT position tokens (Uniswap V3 LP positions, etc.) are priced using regex-matched
handlers. Each DeFi protocol registers a regex pattern that matches its NFT symbols:

```python
_token_handlers = [
    (SHADOW_REGEX, ShadowPositionPriceFeed),
    (UNISWAP_V3_REGEX, UniswapV3PositionPriceFeed),
    (PENDLE_REGEX, PendleMasterPricer),
    ...
]
```

**Rule:** When pricing a symbol, iterate through handlers until a regex matches.
This allows protocol-specific pricing logic without modifying the core price feed.

---

## What to Port

### [x] Port -- Rate-Limited HTTP Client Pattern

Port the pattern of injecting rate limiting at the transport/adapter level.
Use `httpx` with custom transport or `tenacity` for retries.

**New design:**
```python
class RateLimitedClient:
    def __init__(self, base_url: str, max_rate: float, time_period: float):
        self._client = httpx.AsyncClient(base_url=base_url)
        self._limiter = AsyncLimiter(max_rate, time_period)

    async def get(self, path, params=None):
        async with self._limiter:
            return await self._client.get(path, params=params)
```

### [x] Port -- Etherscan Client with 10K Splitting

Port the recursive block-range splitting for the Etherscan 10K limit.
This is essential for loading complete transaction histories.

### [x] Port -- Blockscout Client with Cursor Pagination

Port the `BlockscoutIterator` pattern for cursor-based pagination.
Generalize it for any cursor-based API.

### [x] Port -- Response Normalization

Port the pattern of normalizing different API responses to a single format.
Essential for the `TxLoader` to be provider-agnostic.

### [x] Port -- BlockFinder with Binary Search

Port the abstract `BlockFinder` with binary search + `@lru_cache`.
For CryptoTax VN, initially only EVM chains are needed.

### [x] Port -- Scan Provider Abstraction (Chain -> API mapping)

Port the `CHAIN_TO_SCAN_PROVIDER` mapping so new chains only need a config entry.

### [x] Port -- TxLoader Idempotent Loading Pattern

Port the pattern of:
1. Query existing TX hashes
2. Fetch from API with block range
3. Deduplicate
4. Batch insert
5. Update `last_block_loaded`

### [x] Port -- Composable Pricer Architecture

Port the core pattern:
- `AbstractPriceFeed` with `get_price(at_ts, in_currency) -> Decimal`
- `Pricer` base class with dependencies, ticker, and config serialization
- `PricerRegistry` for lookup by ticker
- `ComposablePriceFeed` as coordinator
- `StablePricer`, `ExternalSourcePricer` as concrete implementations

### [x] Port -- Price Caching in Database

Port `AssetPrice` caching: key = (symbol, hour_timestamp, currency), value = Decimal price.

### [x] Port -- CoinGecko and CryptoCompare API Clients

Port the hourly price fetch APIs. Use `httpx` async instead of `requests`.

### [x] Port -- ParsedEventFinder Pattern

Port the event-finding pattern using Etherscan log APIs.
Critical for discovering protocol-specific transactions efficiently.

### [ ] Rewrite -- ReferenceAPI

Do NOT port. This is a Pennyworks-internal metadata service. CryptoTax VN will
store token/contract/parser metadata locally in PostgreSQL. The concept of a
central reference API is Pennyworks-specific infrastructure.

### [ ] Rewrite -- WebApi / GraphQL Client

Do NOT port. The `WebApi` class is heavily broken (`[UNCLEAR]` throughout),
uses `requests` instead of `httpx`, and the GraphQL client is tied to
Pennyworks-specific subgraph queries.

### [ ] Rewrite -- Protocol-Specific Helpers (Hedron, Superform)

Do NOT port directly. These are Pennyworks-specific protocol integrations.
CryptoTax VN will focus on Aave/Uniswap/Curve. If needed, similar helpers
can be written from scratch using the same patterns.

### [ ] Rewrite -- EventLoader Class

Do NOT port the EventLoader class directly. It is tightly coupled to Pennyworks
DB models and protocols (Hashnote, Hedron). The pattern of using `web3 contract.events`
to get logs is good, but the orchestration should be rewritten.

### [ ] Rewrite -- Multi-Chain TxLoader Dispatch

The `_load_on_chain_txs` method has 8+ chain-specific branches with heavy duplication.
Rewrite with a strategy pattern:

```python
class ChainTxLoader(ABC):
    @abstractmethod
    async def load(self, wallet, from_block, to_block) -> List[Transaction]: ...

class EVMTxLoader(ChainTxLoader): ...
class SolanaTxLoader(ChainTxLoader): ...

LOADERS: Dict[Chain, ChainTxLoader] = {
    Chain.ETHEREUM: EVMTxLoader(),
    Chain.SOLANA: SolanaTxLoader(),
}
```

### [ ] Rewrite -- PriceFeed God Class

The legacy `PriceFeed` class (~300 lines) combines:
- Composable pricer registration
- CoinGecko/CryptoCompare fallback
- NFT token handler dispatch
- DB price caching
- Config file loading
- Reference API lazy loading

Rewrite as separate concerns with dependency injection.

### [ ] Rewrite -- Global Singletons

Legacy uses `@lru_cache` on module-level factory functions as pseudo-singletons:
```python
@lru_cache
def get_block_finder(chain) -> BlockFinder: ...
@lru_cache
def get_crypto_compare_min_api() -> CryptoCompareMinApi: ...
```

Replace with `dependency-injector` containers for proper lifecycle management.

---

## Clean Examples

### Example 1: Rate-Limited Etherscan Client (Simplified)

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class EtherscanClient:
    """Etherscan API client with rate limiting and automatic pagination."""

    PAGE_SIZE = 10000

    def __init__(self, api_key: str, chain_id: int, base_url: str = "https://api.etherscan.io"):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            params={"apikey": api_key, "chainid": str(chain_id)},
            timeout=60.0,
        )

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, max=30))
    async def _request(self, params: dict) -> list:
        response = await self._client.get("/api", params=params)
        data = response.json()
        if data["status"] != "1":
            if data["message"] == "No transactions found":
                return []
            if "rate limit" in str(data.get("result", "")).lower():
                raise Exception("Rate limited")  # triggers retry
            raise Exception(f"Etherscan error: {data['message']}")
        return data["result"]

    async def get_transactions(
        self, address: str, from_block: int = 0, to_block: int = 99999999
    ) -> list[dict]:
        """Fetch all transactions, auto-splitting on 10K limit."""
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": from_block,
            "endblock": to_block,
            "sort": "asc",
        }
        results = await self._request(params)
        if len(results) >= self.PAGE_SIZE:
            mid = (from_block + to_block) // 2
            lower = await self.get_transactions(address, from_block, mid)
            upper = await self.get_transactions(address, mid + 1, to_block)
            return lower + upper
        return results
```

### Example 2: BlockFinder with Binary Search

```python
from abc import ABC, abstractmethod
from functools import lru_cache

class BlockFinder(ABC):
    def __init__(self, avg_block_time: float):
        self._avg_block_time = avg_block_time

    @abstractmethod
    def get_latest_block(self) -> int: ...

    @abstractmethod
    @lru_cache(maxsize=4096)
    def get_block_timestamp(self, block_number: int) -> int: ...

    def get_block_at_timestamp(self, target_ts: int) -> int:
        """Binary search for the block closest to target_ts."""
        lo, hi = 1, self.get_latest_block()

        while lo + 1 < hi:
            mid = (lo + hi) // 2
            mid_ts = self.get_block_timestamp(mid)
            if mid_ts <= target_ts:
                lo = mid
            else:
                hi = mid

        return lo


class EVMBlockFinder(BlockFinder):
    def __init__(self, web3_provider, avg_block_time: float = 12.0):
        super().__init__(avg_block_time)
        self._w3 = web3_provider

    def get_latest_block(self) -> int:
        return self._w3.eth.block_number

    @lru_cache(maxsize=4096)
    def get_block_timestamp(self, block_number: int) -> int:
        return self._w3.eth.get_block(block_number)["timestamp"]
```

### Example 3: Composable Pricer

```python
from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum

class Currency(Enum):
    USD = "USD"
    VND = "VND"

class Pricer(ABC):
    def __init__(self, ticker: str | None = None):
        self._ticker = ticker

    @property
    def ticker(self) -> str | None:
        return self._ticker

    @abstractmethod
    def get_price(self, at_ts: int, in_currency: Currency) -> Decimal: ...


class StablePricer(Pricer):
    """Returns a fixed price. Used for USDC, USDT, DAI."""
    def __init__(self, value: Decimal, ticker: str | None = None):
        super().__init__(ticker)
        self._value = value

    def get_price(self, at_ts: int, in_currency: Currency) -> Decimal:
        if in_currency != Currency.USD:
            raise ValueError(f"StablePricer only supports USD, got {in_currency}")
        return self._value


class ExternalPricer(Pricer):
    """Fetches price from CoinGecko or CryptoCompare."""
    def __init__(self, api, provider_id: str, ticker: str | None = None):
        super().__init__(ticker)
        self._api = api
        self._provider_id = provider_id

    def get_price(self, at_ts: int, in_currency: Currency) -> Decimal:
        ts_hour = (at_ts // 3600) * 3600  # truncate to hour
        return self._api.get_hourly_price_by_id(
            self._provider_id, in_currency.value.lower(), ts_hour
        )


class PricerRegistry:
    def __init__(self):
        self._by_ticker: dict[str, Pricer] = {}

    def register(self, pricer: Pricer) -> None:
        if pricer.ticker:
            self._by_ticker[pricer.ticker] = pricer

    def get(self, ticker: str) -> Pricer | None:
        return self._by_ticker.get(ticker)
```

### Example 4: Idempotent TX Loader Pattern

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class TxLoader:
    MIN_CONFIRMATIONS = 50

    def __init__(self, session: AsyncSession, scan_client):
        self._session = session
        self._client = scan_client

    async def load_wallet_txs(self, wallet) -> int:
        """Load new transactions for a wallet. Returns count of new TXs."""
        # 1. Get existing hashes for deduplication
        result = await self._session.scalars(
            select(Transaction.hash).where(Transaction.wallet_id == wallet.id)
        )
        existing_hashes = set(result.all())

        # 2. Determine block range
        from_block = wallet.last_block_loaded or 0
        to_block = await self._client.get_latest_block() - self.MIN_CONFIRMATIONS

        if to_block <= from_block:
            return 0

        # 3. Fetch from API
        raw_txs = await self._client.get_transactions(
            wallet.address, from_block=from_block, to_block=to_block
        )

        # 4. Filter and create
        new_txs = []
        for tx_data in raw_txs:
            if tx_data["hash"] not in existing_hashes:
                tx = Transaction(
                    wallet_id=wallet.id,
                    hash=tx_data["hash"],
                    block_num=int(tx_data["blockNumber"]),
                    timestamp=int(tx_data["timeStamp"]),
                    tx_data=tx_data,
                )
                new_txs.append(tx)

        # 5. Batch insert + update cursor
        if new_txs:
            self._session.add_all(new_txs)
            wallet.last_block_loaded = to_block
            await self._session.flush()

        return len(new_txs)
```

### Example 5: Scan Provider Factory

```python
from enum import Enum

class ScanProvider(Enum):
    ETHERSCAN = "etherscan"
    BLOCKSCOUT = "blockscout"
    ROUTESCAN = "routescan"

CHAIN_PROVIDERS = {
    "ethereum": ScanProvider.ETHERSCAN,
    "arbitrum": ScanProvider.ETHERSCAN,
    "base": ScanProvider.ETHERSCAN,
    "polygon": ScanProvider.ETHERSCAN,
    "gnosis": ScanProvider.BLOCKSCOUT,
}

def create_scan_client(chain: str, settings) -> ScanClient:
    provider = CHAIN_PROVIDERS.get(chain, ScanProvider.ETHERSCAN)
    match provider:
        case ScanProvider.ETHERSCAN:
            return EtherscanClient(
                api_key=settings.etherscan_api_key,
                chain_id=CHAIN_IDS[chain],
            )
        case ScanProvider.BLOCKSCOUT:
            return BlockscoutClient(
                base_url=BLOCKSCOUT_URLS[chain],
                max_rate_per_min=600,
            )
        case ScanProvider.ROUTESCAN:
            return RoutescanClient(chain_id=CHAIN_IDS[chain])
```

---

## Summary of Key Takeaways for CryptoTax VN

1. **Use async httpx** instead of sync requests. Rate limit at transport layer.

2. **Etherscan 10K splitting** is a must-port. Without it, active wallets will have
   incomplete transaction histories.

3. **BlockFinder** binary search with `lru_cache` is elegant and works for all chains.
   Start with `EVMBlockFinder` only.

4. **Composable pricers** are the right architecture. Start with `StablePricer` +
   `ExternalPricer` (CoinGecko). Add on-chain pricers later per protocol.

5. **Idempotent TX loading** with deduplication is critical. Always track
   `last_block_loaded` and query existing hashes before inserting.

6. **Normalize responses** to a common format at the client layer, not in business logic.

7. **Do NOT port** the ReferenceAPI, the EventLoader orchestrator, or the PriceFeed
   God class. Port the patterns, rewrite the implementation.

8. **Replace singletons** (`@lru_cache` factories) with `dependency-injector` containers.
