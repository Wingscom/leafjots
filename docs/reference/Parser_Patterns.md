# Parser Engine -- Distilled Reference

> Distilled from Pennyworks/ChainCPA legacy_code/v2/parser/ (~100+ files, ~15K LOC parser code).
> This document captures patterns, interfaces, domain rules, and porting recommendations.
> Source scan date: 2026-02-18.

---

## 1. Patterns -- Design Patterns, Why Good

### 1.1 Parser Class Hierarchy

The legacy system uses a deep inheritance hierarchy with multiple parser strategies:

```
RootParserAbstract                     # Abstract root, owns session + ParserMap
  EVMRootParser                        # EVM entry point, owns ContractMap + PriceFeed
    parse(TransactionBundle) -> JournalEntry

EVMParserAbstract                      # Abstract base for all EVM parsers
  EVMSimpleTransfer                    # Handles plain ETH transfers (no contract)
  EVMContractParser                    # Base for contract-specific parsers
    EventDrivenParser                  # Maps events -> handler methods
      ExtEventDrivenParser             # Enhanced: passes transfer lists to handlers
        ExtFunctionCallParser          # Hybrid: events first, fallback to function call
    FunctionDrivenParser               # Function call first (ABI decode)
      FunctionDrivenParserV2           # Modern version with handler objects
    ProxyWalletParser                  # Gnosis Safe / proxy wallet delegation
      DefaultMulticallProxyParser      # Multicall support (execTransaction)
```

**Why good:** Clear separation of parsing strategies. Each layer adds one concern:
- EventDrivenParser: "map event names to handler methods"
- FunctionDrivenParser: "map function names to handler methods"
- ProxyWalletParser: "delegate parsing to sub-parsers for proxy calls"

**Why problematic:** Too deep. 5+ levels of inheritance causes fragile base class problem.
Many `[UNCLEAR]` markers suggest confusion about which level handles what.

### 1.2 EventDrivenParser Pattern (CORE -- PORT THIS)

The most important pattern. Declarative mapping of Solidity events to handler methods:

```python
class EventDrivenParser(EVMContractParser):
    IGNORED_EVENTS: Set[str] = set()       # Events to skip silently
    EVENT_HANDLERS: Dict[str, str] = {}     # {"EventName": "handler_method_name"}
    FALLBACK_HANDLER: Optional[str] = None  # Called when no events match but transfers exist

    def get_journal_splits(self, tx, context) -> List[JournalSplit]:
        for event in self.get_contract_events(tx):
            if event["event"] in self.IGNORED_EVENTS:
                continue
            handler_name = self.EVENT_HANDLERS.get(event["event"])
            if handler_name:
                handler_func = getattr(self, handler_name)
                splits = handler_func(tx, event)
                out.extend(splits)
            else:
                unsupported.append(event)

        if unsupported:
            raise UnsupportedEventsError(...)

        if no_handled_events and has_transfers:
            if self.FALLBACK_HANDLER:
                # Use fallback handler
            else:
                raise TxParseError("unexpected transfers")

        return out
```

**Why good:**
- Declarative: Add new event support by adding one entry to EVENT_HANDLERS dict
- Self-documenting: IGNORED_EVENTS clearly lists known-irrelevant events
- Safety net: Unsupported events raise errors, preventing silent data loss
- Fallback: Handles edge cases where events don't fire but transfers happen

### 1.3 ExtEventDrivenParser Pattern (Enhanced Version)

Enhanced version that passes mutable transfer lists to handlers, so handlers can "consume" transfers:

```python
class ExtEventDrivenParser(EventDrivenParser):
    def get_journal_splits(self, tx, context):
        # Extract all transfers upfront
        ctx = TransactionContext.from_transaction(tx, self)
        token_transfers = ctx.token_transfers      # mutable list
        native_transfers = ctx.native_transfers     # mutable list

        for event in contract_events:
            handler_func = self.get_handler_for_event(event)
            # Handler signature includes transfer lists
            splits = handler_func(tx, event, token_transfers, native_transfers)
            out.extend(splits)

        # After all events: ALL transfers should be consumed
        if len(token_transfers) > 0 or len(native_transfers) > 0:
            raise TxParseError("Unexpected unconsumed transfers")
```

**Why good:** Transfer consumption prevents double-counting. Each handler pops its
transfers from the list, and leftover transfers signal a bug.

**Why problematic:** Mutable shared state. Order-dependent. Hard to test in isolation.

### 1.4 FunctionDrivenParser Pattern (V2 -- Modern)

Function-call-first approach. Decodes the Solidity function call and dispatches:

```python
class FunctionDrivenParserV2(EVMContractParser):
    FUNC_HANDLERS: Dict[str, str] = {}     # {"functionName": "handler_method_name"}
    IGNORED_FUNCTIONS: Set[str] = set()
    ENSURE_TOKEN_CONSUMED: bool = True

    def get_journal_splits(self, tx, context):
        fn, args = ContractInfo.decode_function_call2(tx, self)

        if self.is_ignored_func(fn.fn_name):
            return []

        handler_name = self.FUNC_HANDLERS.get(fn.fn_name)
        handler = getattr(self, handler_name)

        # Handler returns (splits, events_consumed)
        splits, events_used = handler(tx, args, context)

        if self.ENSURE_TOKEN_CONSUMED:
            # Verify all transfers were accounted for
```

**Why good:** Better for protocols where function name is more meaningful than events
(e.g., Aave V3 where supply/withdraw/borrow/repay are distinct functions).

### 1.5 ContractMap -- Parser Registry (PORT THIS PATTERN)

Two-level registry: Chain -> Address -> Parser. Lazy-loaded with fallback chain:

```
Lookup order:
1. In-memory cache (includes file-based parsers)
2. Local database (EVMParser table)
3. Reference API (external service)
4. Token detection (ERC20 / ERC721)
5. Return None (unknown contract)
```

```python
class ContractMap:
    _parsers: Dict[Chain, Dict[Web3Address, EVMContractParser]] = {}

    def get_contract_parser(self, chain, address) -> Optional[EVMContractParser]:
        self._build_chain_map_if_missing(chain)  # Lazy init

        # 1. Cache
        if address in self._parsers[chain]:
            return self._parsers[chain][address]

        # 2. Database
        parser_data = db.query(EVMParser).filter(...)
        if parser_data:
            parser = self._create_parser_from_data(...)
            self._parsers[chain][address] = parser
            return parser

        # 3-5. ref-api, token, NFT fallbacks...
```

**Why good:** Single point of parser selection. Lazy loading avoids startup cost.
Protocol helpers (init_aave_parsers, init_curve_parsers) register bulk parsers per chain.

**Why problematic:** Reference API coupling. Database dependency in parser lookup.
For our rewrite: keep the pattern, remove external API dependency.

### 1.6 LazyLoadEVMContractParser

Proxy/lazy pattern that defers parser instantiation until first use:

```python
class LazyLoadEVMContractParser:
    def __init__(self, parser_class, *args, **kwargs):
        self._parser_class = parser_class
        self._args = args
        self._kwargs = kwargs
        self._instance = None

    def __getattr__(self, name):
        if self._instance is None:
            self._instance = self._parser_class(*self._args, **self._kwargs)
        return getattr(self._instance, name)
```

**Why good:** Many contracts registered at startup but only a few used per run.
Avoids expensive Web3 contract initialization for unused parsers.

### 1.7 TransactionBundle -- Grouping Pattern

Groups transactions by (chain, block_number, tx_index) for multi-wallet scenarios:

```python
class TransactionBundle:
    key: GroupKey  # (chain, block_num, tx_index)
    tx_list: List[Transaction]
    timestamp: int  # min timestamp across txs
```

**Why good:** When multiple wallets participate in the same on-chain transaction,
they share the same receipt/events. Bundling avoids duplicate parsing.

### 1.8 Reusable Handler Objects (PORT THIS)

Extracted handler logic into composable objects instead of inheritance:

```python
class BaseHandler(ABC):
    def __init__(self, parser_map: ParserMap):
        self._map = parser_map

    @abstractmethod
    def __call__(self, tx, args, events, token_transfers, native_transfers):
        ...
```

Concrete handlers: SwapHandler, ClaimHandler, DepositHandler, WithdrawHandler,
BorrowHandler, RepayHandler, VaultInflowHandler, VaultOutflowHandler, OftFeeHandler.

These are used by FunctionDrivenParserV2 via composition:

```python
# Inside AaveV3ParserV2._handle_supply:
dh = DepositHandler(self._map)
splits = dh.process(
    token_transfers=ctx.token_transfers,
    native_transfers=ctx.native_transfers,
    wallet=wallet,
    protocol=Protocol.AAVE_V3,
    deposit_from_address=user,
    deposit_to_address=pool,
    deposit_value=amount,
)
```

**Why good:** Composition over inheritance. Same DepositHandler works for Aave, Compound,
Euler, etc. Handler knows accounting pattern, parser knows protocol specifics.

---

## 2. Key Interfaces -- Abstract Classes, Signatures

### 2.1 EVMContractParser (Core Base)

```python
class EVMContractParser(EVMParserAbstract):
    ABI_NAMES = AbiName.NULL              # ABI identifier(s) for event decoding
    DESCRIPTION_PREFIX = ""               # Human-readable protocol name

    def __init__(self, map: ParserMap, price_feed: PriceFeed, chain: Chain, address: str, *, abi=None):
        ...

    @property
    def address(self) -> str: ...          # Contract address this parser handles

    # Event handling
    def get_contract_events(self, tx: Transaction) -> List[EventData]: ...
    def get_erc20_transfers(self, tx: Transaction) -> List[EventData]: ...

    # Native asset handling
    @classmethod
    def net_native_transfers(cls, tx: Transaction) -> Dict[str, int]: ...

    # Journal split creation (ABSTRACT -- must implement)
    @abstractmethod
    def get_journal_splits(self, tx: Transaction, context: CallContext) -> List[JournalSplit]: ...

    # Wallet lookup
    def get_wallet(self, address: str) -> Optional[Wallet]: ...
    def get_erc20_token(self, address: str) -> ERC20Token: ...

    # Description
    def get_description(self, tx: Transaction) -> str: ...
```

### 2.2 EventDrivenParser Interface

```python
class EventDrivenParser(EVMContractParser):
    IGNORED_EVENTS: Set[str] = set()
    EVENT_HANDLERS: Dict[str, str] = {}
    FALLBACK_HANDLER: Optional[str] = None

    # Handler method signature (basic):
    def handler_method(self, tx: Transaction, event: EventData) -> List[JournalSplit]: ...

    # Handler method signature (extended, with transfer lists):
    def handler_method(self, tx: Transaction, event: EventData,
                       token_transfers: List[Transfer],
                       native_transfers: List[Transfer]) -> List[JournalSplit]: ...
```

### 2.3 FunctionDrivenParser Interface

```python
class FunctionDrivenParserV2(EVMContractParser):
    FUNC_HANDLERS: Dict[str, str] = {}        # {"solidity_function": "handler_method"}
    IGNORED_FUNCTIONS: Set[str] = set()
    ENSURE_TOKEN_CONSUMED: bool = True

    # Handler method signature:
    def handler_method(self, tx: Transaction, args: Dict[str, Any],
                       context: CallContext) -> Tuple[List[JournalSplit], List[EventData]]: ...
```

### 2.4 Handler Object Interface

```python
class BaseHandler(ABC):
    def __init__(self, parser_map: ParserMap): ...

    @abstractmethod
    def __call__(self, tx, args, events, token_transfers, native_transfers) -> Tuple[List[JournalSplit], List[EventData]]: ...

# Concrete handler .process() signatures:

class SwapHandler(BaseHandler):
    def process(self, token_transfers, native_transfers, beneficiary_wallet, **kwargs) -> List[JournalSplit]: ...

class DepositHandler(BaseHandler):
    def process(self, token_transfers, native_transfers, wallet, protocol,
                *, deposit_from_address=None, deposit_to_address=None,
                deposit_value=None, protocol_token_symbol=None,
                protocol_contract_address=None, protocol_position_id=None,
                protocol_token_amount=None) -> List[JournalSplit]: ...

class WithdrawHandler(BaseHandler):
    def process(self, ..., flow_direction=FlowDirection.WITHDRAW, ...) -> List[JournalSplit]: ...

class BorrowHandler(BaseHandler):
    def process(self, ..., protocol_account_type="debt", ...) -> List[JournalSplit]: ...

class RepayHandler(BaseHandler):
    def process(self, ..., flow_direction=FlowDirection.DEPOSIT, protocol_account_type="debt", ...) -> List[JournalSplit]: ...

class ClaimHandler(BaseHandler):
    def process(self, token_transfers, native_transfers, beneficiary_wallet,
                reward_token_symbol, protocol_contract_address, ...) -> List[JournalSplit]: ...
```

### 2.5 TransactionContext

Holds mutable state for all transfers/events during parsing of a single transaction:

```python
class TransactionContext:
    contract_events: List[EventData]      # Mutable: events get popped as consumed
    token_transfers: List[Transfer]       # Mutable: transfers get popped as consumed
    native_transfers: List[Transfer]      # Mutable
    nft_transfers: List[NFTTransfer]
    erc1155_transfers: List[ERC1155Transfer]

    @classmethod
    def from_transaction(cls, tx, parser, contract_map=None) -> TransactionContext: ...

    # Peek (find without removing)
    def peek_token_transfer(self, *, from_addr=None, to_addr=None, token_address=None, value=None): ...

    # Pop (find and remove from list)
    def pop_token_transfer(self, *, from_addr=None, to_addr=None, token_address=None, value=None): ...
    def pop_native_transfer(self, ...): ...
    def pop_event(self, event_name, address=None, args=None): ...

    # Filter to wallet-related transfers only
    def get_related_transfers(self, transfer_types: Set[TransferType], ...) -> List: ...
```

### 2.6 Transfer Data Types

```python
# Raw transfer (wei values, no token metadata)
Transfer = namedtuple("Transfer", [
    "chain",        # Chain enum
    "token_addr",   # Contract address (None for native)
    "from_addr",    # Sender address
    "to_addr",      # Receiver address
    "value",        # Amount in wei (int)
    "block_number", # Block number
])

# Enriched transfer (decimal amounts, token metadata)
class TokenTransfer(AnyTokenTransfer):
    token: ERC20Token
    from_addr: str
    to_addr: str
    amount: Decimal  # Already converted from wei

# Native transfer
class NativeTransfer(NamedTuple):
    from_addr: Web3Address
    to_addr: Web3Address
    value: int  # wei
```

### 2.7 ContractMap Interface

```python
class ContractMap:
    def get_contract_parser(self, chain: Chain, address: str) -> Optional[EVMContractParser]: ...
    def add_parser(self, chain, address, parser_class_name, params=None) -> EVMContractParser: ...
    def __contains__(self, key: Tuple[Chain, str]) -> bool: ...
    def __getitem__(self, key: Tuple[Chain, str]) -> EVMContractParser: ...
```

### 2.8 CallContext

Tracks state during recursive/proxy/multicall parsing:

```python
class CallContext:
    delegate_caller: Optional[Web3Address]
    transaction_context: Optional[TransactionContext]
    exclude_events: Set[int]     # logIndex values already consumed
    call_depth: int

    def initialize_transaction_context(self, tx, parser): ...
    def ensure_transaction_context(self) -> TransactionContext: ...
    def create_child_context(self, delegate_caller=None, ...) -> CallContext: ...
```

---

## 3. Domain Rules -- Business/Accounting Rules

### 3.1 Double-Entry Accounting Invariant

Every transaction produces journal splits that SUM TO ZERO:

```
For any JournalEntry:
    sum(split.amount for split in entry.splits) == 0

SWAP 1 ETH -> 2500 USDC:
    JournalSplit(account=asset_eth,  amount=-1)       # outflow
    JournalSplit(account=asset_usdc, amount=+2500)     # inflow
    # Requires price feed to balance in USD terms
```

### 3.2 Account Category Mapping

Each transfer maps to TWO accounts (from and to) based on address ownership:

```python
# If address is OUR wallet:
account = parser_map.token_asset(wallet, token)           # ASSET account

# If address is a protocol contract:
account = parser_map.protocol_asset(wallet, protocol, symbol)   # Protocol deposit (ASSET)
account = parser_map.protocol_debt(wallet, protocol, symbol)    # Protocol borrow (LIABILITY)
account = parser_map.protocol_rewards(wallet, protocol, symbol) # Rewards (INCOME)

# If address is unknown external:
account = parser_map.external_transfer(wallet, symbol, address) # External transfer

# If address is a known exchange:
account = parser_map.exchange(wallet, exchange, symbol)         # Exchange account

# For fees:
account = parser_map.wallet_expense(wallet, symbol, label)      # EXPENSE
account = parser_map.transaction_fees(wallet, symbol)           # Gas fees (EXPENSE)
```

### 3.3 DeFi Operation Accounting Rules

| Operation | From Account | To Account | Amount Sign |
|-----------|-------------|------------|-------------|
| Deposit | token_asset (wallet) | protocol_asset (aToken) | -/+ |
| Withdraw | protocol_asset (aToken) | token_asset (wallet) | -/+ |
| Borrow | protocol_debt | token_asset (wallet) | -/+ |
| Repay | token_asset (wallet) | protocol_debt | -/+ |
| Swap | token_asset_A (wallet) | token_asset_B (wallet) | -/+ |
| Claim | protocol_rewards | token_asset (wallet) | -/+ |
| Gas Fee | token_asset_native | expense_gas | -/+ |
| Liquidation | protocol_asset (collateral) | protocol_debt (debt) | -/+ |
| LP Deposit | token_asset | protocol_asset (LP) | -/+ |
| LP Withdraw | protocol_asset (LP) | token_asset | -/+ |

### 3.4 Transfer Consumption Pattern

Handlers MUST consume (pop) the transfers they account for from the mutable list:

```python
# Find and remove the matching transfer
token, from_addr, to_addr, amount = TransferManager.find_token_transfer(
    token_transfers,
    from_addr=user_address,
    to_addr=pool_address,
    value=expected_amount,
)

# After all handlers: leftover transfers = ERROR
if len(token_transfers) > 0:
    raise TxParseError("Unconsumed transfers detected")
```

This prevents double-counting and catches unexpected transfers.

### 3.5 Gas Fee Calculation

```python
def calculate_gas_fee_wei(tx_data, chain=None) -> int:
    receipt = tx_data.get("receipt", {})
    gas_used = receipt.get("gasUsed")
    gas_price = receipt.get("effectiveGasPrice", 0)

    gas_fee = gas_price * gas_used

    # L2 chains add L1 fee component
    if "l1Fee" in receipt:
        gas_fee += int(receipt["l1Fee"], 16)

    return gas_fee
```

### 3.6 Event-Driven Aave V3 _EVENT_MAP (Declarative Accounting)

The most elegant pattern -- declarative event-to-account mapping:

```python
class AaveV3Parser:
    _EVENT_MAP = {
        "Supply": [
            ("token_asset", "user", -1),        # Decrease user token
            ("protocol_asset", "onBehalfOf", 1), # Increase protocol position
        ],
        "Withdraw": [
            ("protocol_asset", "user", -1),      # Decrease protocol position
            ("token_asset", "to", 1),            # Increase user token
        ],
        "Borrow": [
            ("protocol_debt", "onBehalfOf", -1), # Increase debt (negative sign = increase liability)
            ("token_asset", "user", 1),          # Increase user token
        ],
        "Repay": [
            ("token_asset", "repayer", -1),      # Decrease user token
            ("protocol_debt", "user", 1),        # Decrease debt (positive sign = decrease liability)
        ],
    }
```

Each tuple is (account_category, event_arg_for_address, sign).
The parser loops over events, looks up the map, creates splits.

**Port this pattern.** It is the cleanest way to express protocol accounting rules.

---

## 4. What to Port

### [x] PORT -- EventDrivenParser pattern
The declarative event->handler mapping. Core of the system.
Clean it up: flatten inheritance, use composition instead.

### [x] PORT -- Handler objects (SwapHandler, DepositHandler, etc.)
Reusable accounting operations as composable objects.
Clean interface: process(transfers, wallet, protocol, ...) -> List[JournalSplit].

### [x] PORT -- ContractMap registry pattern
Chain -> Address -> Parser lookup with lazy loading.
Simplify: remove Reference API dependency, use config files or database only.

### [x] PORT -- TransactionContext (peek/pop transfer management)
Mutable context for tracking consumed events and transfers.
Key methods: pop_token_transfer, pop_native_transfer, pop_event.

### [x] PORT -- Transfer consumption + leftover validation
The pattern of handlers consuming transfers and validating none remain.
Critical for correctness (prevents double-counting).

### [x] PORT -- _EVENT_MAP declarative accounting rules
Aave's approach of mapping events to (account_type, address_key, sign).
Generalize for all lending protocols.

### [x] PORT -- TransactionBundle grouping
Group by (chain, block, tx_index) for multi-wallet transactions.

### [x] PORT -- Gas fee calculation (with L2 support)
calculate_gas_fee_wei with L1/L2 fee component handling.

### [x] PORT -- LazyLoadParser proxy pattern
Defer parser instantiation until first use. Saves startup time.

### [x] PORT -- ABI version management (AbiVersionSpecList)
Support contracts that upgrade ABIs at specific block numbers.

### [ ] REWRITE -- EVMContractParser base class
Too many concerns. Split into:
- Parser (logic only, no Web3 dependency)
- EventDecoder (ABI-specific event decoding)
- TransferExtractor (ERC20/native transfer extraction)

### [ ] REWRITE -- ParserMap / AccountMap
Too tightly coupled to SQLAlchemy session. Rewrite as pure domain service
with repository pattern underneath.

### [ ] REWRITE -- EVMRootParser
God class that does too much: spam detection, parser selection, bundling,
journal creation, pricing. Split into pipeline stages.

### [ ] REWRITE -- ProxyWalletParser / multicall handling
Too much [UNCLEAR] code. Recursive proxy parsing is fragile.
Rewrite with explicit call tree traversal.

### [ ] REWRITE -- GenericMethod utility class
Static method dumping ground. Break into focused utility modules.

### [ ] REWRITE -- Reference API integration
External API dependency in parser lookup. Replace with local config/database.

---

## 5. Clean Examples

### 5.1 Minimal EventDrivenParser Implementation

```python
class AaveV3StakedTokenParser(ExtEventDrivenParser):
    ABI_NAMES = (AbiName.AAVE_V3_STAKE_TOKEN,)
    DESCRIPTION_PREFIX = "Aave V3 Staked Token"
    PROTOCOL = Protocol.AAVE_STAKE

    # Ignore internal bookkeeping events
    IGNORED_EVENTS = {
        "AssetIndexUpdated", "UserIndexUpdated", "DelegatedPowerChanged",
        "RewardsAccrued", "Cooldown", "Transfer",
    }

    # Map events to handler methods
    EVENT_HANDLERS = {
        "Staked": "_handle_staked",
        "Redeem": "_handle_redeem",
        "RewardsClaimed": "_handle_rewards_claimed",
    }

    def _handle_staked(self, tx, event, token_transfers, native_transfers):
        user = event["args"]["to"]
        wallet = self.get_wallet(user)
        if not wallet:
            return []

        # Consume the token transfer
        token, _, _, amount = TransferManager.find_token_transfer(
            token_transfers, event["args"]["from"], self.address, event["args"]["assets"]
        )
        # Consume the mint transfer (aToken minted to user)
        TransferManager.pop_token_transfer(
            token_transfers, ADDRESS_ZERO, wallet.address, token_address=self.address
        )

        from_account = self._map.token_asset(wallet, token)
        to_account = self._map.protocol_asset(wallet, self.PROTOCOL, token.symbol, self.address)

        return [
            JournalSplit(account=from_account, amount=-amount),
            JournalSplit(account=to_account, amount=+amount),
        ]
```

### 5.2 FunctionDrivenParserV2 with Handler Objects

```python
class AaveV3ParserV2(FunctionDrivenParserV2):
    ABI_NAMES = (AbiName.AAVE_V3_POOL,)
    PROTOCOL = Protocol.AAVE_V3
    IGNORED_FUNCTIONS = {"setUserEMode", "setUserUseReserveAsCollateral"}

    FUNC_HANDLERS = {
        "supply": "_handle_supply",
        "withdraw": "_handle_withdraw",
        "borrow": "_handle_borrow",
        "repay": "_handle_repay",
    }

    def _handle_supply(self, tx, args, context):
        events_used = []

        # 1. Pop the Supply event
        e = EventManager.pop_event(context.transaction_context.contract_events, "Supply")
        events_used.append(e)

        # 2. Get wallet
        wallet = self.get_wallet(e["args"]["onBehalfOf"])
        if not wallet:
            return [], events_used

        # 3. Pop internal aToken transfer (cleanup)
        context.transaction_context.pop_token_transfer(
            from_addr=ADDRESS_ZERO, to_addr=e["args"]["onBehalfOf"]
        )

        # 4. Use composable DepositHandler
        dh = DepositHandler(self._map)
        splits = dh.process(
            token_transfers=context.transaction_context.token_transfers,
            native_transfers=context.transaction_context.native_transfers,
            wallet=wallet,
            protocol=self.PROTOCOL,
            deposit_value=e["args"]["amount"],
        )

        return splits, events_used
```

### 5.3 SwapHandler Usage

```python
# Inside any parser that detects a swap:
swap_handler = SwapHandler(self._map)
splits = swap_handler.process(
    token_transfers=ctx.token_transfers,
    native_transfers=ctx.native_transfers,
    beneficiary_wallet=wallet,
)
# SwapHandler internally:
# 1. Combines token + native transfers
# 2. Finds flows into/out of wallet using net_transfers_by_addr
# 3. Creates JournalSplits for each flow
# 4. Checks for same-symbol fee splits
```

### 5.4 ContractMap Parser Registration

```python
# File-based protocol registration (at startup):
def init_aave_v3_parsers(pmap, price_feed, chain):
    parsers = {}
    # Load pool addresses from config/database
    pool_address = get_aave_pool_address(chain)
    parsers[pool_address] = LazyLoadEVMContractParser(
        AaveV3Parser, pmap, price_feed, chain, pool_address
    )
    return parsers

# At ContractMap init:
build_chain_parsers(chain, pmap, price_feed, contract_map):
    parsers = init_aave_v3_parsers(pmap, price_feed, chain)
    contract_map._update_map(chain, parsers)
    # ... repeat for Uniswap, Curve, etc.
```

### 5.5 Declarative _EVENT_MAP Pattern

```python
# Generic approach for any lending protocol:
class LendingProtocolParser(EVMContractParser):
    PROTOCOL = None  # Set in subclass
    _EVENT_MAP = {}  # Set in subclass

    def get_journal_splits(self, tx, context):
        out = []
        for event in self.get_all_events(tx):
            token = self.get_erc20_token(event["args"]["reserve"])
            amount = token.get_decimal_amount(event["args"]["amount"])

            for category, address_key, sign in self._EVENT_MAP[event["event"]]:
                address = event["args"][address_key]
                wallet = self.get_wallet(address)
                if not wallet:
                    continue

                account = self._get_account(category, wallet, token)
                out.append(JournalSplit(account=account, amount=sign * amount))

        return out

    def _get_account(self, category, wallet, token):
        if category == "token_asset":
            return self._map.token_asset(wallet, token)
        elif category == "protocol_asset":
            return self._map.protocol_asset(wallet, self.PROTOCOL, token.symbol)
        elif category == "protocol_debt":
            return self._map.protocol_debt(wallet, self.PROTOCOL, token.symbol)
```

---

## 6. File Inventory (Legacy)

### Parser Core (v2/parser/)
| File | Purpose | Lines | Port? |
|------|---------|-------|-------|
| `_abstract.py` | RootParserAbstract, TransactionBundle | ~120 | Pattern only |
| `evm_root.py` | EVMRootParser entry point | ~300 | Rewrite |
| `map.py` | ParserMap (extends AccountMap) | ~100 | Rewrite |

### EVM Parser Engine (v2/parser/evm/)
| File | Purpose | Lines | Port? |
|------|---------|-------|-------|
| `contract/_abstract.py` | EVMContractParser, EventDrivenParser, ProxyWalletParser | ~640 | Port patterns |
| `contract/generic.py` | ExtEventDrivenParser, FunctionDrivenParser, FunctionDrivenParserV2 | ~500 | Port patterns |
| `contract_map.py` | ContractMap registry | ~400 | Port pattern, simplify |
| `contract_info.py` | ABI decoding, AbiVersionSpec | ~100+ | Port ABI version pattern |
| `generic_utils.py` | GenericMethod, TransactionContext, TransferManager, EventManager, Transfer | ~1800 | Port key classes |

### Handlers (v2/parser/evm/handler/)
| File | Purpose | Port? |
|------|---------|-------|
| `base.py` | BaseHandler ABC | Port |
| `swap.py` | SwapHandler, MultiSwapHandler | Port |
| `claim.py` | ClaimHandler | Port |
| `single_flow.py` | SingleFlowProtocolHandler, DepositHandler, WithdrawHandler, BorrowHandler, RepayHandler, VaultInflow/Outflow | Port |
| `misc.py` (single_flow.py) | OftFeeHandler | Port if needed |

### Protocol Parsers (v2/parser/evm/contract/)
| File | Purpose | Port? |
|------|---------|-------|
| `aave.py` | AaveV2Parser, AaveV3Parser, AaveV3ParserV2 + variants | Port (priority) |
| `curve.py` | Curve pool parser | Port |
| 60+ other protocol files | Various DeFi protocols | Port as needed |

### Events (v2/parser/events/)
| File | Purpose | Port? |
|------|---------|-------|
| `_abstract.py` | EventParserAbstract (protocol events, not EVM events) | Port pattern |
| `root.py` | RootEventParser registry | Port pattern |

---

## 7. Recommended Architecture for CryptoTax VN

Based on legacy analysis, the new parser engine should:

```
ParserEngine (orchestrator)
  |
  +-- ParserRegistry (Chain -> Address -> Parser)
  |     +-- register_protocol_parsers(chain)   # bulk registration
  |     +-- get_parser(chain, address)          # lazy lookup
  |
  +-- TransactionContext (per-TX mutable state)
  |     +-- token_transfers: List[Transfer]     # peek/pop
  |     +-- native_transfers: List[Transfer]    # peek/pop
  |     +-- contract_events: List[EventData]    # peek/pop
  |
  +-- Parser (per-contract logic)
  |     +-- EventDrivenParser                   # event -> handler mapping
  |     +-- FunctionDrivenParser                # function -> handler mapping
  |     +-- GenericEVMParser                    # auto-detect from transfers only
  |
  +-- Handlers (composable accounting operations)
  |     +-- SwapHandler
  |     +-- DepositHandler / WithdrawHandler
  |     +-- BorrowHandler / RepayHandler
  |     +-- ClaimHandler
  |
  +-- AccountMapper (address -> Account resolution)
        +-- token_asset(wallet, token)
        +-- protocol_asset(wallet, protocol, symbol)
        +-- protocol_debt(wallet, protocol, symbol)
        +-- expense(wallet, category)
```

Key simplifications from legacy:
1. Flatten inheritance to max 2 levels (Base -> Protocol)
2. Use DI container instead of ParserMap global
3. Remove Reference API dependency
4. Use async repository pattern instead of session-coupled AccountMap
5. Split GenericMethod into focused modules
6. Type everything with Pydantic models
