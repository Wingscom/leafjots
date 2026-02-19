# Business Logic -- Distilled Reference

> Distilled from Pennyworks/ChainCPA v2 legacy code.
> Source files: `bookkeeper.py`, `capital_gains.py`, `capital_gains_cache.py`,
> `account_map.py`, `reports.py`, `reporting/{components,formatters}.py`, `viewer.py`

---

## Patterns -- Design Patterns, Why Good

### 1. Bookkeeper Pattern (Coordinator)

The `Bookkeeper` is the central orchestrator that converts parsed transactions into
journal entries. It coordinates between parsers, price feeds, and the database.

```
Bookkeeper
  |-- TransactionProcessor (delegates actual parsing)
  |-- ParserMap (registry of event->handler mappings)
  |-- PriceFeed (prices journal splits at entry time)
  |-- AccountMap (lazily creates/retrieves accounts)
```

**Why good:** Single responsibility -- Bookkeeper only coordinates. Parsing logic
lives in parsers, pricing in PriceFeed, account resolution in AccountMap.

**Why broken:** The legacy Bookkeeper uses synchronous SQLAlchemy sessions, has
`[UNCLEAR]` sections, and the `update_journal()` method has a syntax error in its
parameter list (`coin_types: list[str] = None, list[str] = []`). The session is
leaked through the constructor (no DI container).

### 2. Double-Entry Journal (Accounting Core)

Every transaction produces a `JournalEntry` containing `JournalSplit` records.
The fundamental invariant:

```
SUM(all splits in an entry) == 0    # NON-NEGOTIABLE
```

Splits are created in pairs: one negative (source/decrease), one positive
(destination/increase). Price feed values each split in the entity's base currency
at the time of the transaction.

**JournalEntry structure:**
```python
JournalEntry:
    id: UUID
    description: str
    timestamp: int          # Unix timestamp
    created_by: str         # "Bookkeeper", "ManualEntry", etc.
    manual_input: bool
    splits: List[JournalSplit]

JournalSplit:
    account: Account        # Which account this affects
    amount: Decimal         # Quantity change (negative=decrease, positive=increase)
    value_in_currency: Decimal  # Value in base currency (USD/VND) at time of TX
    currency: Currency      # Base currency used for valuation
    memo: str               # Optional descriptive text
```

**Why good:** True double-entry -- every movement is tracked with counterparts.
The sum-to-zero invariant catches bugs immediately.

### 3. AccountMap Pattern (Lazy Account Registry)

`AccountMap` provides get-or-create semantics for accounts. Accounts are identified
by a `unique_key` composed from their properties. If the account already exists,
it returns the cached version; otherwise it creates a new one and adds it to the
session.

**Why good:** Prevents duplicate accounts, provides a clean interface for parsers
to request accounts without worrying about persistence.

**Why broken:** Uses `lru_cache` on wallet lookups (state leak), the read-only
check is unclear (`if not self._map`), and session management is leaky.

### 4. Capital Gains Calculator (FIFO Lot Matching)

The `GainsCalculator` implements FIFO lot matching for capital gains/losses. It
processes a stream of `Trade` events (BUY/SELL) and produces `ClosedLot` records
when a sell matches against a prior buy.

```
Trade event stream (sorted by timestamp)
  --> GainsCalculator
      --> FIFO matching: oldest buy lot consumed first
      --> OpenLot (remaining position)
      --> ClosedLot (realized gain/loss)
```

**Why good:** Clean separation of Trade/OpenLot/ClosedLot concepts. Supports
both GLOBAL_FIFO and PER_WALLET modes. Serializable state for snapshotting.

**Why broken:** The code has numerous bugs -- see [What's Broken in Capital Gains](#whats-broken-in-capital-gains).

### 5. Capital Gains Snapshot Caching

`CapitalGainsCache` avoids reprocessing all historical events by snapshotting
calculator state at month-end boundaries.

**Cache invalidation strategy:**
- A `JournalFingerprint` is computed from journal splits up to a timestamp
- Fingerprint = (COUNT, SUM(ABS(amount)), SUM(ABS(value)), MAX(split_id))
- If any journal data changes (insert, delete, edit), the fingerprint changes
- Invalid snapshots cascade-delete all future snapshots

**Boundary semantics:**
- Snapshot at timestamp T = state after processing all events with timestamp <= T
- Resume fetches events with timestamp > T (exclusive start)
- No overlap: snapshot captures [0, T], resume fetches (T, to_date]

**Why good:** Clever fingerprint-based invalidation. Monthly granularity balances
cache hit rate vs storage. State serialization is well-defined.

**Why port-worthy:** The fingerprint + cascade invalidation approach is elegant.
The month-end boundary semantics are sound.

### 6. Report Builder Pattern (Template Method)

Reports are built using a hierarchy of report builders:

```
BaseReportBuilder (abstract)
  |-- ClientReportBuilder (standard client reports)
       |-- BaseNAVReportBuilder (NAV reports, template method)
            |-- NAVReportBuilder (with performance fees)
            |-- RedemptionNAVReportBuilder (with pending redemptions)
       |-- L1ReportBuilder (L1 chain-specific augmentations)
```

Output is a `ReportData` named tuple containing DataFrames for each sheet.

### 7. Formatter Pattern (Strategy)

Report output uses a Strategy pattern via `FormatterFactory`:

```python
FormatterFactory.get_formatter("json").format(data)   # -> dict
FormatterFactory.get_formatter("csv").format(data)     # -> str
FormatterFactory.get_formatter("dataframe").format(data) # -> pd.DataFrame
```

Components calculate once (canonical format), formatters serialize multiple
times without recalculation.

**Why good:** Clean separation of calculation vs presentation. Extensible via
`register_formatter()`.

---

## Key Interfaces -- Abstract Classes, Signatures

### Bookkeeper

```python
class Bookkeeper:
    def __init__(self, session: Session, entity: Union[str, Entity],
                 transaction_class: str = "Transaction")

    def update_journal(
        self,
        as_of_date: Optional[TimestampType] = None,
        skip_date: Optional[TimestampType] = None,
        batch_size: int = 5000,
        skip_price_validation: bool = False,
    ) -> Tuple[List[int], List[int]]
    """Returns (processed_tx_ids, unprocessed_tx_ids)"""

    def parse_events(self) -> int
    """Parse ProtocolEvents into journal entries. Returns count."""

    def add_manual_entry(
        self,
        timestamp: TimestampType,
        description: str,
        from_account: Account,
        to_account: Account,
        from_amount: Optional[Decimal] = None,
        to_amount: Optional[Decimal] = None,
    )
    """Create a manual journal entry with two splits."""

    def delete_journal_entries(self, wallet=None, include_manual=False, ...)
    def delete_manual_entry(self, timestamp, description)
```

### Capital Gains Core Types

```python
class Trade(BaseModel):
    id: str
    timestamp: int
    account_id: str
    symbol: Symbol
    side: TradeSide        # BUY or SELL
    quantity: Decimal
    value: Decimal          # Total value (not per-unit)
    currency: Currency
    is_flow: bool           # True = external transfer (not taxable gain)

class BasisAdjustment(BaseModel):
    id: str
    timestamp: int
    account_id: str
    symbol: Symbol
    value: Decimal          # Adjustment to cost basis
    currency: Currency

CapitalEvent = Union[Trade, BasisAdjustment]

class OpenLot:
    """Represents an unmatched position (partial or full)."""
    trade: Trade
    open_quantity: Decimal   # Remaining unmatched quantity
    cost_basis: Decimal      # Pro-rata cost for open_quantity
    value: Decimal           # Per-unit value

    def match(self, quantity: Decimal)
    """Consume quantity from this lot."""

class ClosedLot:
    """Represents a matched buy-sell pair (realized gain/loss)."""
    open_trade: Trade        # The buy
    close_trade: Trade       # The sell
    matched_quantity: Decimal
    date_acquired: date
    date_sold: date
    cost_basis: Decimal      # Pro-rata cost for matched_quantity
    proceeds: Decimal        # Pro-rata proceeds for matched_quantity
    gain: Decimal            # proceeds - cost_basis + adjustments
    is_short_term: bool      # Held <= 1 year
```

### GainsCalculator

```python
class GainsMode(str, Enum):
    GLOBAL_FIFO = "GLOBAL_FIFO"    # All accounts share one lot queue per symbol
    PER_WALLET = "PER_WALLET"       # Each wallet has its own lot queues

class GainsCalculator:
    def __init__(self, base_currency: Currency = Currency.USD,
                 mode: GainsMode = GainsMode.GLOBAL_FIFO)

    def process_single(self, event: CapitalEvent)
    """Process one event. Events MUST be in timestamp order."""

    def process_events(self, events: List[CapitalEvent])
    """Process a batch. Auto-sorts by timestamp."""

    def get_state(self) -> dict
    """Serialize open lots for snapshotting."""

    def restore_state(self, state: dict)
    """Resume from a snapshot."""

    def open_lots(self) -> Optional[pd.DataFrame]
    def gains_data(self) -> Optional[pd.DataFrame]
    def gains_summary(self) -> Optional[pd.DataFrame]
    """Monthly summary grouped by holding period (S/L)."""
```

### AccountMap

```python
class AccountMap:
    def __init__(self, session: Session, entity: Union[str, Entity])

    # Token accounts (main interface for parsers)
    def token_asset(self, wallet, token) -> AnyTokenAccount
    def native_asset(self, wallet) -> NativeAssetAccount
    def erc20(self, wallet, token) -> ERC20TokenAccount
    def nft(self, wallet, token) -> NFTTokenAccount

    # Protocol accounts (DeFi positions)
    def protocol_asset(self, wallet, protocol, symbol, ...) -> ProtocolAssetAccount
    def protocol_debt(self, wallet, protocol, symbol, ...) -> ProtocolDebtAccount
    def protocol_rewards(self, wallet, protocol, symbol, ...) -> ProtocolRewardsAccount

    # Income/Expense accounts
    def wallet_income(self, wallet, symbol, tag) -> WalletIncomeAccount
    def wallet_expense(self, wallet, symbol, tag) -> WalletExpenseAccount
    def interest_income(self, wallet, symbol) -> WalletIncomeAccount
    def interest_expense(self, wallet, symbol) -> WalletExpenseAccount
    def transaction_fees(self, wallet, symbol) -> WalletExpenseAccount

    # Other accounts
    def external_transfer(self, wallet, symbol, external_address) -> ExternalTransferAccount
    def exchange(self, entity, exchange, symbol, tag) -> ExchangeAccount
    def equity(self, entity, symbol, tag) -> EquityAccount
    def gift(self, entity, symbol, tag) -> GiftAccount
    def unknown(self, entity, symbol) -> UnknownAccount
    def bank(self, entity) -> BankAccount
    def manual_entry(self, entity, account_type, symbol, description) -> ManualEntryAccount
```

### Report Builder

```python
class BaseReportBuilder:
    @classmethod
    def gen_report_data(cls, entity_name, from_date, to_date,
                        short_version=True, include_flat_journal=False,
                        aggregate=False, gains_mode=GainsMode.GLOBAL_FIFO,
                        include_wallet_list=False, show_internal=False
    ) -> ReportData

class ReportData(NamedTuple):
    final_summary: pd.DataFrame
    bs_amt: pd.DataFrame              # Balance sheet by quantity
    bs_mkt: pd.DataFrame              # Balance sheet by market value (USD)
    income: pd.DataFrame              # Income statement
    period_flows_amt: pd.DataFrame    # Period flows by quantity
    period_flows_val: pd.DataFrame    # Period flows by value
    gains_data: pd.DataFrame          # Realized gains
    open_lots: pd.DataFrame           # Open lots (unrealized)
    flow_fmt: pd.DataFrame            # Full journal (formatted)
    src_dest_fmt: Optional[pd.DataFrame]  # Flat journal (src->dest pairs)
    currency: str                     # Base currency
    warnings: Optional[List[str]]     # Validation warnings
    settings: pd.DataFrame            # Report parameters
    wallets: Optional[pd.DataFrame]   # Wallet list
```

### PeriodSummary (Viewer output)

```python
class PeriodSummary(NamedTuple):
    period_end: float
    balance_sheet_start: Optional[pd.DataFrame]
    balance_sheet_end: Optional[pd.DataFrame]
    open_lots_start: Optional[pd.DataFrame]
    open_lots_end: Optional[pd.DataFrame]
    income_statement: Optional[pd.DataFrame]
    gains: Optional[pd.DataFrame]

    # Computed properties:
    realized_gains: Decimal
    flow_gains: Decimal
    unrealized_gains_start: Decimal
    unrealized_gains_end: Decimal
```

---

## Domain Rules -- Business / Accounting Rules

### Rule 1: Double-Entry Invariant

Every journal entry MUST have splits that sum to zero:

```
SUM(split.amount for split in entry.splits) == 0    # By quantity
SUM(split.value_in_currency for split in entry.splits) == 0  # By value
```

If this invariant is violated, the entry is flagged as unbalanced (a bug).

### Rule 2: Sign Convention

```
Negative amount = DECREASE in that account (source)
Positive amount = INCREASE in that account (destination)
```

Examples:
```
SWAP 1 ETH -> 2500 USDC:
    Split 1: ETH account,  amount = -1,     value = -2500 USD
    Split 2: USDC account, amount = +2500,  value = +2500 USD
    SUM = 0 (balanced)

GAS FEE 0.01 ETH:
    Split 1: ETH account,     amount = -0.01,  value = -25 USD
    Split 2: Gas Expense acct, amount = +0.01,  value = +25 USD
    SUM = 0 (balanced)

AAVE DEPOSIT 1000 USDC:
    Split 1: USDC account,          amount = -1000, value = -1000 USD
    Split 2: Protocol:Aave:USDC,    amount = +1000, value = +1000 USD
    SUM = 0 (balanced)

AAVE BORROW 500 DAI:
    Split 1: DAI account,           amount = +500,  value = +500 USD
    Split 2: Protocol:Aave:Debt:DAI, amount = -500,  value = -500 USD
    SUM = 0 (balanced)
```

### Rule 3: Account Types

Four fundamental account types:
```
ASSET       Positive balance = user owns tokens. Chain:Wallet:Token
LIABILITY   Negative balance = user owes. Protocol debts.
INCOME      Accumulated revenue: interest, rewards, yield
EXPENSE     Accumulated costs: gas fees, tx fees
FLOW        External capital flows (deposits/withdrawals from entity)
```

### Rule 4: Account Naming Convention

Accounts are identified by a hierarchical `unique_key`:

```
{Chain}:{WalletAddress}:{AccountType}:{Details}

Examples:
  Ethereum:0xABC...:NativeAsset              # ETH balance
  Ethereum:0xABC...:ERC20:USDC:0x123...      # USDC token
  Ethereum:0xABC...:Protocol:Aave:USDC       # Aave deposit position
  Ethereum:0xABC...:Protocol:Aave:Debt:DAI   # Aave debt position
  Ethereum:0xABC...:Income:Interest Income    # Interest earned
  Ethereum:0xABC...:Expense:Tx Fees          # Gas fees
  Ethereum:0xABC...:External:0xDEF...        # Transfer to external address
```

Standard tags for income/expense:
```python
INTEREST_INCOME_TAG = "Interest Income"
INTEREST_EXPENSE_TAG = "Interest Expense"
TRANSACTION_FEES_TAG = "Tx Fees"
```

### Rule 5: FIFO Lot Matching

Capital gains are calculated using First-In-First-Out:

```
1. BUY creates an OpenLot (pushed to back of deque)
2. SELL matches against the OLDEST OpenLot first (popleft from deque)
3. Partial matches: lot is split -- matched portion becomes ClosedLot,
   remainder stays as OpenLot
4. Multiple matches: one SELL can consume multiple lots
5. Events MUST be processed in timestamp order
```

FIFO modes:
```
GLOBAL_FIFO  -- All accounts share one lot queue per symbol (VN requirement)
PER_WALLET   -- Each wallet maintains independent lot queues
```

### Rule 6: Holding Period

```
Short-term: Held <= 365 days (SECONDS_PER_YEAR = 60 * 60 * 24 * 365)
Long-term:  Held > 365 days
```

Determined by: `close_trade.timestamp - open_trade.timestamp`

### Rule 7: Flow vs Trade

Trades marked as `is_flow=True` represent external capital flows (deposits into
or withdrawals from the entity). Flow gains/losses are tracked separately from
trading gains because they represent capital movement, not taxable events.

### Rule 8: Wash Trade Handling

The legacy code includes wash trade detection and basis adjustment logic (US tax
rule). A wash trade occurs when a loss is realized and a replacement position is
acquired within a window.

**For Vietnam (CryptoTax VN):** Wash trade rules do NOT apply. Vietnam uses a
flat 0.1% transfer tax. This entire subsystem should NOT be ported.

### Rule 9: Basis Adjustments

`BasisAdjustment` events modify the cost basis of existing open lots without
creating new positions. Applied pro-rata across all open lots for the given
account/symbol.

### Rule 10: Price Validation

Journal splits are priced via `price_journal_splits()` at entry creation time.
The price feed provides token prices in the entity's base currency. A
`no_adjustment_limit` flag can disable large-price-mismatch validation.

### Rule 11: Report Validation (Sanity Checks)

Reports validate:
1. Balance sheet consistency: end balance = start balance + net changes
2. Lots vs balance sheet: token gains from open lots match balance sheet values
3. Warnings are collected and included in report output

---

## What's Broken in Capital Gains

The `capital_gains.py` file has **significant bugs** that make it non-functional
as-is. These are catalogued here for awareness -- do NOT copy this code.

### Bug 1: OpenLot.match() is empty

```python
def match(self, quantity: Decimal):
    if quantity <= 0:
        raise ValueError(...)
    # BUG: No actual matching logic! Never updates self._open_quantity
```

The method validates the quantity but never decrements `_open_quantity`.

### Bug 2: _add_lot() has duplicate and contradictory logic

```python
def _add_lot(self, lot: 'OpenLot'):
    lot_queue = self._lot_queue(lot)          # Get queue
    if lot.open_quantity <= 0: raise ...       # Check lot

    empty_lot = self._lot_queue(lot)          # BUG: Gets queue again, treats as lot
    if empty_lot.open_quantity <= 0: raise ... # BUG: Deque has no .open_quantity

    lot_queue = self._lot_queue(lot)          # Gets queue AGAIN
    bisect.insort_right(lot_queue, lot, ...)  # Insert sorted
    lot_queue.append(lot)                     # BUG: Also appends -- double insert!
```

### Bug 3: _find_match() references undefined variables

```python
def _find_match(self, trade: Trade):
    # ...
    if not temp_match:      # BUG: temp_match undefined in this scope
        return None
    out = temp_match

    if out.timestamp < out.timestamp:  # BUG: Compares to itself (always False)
        self._add_lot(out)
    else:
        self._add_lot(temp_match)      # Same as out -- meaningless branch
```

### Bug 4: _match_lot() signature is broken

```python
def _match_lot(self, new_lot: 'OpenLot', new_lot_open_quantity: Decimal,
               new_lot: 'OpenLot') -> Optional['ClosedLot']:
    # BUG: 'new_lot' parameter declared twice
    # BUG: 'matching_lot' used but never defined in this scope
    matching_quantity = min(matching_lot.open_quantity, new_lot.open_quantity)
```

### Bug 5: _process_trade() uses dict where list expected

```python
new_closed_lots: list[ClosedLot] = {}  # BUG: Initializes as dict, not list
# ...
new_closed_lots.append(...)            # Will fail at runtime
```

### Bug 6: process_events() references undefined method

```python
def process_events(self, events):
    sorted_trades = sorted(events, key=lambda x: x.timestamp)
    self._process_single(x)  # BUG: 'x' undefined, should iterate
    # Should be: for event in sorted_trades: self._process_single(event)
```

### Bug 7: apply_basis_adjustment() references undefined variables

```python
def apply_basis_adjustment(self, adjustment):
    # ...
    total_adj    # BUG: undefined
    value_adjustment  # BUG: undefined in the loop body
    # The method is at the end of GainsCalculator but the
    # process_single dispatching code appears after it without
    # proper method boundaries
```

### Bug 8: ClosedLot.aligned_net_amount() returns nothing

```python
def aligned_net_amount(self, trade: Trade) -> Decimal:
    adj_sign = trade.total_adjustment * self._matched_quantity / trade.quantity
    # BUG: No return statement
```

### Bug 9: ReplacementLot.__init__() references undefined variables

```python
class ReplacementLot:
    def __init__(self, original_lot, wash_lot, amount):
        # ...
        value=(orig_trade.value * amount) / orig_trade.quantity * basis_adj,
        # BUG: basis_adj is undefined
        super().__init__(trade)  # BUG: ReplacementLot has no parent with __init__(trade)
        self.original_lot_match(amount)  # BUG: no such method
```

### Summary of Capital Gains Status

The **concepts** are sound (Trade/OpenLot/ClosedLot/FIFO/snapshotting), but the
**implementation** is riddled with bugs -- undefined variables, missing return
statements, duplicate parameters, wrong types. This code cannot run as-is.

**Verdict:** Port the CONCEPTS (types, FIFO algorithm, snapshot caching), but
REWRITE the implementation from scratch.

---

## What to Port

### [x] PORT -- Concepts and patterns to carry forward

- [x] **Double-entry journal model** -- JournalEntry + JournalSplit with sum=0 invariant
- [x] **Sign convention** -- Negative=decrease, Positive=increase
- [x] **Account type hierarchy** -- ASSET, LIABILITY, INCOME, EXPENSE, FLOW
- [x] **AccountMap get-or-create pattern** -- Lazy account creation with unique keys
- [x] **Account naming convention** -- `Chain:Wallet:Type:Details`
- [x] **Standard account tags** -- "Interest Income", "Interest Expense", "Tx Fees"
- [x] **FIFO lot matching algorithm** -- Trade -> OpenLot -> ClosedLot pipeline
- [x] **GainsMode enum** -- GLOBAL_FIFO (required for VN), PER_WALLET
- [x] **Trade/OpenLot/ClosedLot type system** -- Clean domain models
- [x] **Snapshot caching with fingerprint invalidation** -- Monthly boundaries, cascade delete
- [x] **Snapshot serialization** -- get_state() / restore_state() on GainsCalculator
- [x] **JournalFingerprint validation** -- COUNT + SUM(ABS(amount)) + SUM(ABS(value)) + MAX(id)
- [x] **ReportData structure** -- Named tuple with all report DataFrames
- [x] **Excel sheet layout** -- summary, balance_sheet_by_qty, balance_sheet_by_value_USD/VND, income_statement, flows_by_qty, flows_by_value, realized_gains, open_lots, journal, warnings, wallets, settings
- [x] **Formatter pattern** -- Strategy pattern with FormatterFactory
- [x] **PeriodSummary concept** -- Balance sheets at start/end, income, gains, open lots
- [x] **Report validation sanity checks** -- Balance consistency, lots vs balance sheet
- [x] **Holding period calculation** -- timestamp difference, S/L classification
- [x] **Token -> Account type routing** -- `token_asset()` dispatching by token type
- [x] **Protocol position accounts** -- Separate asset vs debt vs rewards accounts
- [x] **Basis adjustment concept** -- Modifying cost basis of existing lots

### [ ] REWRITE -- Use concept but write from scratch

- [ ] **GainsCalculator implementation** -- Keep types, rewrite FIFO engine (legacy is broken)
- [ ] **Bookkeeper orchestration** -- Rewrite with async, DI, proper error handling
- [ ] **AccountMap session management** -- Replace lru_cache + leaked session with DI
- [ ] **Report builder hierarchy** -- Simplify for VN (no NAV, no performance fees)
- [ ] **Price feed integration** -- Rewrite with async httpx + tenacity
- [ ] **Journal pricing** -- `price_journal_splits()` needs async + better error handling

### [ ] DO NOT PORT -- Legacy-specific, irrelevant, or broken

- [ ] ~~Wash trade detection~~ -- US tax rule, not applicable to VN 0.1% transfer tax
- [ ] ~~ReplacementLot~~ -- Part of wash trade system
- [ ] ~~NAVCalculator / NAVReportBuilder~~ -- Fund NAV calculations, not needed for individual tax
- [ ] ~~RedemptionNAVCalculator~~ -- On-chain redemption tracking for funds
- [ ] ~~L1ReportBuilder~~ -- Octav-specific L1 chain reporting
- [ ] ~~Vault lens on-chain validation~~ -- Fund-specific vault share validation
- [ ] ~~Performance/management/admin/incentive fees~~ -- Fund management fees
- [ ] ~~CurrencyConverter (reports.py version)~~ -- Tied to NAV, too complex
- [ ] ~~ExchangeWallet / ExchangeAccount~~ -- CEX-specific (DeFi-first)
- [ ] ~~AddressBook config~~ -- File-based address labeling (use DB instead)
- [ ] ~~Synchronous SQLAlchemy sessions~~ -- Rewrite all DB access as async
- [ ] ~~`with_polymorphic` query patterns~~ -- Over-engineered ORM usage

---

## Clean Examples

### Example 1: Creating a Journal Entry (Swap)

Pattern to port -- how a swap creates balanced journal splits:

```python
# SWAP: 1 ETH -> 2500 USDC on Uniswap
# Parser produces this:

entry = JournalEntry(
    description="Swap 1 ETH for 2500 USDC via Uniswap V3",
    timestamp=1700000000,
    created_by="GenericSwapParser",
)

entry.splits = [
    JournalSplit(
        account=account_map.native_asset(wallet),      # ETH account
        amount=Decimal("-1"),                            # Decrease
        value_in_currency=Decimal("-2500.00"),           # USD value
        currency=Currency.USD,
    ),
    JournalSplit(
        account=account_map.erc20(wallet, usdc_token),  # USDC account
        amount=Decimal("2500"),                          # Increase
        value_in_currency=Decimal("2500.00"),            # USD value
        currency=Currency.USD,
    ),
]

# Gas fee is a separate entry:
gas_entry = JournalEntry(
    description="Gas fee for swap",
    timestamp=1700000000,
    created_by="GenericEVMParser",
)

gas_entry.splits = [
    JournalSplit(
        account=account_map.native_asset(wallet),
        amount=Decimal("-0.005"),
        value_in_currency=Decimal("-12.50"),
        currency=Currency.USD,
    ),
    JournalSplit(
        account=account_map.transaction_fees(wallet, Symbol.ETH),
        amount=Decimal("0.005"),
        value_in_currency=Decimal("12.50"),
        currency=Currency.USD,
    ),
]
```

### Example 2: FIFO Lot Matching (Simplified)

The correct algorithm (not the broken legacy code):

```python
# Events in order:
# T1: BUY  2 ETH at $1000 each  (total value = $2000)
# T2: BUY  1 ETH at $1500       (total value = $1500)
# T3: SELL 1.5 ETH at $2000 each (total value = $3000)

# After T1: OpenLots = [Lot(2 ETH, $2000, T1)]
# After T2: OpenLots = [Lot(2 ETH, $2000, T1), Lot(1 ETH, $1500, T2)]

# T3 SELL 1.5 ETH:
#   FIFO matches against Lot(T1) first:
#     Match 1.5 ETH from Lot(T1):
#       cost_basis = $2000 * 1.5 / 2 = $1500
#       proceeds   = $3000 * 1.5 / 1.5 = $3000
#       gain       = $3000 - $1500 = $1500
#     Lot(T1) reduced: 0.5 ETH remaining

# After T3:
#   OpenLots = [Lot(0.5 ETH, $500, T1), Lot(1 ETH, $1500, T2)]
#   ClosedLots = [ClosedLot(1.5 ETH, cost=$1500, proceeds=$3000, gain=$1500)]
```

### Example 3: Account Map Usage (DeFi Positions)

```python
# Aave V3 Deposit: 1000 USDC
# Parser calls:
src_account = account_map.erc20(wallet, usdc_token)
dst_account = account_map.protocol_asset(
    wallet=wallet,
    protocol=Protocol.AAVE_V3,
    symbol=Symbol.USDC,
    contract_address="0xbcca60bb61934080951369a648fb03df4f96263c",  # aUSDC
)

# Aave V3 Borrow: 500 DAI
asset_account = account_map.erc20(wallet, dai_token)
debt_account = account_map.protocol_debt(
    wallet=wallet,
    protocol=Protocol.AAVE_V3,
    symbol=Symbol.DAI,
    contract_address="0x6c3c78838c761c6ac7be9f59fe808ea2a6e4379d",  # variableDebtDAI
)

# Interest earned: 10 USDC
interest_account = account_map.interest_income(wallet, Symbol.USDC)
# Creates: WalletIncomeAccount with tag="Interest Income"
```

### Example 4: Snapshot Caching Flow

```python
# First run: No snapshot exists
cache = CapitalGainsCache(session, viewer)
calculator = cache.get_calculator(entity, to_ts=1700000000)
# -> Processes all events from epoch
# -> Saves snapshots at month boundaries:
#    2023-10-31 23:59:59, 2023-11-30 23:59:59, etc.

# Second run: Snapshot exists at 2023-10-31
calculator = cache.get_calculator(entity, to_ts=1700500000)
# -> Finds valid snapshot at 2023-10-31
# -> Verifies fingerprint matches (COUNT, SUM, MAX)
# -> Restores calculator state from snapshot
# -> Only processes events from 2023-11-01 onwards
# -> Saves new snapshots at 2023-11-30

# If journal data changed (re-parse, manual edit):
calculator = cache.get_calculator(entity, to_ts=1700500000)
# -> Finds snapshot at 2023-10-31
# -> Fingerprint MISMATCH (data changed)
# -> Deletes snapshot at 2023-10-31 AND all future snapshots
# -> Falls back to processing from epoch
```

### Example 5: Report Excel Output Structure

```python
# ReportData maps to Excel sheets:
report = ReportData(
    final_summary=...,       # Sheet: "summary"
    bs_amt=...,              # Sheet: "balance_sheet_by_qty"
    bs_mkt=...,              # Sheet: "balance_sheet_by_value_USD"
    income=...,              # Sheet: "income_statement"
    period_flows_amt=...,    # Sheet: "flows_by_qty"
    period_flows_val=...,    # Sheet: "flows_by_value_USD"
    gains_data=...,          # Sheet: "realized_gains"
    open_lots=...,           # Sheet: "open_lots"
    flow_fmt=...,            # Sheet: "journal"
    src_dest_fmt=...,        # Sheet: "journal_flat" (optional)
    currency="USD",
    warnings=["..."],        # Sheet: "warnings"
    settings=...,            # Sheet: "settings"
    wallets=...,             # Sheet: "wallets"
)

# For VN, add:
#   "balance_sheet_by_value_VND" -- same as USD sheet but converted
#   "tax_summary" -- 0.1% transfer tax summary with exemptions
```

### Example 6: Vietnam-Specific Adaptations

Things the legacy code does NOT handle that CryptoTax VN needs:

```python
# 1. Dual currency valuation (USD + VND)
# Every split needs both:
split.value_usd = price_feed.get(symbol, timestamp, Currency.USD) * amount
split.value_vnd = price_feed.get(symbol, timestamp, Currency.VND) * amount
# Or: value_vnd = value_usd * usd_vnd_rate

# 2. Transfer tax (0.1% per transfer)
# For each taxable transfer:
tax = transfer_value_vnd * Decimal("0.001")
# Exemption check:
if transfer_value_vnd > Decimal("20_000_000"):  # > VND 20M
    tax = Decimal("0")  # Exempt

# 3. Annual filing with FIFO
# Must use GLOBAL_FIFO (not PER_WALLET)
gains_mode = GainsMode.GLOBAL_FIFO  # VN requires this

# 4. Report deadline: March 31 of following year
# Filing period: January 1 - December 31
```
