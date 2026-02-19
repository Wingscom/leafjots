# Data Model -- Distilled Reference

> Distilled from Pennyworks/ChainCPA legacy code (`legacy_code/v2/db/models/` and `legacy_code/v2/models/`).
> Source: ~421 Python files, ~50K LOC. Reconstructed from 1,712 VS Code screenshots.
> Many fields marked `[UNCLEAR]` in source -- noted where relevant.

---

## Table of Contents

1. [Patterns](#patterns)
2. [Core Models Overview](#core-models-overview)
3. [Entity Model](#entity-model)
4. [Wallet Model Hierarchy](#wallet-model-hierarchy)
5. [Account Model Hierarchy](#account-model-hierarchy)
6. [Transaction Model](#transaction-model)
7. [Journal Models (Entry + Split)](#journal-models-entry--split)
8. [Protocol Event Models](#protocol-event-models)
9. [Price Models](#price-models)
10. [Balance & Snapshot Models](#balance--snapshot-models)
11. [Support Models](#support-models)
12. [Key Relationships (ERD)](#key-relationships-erd)
13. [Domain Rules](#domain-rules)
14. [What to Port](#what-to-port)
15. [Clean Examples](#clean-examples)

---

## Patterns

### 1. SQLAlchemy 2.0 Mapped Columns (GOOD)

All models use the modern `Mapped[T]` + `mapped_column()` pattern. This gives type safety
and IDE autocomplete. CryptoTax should continue this.

```python
id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
```

### 2. Single-Table Inheritance with Polymorphism (GOOD, but complex)

Both `Wallet` and `Account` use STI (single-table inheritance) via SQLAlchemy's
`polymorphic_on` / `polymorphic_identity`. This allows querying all accounts in one table
while having subclass-specific behavior.

- `Wallet` base -> `OnChainWallet`, `ExchangeWallet`
- `Account` base -> 18+ subclasses (NativeAssetAccount, ERC20TokenAccount, ProtocolAssetAccount, etc.)

**Port decision:** The pattern is sound. However, 18+ Account subtypes is excessive for
CryptoTax Vietnam (DeFi-first). Reduce to ~8 core subtypes. See [What to Port](#what-to-port).

### 3. TimestampMixin (GOOD)

```python
class TimestampMixin:
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

Standard audit fields. Port as-is.

### 4. AuditMixin (GOOD for SaaS, SKIP for local)

Some models use `AuditMixin` (from `pylib.db.models`). This tracked created_by/updated_by
for multi-user SaaS. CryptoTax is single-user local -- skip AuditMixin, keep TimestampMixin.

### 5. UUID Primary Keys (GOOD)

All domain models use `UUID` PKs. Good for distributed systems and avoiding sequence conflicts.
Some operational models (Transaction, ProtocolEvent) use `BigInteger` autoincrement -- reasonable
for high-volume append-only tables.

### 6. Entity-Scoped Everything (GOOD)

Nearly every model has `entity_id` FK. Entity = one tax entity (person/company).
This multi-tenant pattern is essential -- a user may have multiple entities.

### 7. Scoped Session / Session Factory (BAD -- rewrite)

Legacy uses `scoped_session` (thread-local session). CryptoTax uses async SQLAlchemy,
so this must be rewritten with `async_sessionmaker`.

```python
# Legacy (BAD)
Session = scoped_session(session_factory)

# CryptoTax (GOOD)
async_session = async_sessionmaker(engine, class_=AsyncSession)
```

### 8. Helper Functions as Module-Level (BAD -- use Repository pattern)

Legacy has `helpers.py` and `tools.py` with functions like `get_entity_by_name()`,
`create_or_get_wallet()`. These are effectively repositories without the class structure.
CryptoTax should formalize as proper Repository classes.

### 9. No Base Model Class Captured

The `Base` declarative base and `TimestampMixin` definitions were NOT captured in screenshots.
CryptoTax must define these fresh.

---

## Core Models Overview

| Model | Table | PK Type | Entity-Scoped | Description |
|-------|-------|---------|---------------|-------------|
| **Entity** | `entity` | UUID | -- (IS entity) | Tax entity (person/company) |
| **Wallet** | `wallet` | UUID | Yes | Polymorphic: OnChainWallet, ExchangeWallet |
| **Account** | `account` | UUID | Yes | Polymorphic: 18+ subtypes for assets/liabilities/income/expense |
| **Transaction** | `transaction` | BigInt | Via wallet | On-chain transaction record |
| **JournalEntry** | `journal_entry` | UUID | Via splits | Double-entry journal header |
| **JournalSplit** | `journal_split` | UUID | Via account | Individual debit/credit line |
| **ProtocolEvent** | `protocol_event` | BigInt | Via wallet | DeFi protocol event (Aave deposit, etc.) |
| **AccountBalance** | `account_balance` | Composite | Via account | Balance snapshot at timestamp |
| **NftToken** | `nft_token` | UUID | No (global) | NFT token registry |
| **NftPrice** | `nft_price` | UUID | Via nft_token | NFT price at timestamp |
| **Pricer** | `pricer` | UUID | No (global) | Price source configuration |
| **ParseError/BookkeeperRun** | `bookkeeper_run` | UUID | Via entity | Parse error tracking |
| **WalletProtocolStatus** | `wallet_protocol_status` | UUID | Via wallet | Last-loaded block per protocol |
| **RawWalletSnapshot** | `raw_wallet_snapshot` | UUID | Via wallet | Raw API response storage |
| **ProcessedBalance** | `processed_balance` | UUID | Via account | Extracted balance from snapshots |
| **UserBalance** | `user_balance` | UUID | No | Protocol balance (supply/borrow) |
| **ExchangeChain** | `exchange` | UUID | Via entity | Exchange deposit address mapping |
| **Journal** | `journal` | UUID | Via entity | Reporting journal config (NOT journal entries) |
| **JournalReport** | `journal_report` | UUID | Via entity | Generated report metadata (S3 path) |
| **NavConfig/Nav** | `nav_config`/`nav` | UUID | Via entity | NAV calculation (fund accounting) |
| **AddressBookEntry** | `address_book` | UUID | Via entity | Named addresses for an entity |

---

## Entity Model

**File:** `legacy_code/v2/models/entity.py`
**Table:** `entity`

```python
class Entity(TimestampMixin, Base):
    __tablename__ = "entity"

    id: Mapped[UUID]                          # PK, uuid4
    name: Mapped[str]                         # String(50), unique, not null
    base_currency: Mapped[Currency]           # Enum, default=USD
    deleted_at: Mapped[Optional[datetime]]    # Soft delete

    # Relationships (one-to-many)
    accounts: List[Account]
    wallets: List[Wallet]                     # cascade delete-orphan
    address_book: List[AddressBookEntry]
    journal_reports: List[JournalReport]      # cascade delete-orphan
    nav_configs: List[NavConfig]              # cascade delete-orphan
    navs: List[Nav]                           # cascade delete-orphan
```

**For CryptoTax Vietnam:**
- `base_currency` should default to `VND` (or support dual `USD`+`VND`)
- NAV-related relationships (nav_configs, navs) can be dropped -- not needed for tax
- Keep soft delete (`deleted_at`) pattern

---

## Wallet Model Hierarchy

**File:** `legacy_code/v2/db/models/wallet.py`
**Table:** `wallet` (single-table inheritance)

```
Wallet (abstract base)
  |-- OnChainWallet (polymorphic_identity="on_chain")
  |-- ExchangeWallet (polymorphic_identity="exchange")
```

### Wallet (Base)
```python
class Wallet(Base):
    __tablename__ = "wallet"
    __mapper_args__ = {"polymorphic_abstract": True, "polymorphic_on": "type"}

    id: Mapped[UUID]                  # PK (labeled entity_id in source -- confusing)
    entity_id: Mapped[UUID]           # FK -> entity.id
    type: Mapped[str]                 # String(30), discriminator
    unique_key: Mapped[str]           # String(120), hashed identity
    description: Mapped[Optional[str]]

    entity: Mapped[Entity]            # relationship

    @classmethod
    def _hash_key(cls, st: str) -> str:
        return hashlib.sha256(st.encode()).hexdigest()
```

### OnChainWallet
```python
class OnChainWallet(Wallet):
    __mapper_args__ = {"polymorphic_identity": "on_chain"}

    chain: Mapped[str]                          # String(30), e.g. "ethereum"
    address: Mapped[str]                        # String(120), e.g. "0x..."
    last_block_loaded: Mapped[Optional[int]]    # Sync cursor

    # unique_key = sha256(f"{chain}:{address}")
```

### ExchangeWallet
```python
class ExchangeWallet(Wallet):
    __mapper_args__ = {"polymorphic_identity": "exchange"}

    exchange: Mapped[Exchange]                    # Enum
    external_id: Mapped[Optional[str]]            # String(120)
    last_cursor_loaded: Mapped[Optional[str]]     # String(200), pagination cursor

    # unique_key = sha256(f"{exchange}:{external_id}")
```

**For CryptoTax Vietnam:**
- `OnChainWallet` is the primary focus (DeFi-first)
- `ExchangeWallet` is NICE-TO-HAVE (Phase 9)
- `unique_key` hashing is a good dedup pattern -- port it
- Fix: `entity_id` as PK in source is confusing -- use separate `id` PK

---

## Account Model Hierarchy

**File:** `legacy_code/v2/models/account.py`
**Table:** `account` (single-table inheritance, 18+ subtypes)

### Account (Base)
```python
class Account(TimestampMixin, Base):
    __tablename__ = "account"

    id: Mapped[UUID]                              # PK
    entity_id: Mapped[UUID]                       # FK -> entity.id
    wallet_id: Mapped[Optional[UUID]]             # FK -> wallet.id (some subtypes only)
    account_type: Mapped[AccountType]             # Enum: ASSET|LIABILITY|INCOME|EXPENSE
    symbol: Mapped[Symbol]                        # Token symbol enum (ETH, USDC, etc.)
    category: Mapped[str]                         # String(20), polymorphic discriminator
    description: Mapped[Optional[str]]            # String(100), user label

    # Columns used by specific subtypes (all nullable, use_existing_column):
    token_address: Mapped[Optional[str]]          # For ERC20, NFT, Solana
    token_id: Mapped[Optional[str]]               # For NFT
    protocol: Mapped[Optional[Protocol]]          # For protocol accounts
    contract_address: Mapped[Optional[str]]       # For protocol accounts
    position_id: Mapped[Optional[str]]            # For protocol accounts
    tag: Mapped[Optional[str]]                    # For income/expense/equity
    external_address: Mapped[Optional[str]]       # For external transfers
    exchange: Mapped[Optional[Exchange]]           # For exchange accounts
    asset_id: Mapped[Optional[int]]               # For Algorand
    coin_type: Mapped[Optional[str]]              # For SUI
    chain: Mapped[Optional[str]]                  # For deprecated ExternalWalletAccount
    wallet_address: Mapped[Optional[str]]         # For deprecated ExternalWalletAccount

    # Key methods
    def unique_key(self) -> Tuple: ...            # Dedup identity (abstract)
    def auto_label(self) -> str: ...              # Human-readable label (abstract)
    def label(self) -> str: ...                   # description or auto_label
```

### Account Type Hierarchy

```
Account (abstract base, polymorphic_on="category")
  |
  |-- AssetAccount (abstract, account_type=ASSET)
  |     |-- NativeAssetAccount    ("native_asset")   -- e.g. ETH in wallet
  |     |-- ERC20TokenAccount     ("erc20_token")    -- e.g. USDC in wallet
  |     |-- NFTTokenAccount       ("nft_token")      -- NFT in wallet
  |     |-- SolanaTokenAccount    ("solana_token")
  |     |-- SuiAssetAccount       ("sui_asset")
  |     |-- StacksAssetAccount    ("stacks_asset")
  |     |-- AlgorandAssetAccount  ("algorand_asset")
  |     |-- ProtocolAssetAccount  ("protocol_asset") -- e.g. aUSDC in Aave
  |     |-- ExternalTransferAccount ("external_transfer")
  |     |-- ExchangeAccount       ("exchange")
  |     |-- ExchangeWalletAccount ("exchange_wallet")
  |     |-- BankAccount           ("bank")
  |     |-- UnknownAccount        ("unknown")
  |     |-- ExternalWalletAccount ("external_wallet") -- DEPRECATED
  |
  |-- LiabilityAccount (abstract, account_type=LIABILITY)
  |     |-- ProtocolDebtAccount   ("protocol_debt")  -- e.g. Aave borrow
  |     |-- EquityAccount         ("equity")
  |
  |-- IncomeAccount (abstract, account_type=INCOME)
  |     |-- WalletIncomeAccount   ("wallet_income")  -- e.g. yield, interest
  |     |-- InterestIncomeAccount ("interest_income") -- DEPRECATED
  |
  |-- ExpenseAccount (abstract, account_type=EXPENSE)
  |     |-- WalletExpenseAccount  ("wallet_expense") -- e.g. gas fees
  |     |-- GiftAccount           ("gift")
  |     |-- InterestExpenseAccount ("interest_expense") -- DEPRECATED
  |     |-- TransactionFeesAccount ("transaction_fees") -- DEPRECATED
  |
  |-- ManualEntryAccount ("manual_entry") -- any account_type, manual
```

### Account Naming Convention (auto_label)
```
NativeAssetAccount:     "{wallet.label}:Native"
ERC20TokenAccount:      "{wallet.label}:ERC20:{abbrev_address}"
ProtocolAssetAccount:   "{wallet.label}:Protocol:{protocol.label}:{contract}:{position}"
ProtocolDebtAccount:    "{wallet.label}:Protocol:{protocol.label}:{contract}:{position}"
WalletIncomeAccount:    "{wallet.label}:{tag}"
WalletExpenseAccount:   "{wallet.label}:{tag}"
ExternalTransferAccount: "{wallet.label}:External:{abbrev_address}"
ExchangeAccount:        "Exchange:{exchange.label}:{tag}"
```

### unique_key() -- Deduplication

Each subtype defines its own uniqueness tuple:
```python
NativeAssetAccount:     (category, wallet_id)
ERC20TokenAccount:      (category, wallet_id, token_address)
ProtocolAssetAccount:   (category, wallet_id, protocol, symbol, contract_address, position_id)
WalletIncomeAccount:    (category, wallet_id, symbol, tag)
```

**For CryptoTax Vietnam:**
- Reduce to ~8 subtypes: NativeAsset, ERC20Token, ProtocolAsset, ProtocolDebt,
  WalletIncome, WalletExpense, ExternalTransfer, ManualEntry
- Drop: Solana/SUI/Stacks/Algorand/Bank/NFT/Exchange accounts initially
- The `unique_key()` pattern is excellent for create-or-get semantics -- port it
- The `auto_label` pattern is excellent for human-readable account names -- port it
- `use_existing_column=True` for shared columns across subtypes is the correct STI pattern

---

## Transaction Model

**File:** `legacy_code/v2/db/models/transaction.py`
**Table:** `transaction`

```python
class Transaction(Base):
    __tablename__ = "transaction"
    __table_args__ = (
        UniqueConstraint("hash", "timestamp", name="transaction_wallet_id_hash_key"),
        Index("ix_transaction_journal_entry_id", "journal_entry_id"),
        Index("ix_transaction_call_stack_id", "call_stack_id"),
    )

    id: Mapped[int]                               # BigInteger PK, autoincrement
    wallet_id: Mapped[UUID]                       # FK -> wallet.id
    block_num: Mapped[Optional[int]]              # Block number
    hash: Mapped[str]                             # String(80), TX hash
    timestamp: Mapped[int]                        # Unix timestamp (Integer)
    call_stack_id: Mapped[Optional[str]]          # String(80), for internal TXs
    source: Mapped[Optional[str]]                 # String(40), data source
    transaction_type: Mapped[Optional[str]]       # String(40)
    tx_data: Mapped[Optional[dict]]               # JSON, raw TX data
    journal_entry_id: Mapped[Optional[UUID]]      # FK -> journal_entry.id (set after parsing)
    created_at: Mapped[Optional[datetime]]

    # Relationships
    journal_entry: Mapped[Optional[JournalEntry]]
    wallet: Mapped[Wallet]                        # viewonly
```

**Key observations:**
- `journal_entry_id` is nullable -- set to NULL until parsed, then linked to a JournalEntry
- `tx_data` stores the full raw TX as JSON (from, to, value, gas, logs, etc.)
- `call_stack_id` groups internal transactions within a single TX
- BigInteger PK for high-volume append-only data

**For CryptoTax Vietnam:**
- Port the structure mostly as-is
- Add `chain` column directly (legacy gets chain via wallet relationship -- inefficient for queries)
- Add `status` column (pending/parsed/error)
- Consider separating `tx_data` into typed columns for common fields (from_addr, to_addr, value, gas)
- Keep the JSON `tx_data` for raw/extra data

---

## Journal Models (Entry + Split)

**NOT fully reconstructed from screenshots.** Inferred from usage across codebase.

### JournalEntry (inferred schema)

**Table:** `journal_entry`

```python
class JournalEntry(Base):
    __tablename__ = "journal_entry"

    id: Mapped[UUID]                           # PK
    timestamp: Mapped[int]                     # Unix timestamp
    description: Mapped[str]                   # Human-readable ("Swap ETH->USDC")
    created_by: Mapped[Optional[str]]          # Parser/Bookkeeper class name
    created_at: Mapped[Optional[datetime]]
    manual_input: Mapped[bool]                 # Default False
    placeholder: Mapped[bool]                  # Default False (temporary entries)
    entry_type: Mapped[Optional[str]]          # Type classification

    # Relationships
    splits: Mapped[List[JournalSplit]]         # One-to-many, cascade
    transactions: Mapped[List[Transaction]]    # Back-reference from Transaction
```

**Evidence from code:**
- `bookkeeper.py` line 226: `JournalEntry(description=..., created_by=...)`
- `bookkeeper.py` line 264: `entry.splits = [JournalSplit(...), JournalSplit(...)]`
- `bookkeeper.py` line 297: `JournalEntry.manual_input.is_(True)`
- `tools.py` line 186: `JournalEntry.placeholder.is_(True)`
- `tools.py` line 195: `JournalEntry.timestamp >= ts`
- `tools.py` line 290: `selectinload(JournalEntry.splits).joinedload(JournalSplit.account)`

### JournalSplit (inferred schema)

**Table:** `journal_split`

```python
class JournalSplit(Base):
    __tablename__ = "journal_split"

    id: Mapped[UUID]                           # PK
    journal_entry_id: Mapped[UUID]             # FK -> journal_entry.id
    account_id: Mapped[UUID]                   # FK -> account.id
    amount: Mapped[Decimal]                    # Numeric(24,8), positive or negative
    value_in_currency: Mapped[Optional[Decimal]]  # Value in reporting currency
    currency: Mapped[Optional[str]]            # Reporting currency code
    memo: Mapped[Optional[str]]                # Optional note

    # Relationships
    journal_entry: Mapped[JournalEntry]
    account: Mapped[Account]
```

**Evidence from code:**
- `bookkeeper.py` line 265-278: JournalSplit constructed with account, amount, value_in_currency, currency, memo
- `tools.py` line 208: `JournalSplit.journal_entry_id == JournalEntry.id`
- `tools.py` line 211: `JournalSplit.account_id == account_id`
- `test_schemas.py`: Split(amount, value_in_currency, currency, symbol, auto_label)

### JournalAdjustment (referenced but not captured)

Referenced in `__init__.py` import but no source code available. Likely a model for
balance adjustments or corrections.

### Double-Entry Invariant

Every JournalEntry MUST have splits that sum to zero:

```
SUM(split.amount) across all splits in an entry = 0

Example: Swap 1 ETH -> 2500 USDC
  Split 1: account=ETH_asset,   amount=-1      (decrease ETH)
  Split 2: account=USDC_asset,  amount=+2500   (increase USDC)
  (Value in currency tracks USD/VND equivalent)
```

**For CryptoTax Vietnam:**
- This is THE most critical model -- port with care
- Add `value_usd` and `value_vnd` to JournalSplit (dual currency requirement)
- Add validation: `sum(splits.amount) == 0` at model level
- Keep `manual_input` flag for user corrections
- `placeholder` entries are for incomplete/estimated entries -- keep pattern

---

## Protocol Event Models

**File:** `legacy_code/v2/db/models/protocol_event.py`
**Table:** `protocol_event`, `protocol_event_status`

### ProtocolEvent
```python
class ProtocolEvent(Base):
    __tablename__ = "protocol_event"
    __table_args__ = (
        UniqueConstraint("wallet_id", "protocol", "contract_address", "timestamp", "event_name"),
    )

    id: Mapped[int]                               # BigInt PK
    wallet_id: Mapped[UUID]                       # FK -> wallet.id
    contract_address: Mapped[str]                 # String(80)
    event_name: Mapped[str]                       # String(80), e.g. "Deposit", "Swap"
    protocol: Mapped[str]                         # String(40), e.g. "aave_v3"
    timestamp: Mapped[int]                        # BigInt
    journal_entry_id: Mapped[Optional[UUID]]      # FK -> journal_entry.id

    journal_entry: Mapped[Optional[JournalEntry]]
    wallet: Mapped[OnChainWallet]
```

### ProtocolEventStatus
```python
class ProtocolEventStatus(Base):
    __tablename__ = "protocol_event_status"
    __table_args__ = (
        UniqueConstraint("wallet_id", "protocol", "contract_address", "event_name"),
    )

    id: Mapped[UUID]                   # PK
    wallet_id: Mapped[UUID]            # FK -> wallet.id
    contract_address: Mapped[str]      # String(80)
    event_name: Mapped[str]            # String(80)
    protocol: Mapped[Protocol]         # Enum
    last_loaded_to: Mapped[int]        # Block number cursor
```

**For CryptoTax Vietnam:**
- ProtocolEvent captures DeFi interactions separately from raw transactions
- Useful for event-driven parsing (Aave deposits, Uniswap swaps, etc.)
- Port the pattern but integrate more tightly with Transaction model
- ProtocolEventStatus tracks sync cursor per (wallet, protocol, contract, event) -- good pattern

---

## Price Models

### Pricer (price source config)

**File:** `legacy_code/v2/db/models/pricer.py`
**Table:** `pricer`

```python
class Pricer(Base, AuditMixin):
    __tablename__ = "pricer"

    id: Mapped[UUID]
    symbol: Mapped[str]                        # Token symbol
    class_name: Mapped[str]                    # Python class for pricing
    params: Mapped[Optional[dict]]             # JSON config
    asset_symbol: Mapped[Optional[Symbol]]     # Maps to canonical asset
```

**For CryptoTax Vietnam:**
- The concept of configurable price sources per token is good
- Simplify: use a price cache table instead of pricer class registry
- Price sources: CoinGecko, CryptoCompare, manual entry

### NftToken + NftPrice

**File:** `legacy_code/v2/db/models/nft_token.py`
**Table:** `nft_token`, `nft_price`

```python
class NftToken(TimestampMixin, Base):
    id: Mapped[UUID]
    address: Mapped[str]          # String(50)
    chain: Mapped[str]            # String(20)
    token_id: Mapped[str]         # String(80)
    symbol: Mapped[Symbol]

class NftPrice(TimestampMixin, Base):
    id: Mapped[UUID]
    nft_token_id: Mapped[UUID]    # FK -> nft_token.id
    timestamp: Mapped[int]        # BigInt
    currency: Mapped[Currency]
    source_id: Mapped[Optional[str]]
```

**For CryptoTax Vietnam:** Low priority. NFTs are not the DeFi focus.

---

## Balance & Snapshot Models

### AccountBalance

**File:** `legacy_code/v2/db/models/account_balance.py`
**Table:** `account_balance`

```python
class AccountBalance(TimestampMixin, Base):
    __tablename__ = "account_balance"

    account_id: Mapped[UUID]      # PK (composite), FK -> account.id
    timestamp: Mapped[int]        # PK (composite), BigInt
    balance: Mapped[Decimal]      # Numeric
    manual_input: Mapped[bool]    # Default False
```

Time-series balance snapshots per account. Composite PK (account_id, timestamp).
Used for reconciliation (journal balance vs on-chain balance).

### RawWalletSnapshot

**File:** `legacy_code/v2/db/models/raw_wallet_snapshot.py`
**Table:** `raw_wallet_snapshot`

```python
class RawWalletSnapshot(TimestampMixin, Base):
    id: Mapped[UUID]
    wallet_id: Mapped[UUID]                    # FK -> wallet.id
    source: Mapped[str]                        # String(100), e.g. "aave_v3_api"
    source_type: Mapped[str]                   # String(40)
    as_of_time: Mapped[datetime]               # Timestamp
    raw_data: Mapped[dict]                     # JSONB, full API response
    request_url: Mapped[Optional[str]]         # String(500)
    request_params: Mapped[Optional[dict]]     # JSONB
    processed: Mapped[bool]                    # Default False
    process_error: Mapped[Optional[str]]       # Text
    last_processed_at: Mapped[Optional[datetime]]
    polled_at: Mapped[Optional[datetime]]
```

Stores raw API responses for later reprocessing. Good pattern for audit trail.

### ProcessedBalance

**File:** `legacy_code/v2/db/models/processed_balance.py`
**Table:** `processed_balance`

```python
class ProcessedBalance(TimestampMixin, Base):
    id: Mapped[UUID]
    snapshot_id: Mapped[UUID]                  # FK -> raw_wallet_snapshot.id
    account_id: Mapped[UUID]                   # FK -> account.id
    balance_type: Mapped[str]                  # String(30), e.g. "supply", "borrow"
    as_of_time: Mapped[datetime]
    extra_metadata: Mapped[Optional[dict]]     # JSON
```

Extracted from RawWalletSnapshot. Maps raw data to accounts.

### UserBalance

**File:** `legacy_code/v2/db/models/user_balance.py`
**Table:** `user_balance`

```python
class UserBalance(TimestampMixin, Base):
    id: Mapped[UUID]
    chain: Mapped[str]                         # Enum
    address: Mapped[str]                       # String(120)
    protocol: Mapped[str]                      # Enum
    balance_type: Mapped[str]                  # Enum (supply, borrow, reward)
    token_address: Mapped[Optional[str]]
    token_symbol: Mapped[Optional[str]]
    contract_address: Mapped[Optional[str]]
    position_id: Mapped[Optional[str]]
    user_amount: Mapped[Decimal]               # Numeric(36,18)
    raw_value: Mapped[int]                     # BigInt (raw integer, no decimals)
    timestamp: Mapped[Optional[datetime]]
    created_by: Mapped[str]
```

**For CryptoTax Vietnam:**
- AccountBalance is essential for reconciliation -- port it
- RawWalletSnapshot is good for audit but heavy -- defer to Phase 8+
- ProcessedBalance and UserBalance can be simplified into AccountBalance

---

## Support Models

### WalletProtocolStatus

**File:** `legacy_code/v2/db/models/wallet_protocol_status.py`
**Table:** `wallet_protocol_status`

```python
class WalletProtocolStatus(TimestampMixin, Base):
    id: Mapped[UUID]
    wallet_id: Mapped[UUID]                    # FK -> wallet.id
    protocol: Mapped[Protocol]                 # Enum
    last_block_loaded: Mapped[Optional[int]]   # Sync cursor
    # Unique(wallet_id, protocol)
```

Tracks how far we've synced per wallet per protocol. Essential for incremental loading.

### ExchangeChain

**File:** `legacy_code/v2/db/models/exchange_chain.py`
**Table:** `exchange`

```python
class ExchangeChain(Base):
    id: Mapped[UUID]
    exchange: Mapped[str]          # Exchange name
    chain: Mapped[str]             # Enum
    address: Mapped[str]           # Deposit address on chain
    # Unique(chain, address)
```

Maps known exchange deposit addresses to exchange names. Useful for identifying
transfers to/from exchanges.

### AddressBookEntry

**File:** `legacy_code/v2/models/address_book.py`
**Table:** `address_book`

```python
class AddressBookEntry(TimestampMixin, Base):
    id: Mapped[UUID]
    entity_id: Mapped[UUID]        # FK -> entity.id
    address: Mapped[str]           # Blockchain address
    name: Mapped[str]              # String(80), human label
    # Unique(entity_id, address)
```

### BookkeeperRun + ParseError

**File:** `legacy_code/v2/db/models/parse_error.py`

```python
class BookkeeperRun(TimestampMixin, Base):
    __tablename__ = "bookkeeper_run"
    id: Mapped[UUID]
    entity_id: Mapped[UUID]
    user_label: Mapped[Optional[str]]

@dataclass
class ParseErrorDetail:
    run: BookkeeperRun
    parse_error: ParseError        # (model not fully captured)
    tx_timestamp: int
    tx_hash: str
    chain: str
    wallet_address: str
    placeholder: bool

    @property
    def tx_url(self) -> str: ...   # Link to block explorer
```

### ParseError Enum
```python
class ParseErrorEnum(str, Enum):
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
```

### JournalReport

**File:** `legacy_code/v2/db/models/journal_report.py`
**Table:** `journal_report`

```python
class JournalReport(Base, AuditMixin):
    id: Mapped[UUID]
    entity_id: Mapped[UUID]                    # FK -> entity.id
    bucket_name: Mapped[str]                   # S3 bucket
    s3_path: Mapped[str]                       # S3 key
    settings: Mapped[dict]                     # JSON, report config
    reporting_currency: Mapped[str]
    tax_year: Mapped[Optional[str]]
    task_official_workflow_run_id: Mapped[Optional[str]]
```

**For CryptoTax Vietnam:**
- Replace S3 storage with local file path (local-first)
- Keep the report metadata pattern (settings, tax_year, etc.)

---

## Key Relationships (ERD)

```
Entity (1) ----< (*) Wallet
Entity (1) ----< (*) Account
Entity (1) ----< (*) JournalReport
Entity (1) ----< (*) AddressBookEntry

Wallet (1) ----< (*) Transaction
Wallet (1) ----< (*) Account (some subtypes)
Wallet (1) ----< (*) ProtocolEvent
Wallet (1) ----< (*) WalletProtocolStatus
Wallet (1) ----< (*) RawWalletSnapshot

Transaction (*) >---- (0..1) JournalEntry
ProtocolEvent (*) >---- (0..1) JournalEntry

JournalEntry (1) ----< (*) JournalSplit
JournalSplit (*) >---- (1) Account

Account (1) ----< (*) AccountBalance
Account (1) ----< (*) ProcessedBalance
```

**Critical path:**
```
Entity -> Wallet -> Transaction -> (parser) -> JournalEntry -> JournalSplit -> Account
```

---

## Domain Rules

### 1. Double-Entry Accounting (NON-NEGOTIABLE)

Every JournalEntry must have splits summing to zero:
```
SUM(split.amount for split in entry.splits) == 0
```

Negative = decrease in account. Positive = increase in account.

### 2. Account Types

| Type | Debit (positive) | Credit (negative) | Example |
|------|------------------|-------------------|---------|
| ASSET | Increase | Decrease | Wallet ETH balance |
| LIABILITY | Decrease | Increase | Protocol debt (Aave borrow) |
| INCOME | Decrease | Increase | Interest earned |
| EXPENSE | Increase | Decrease | Gas fees |

### 3. FIFO Lot Matching (Vietnam tax law)

Capital gains calculated using FIFO. Lots created when assets acquired,
matched when sold/transferred.

### 4. Entity Isolation

All queries must be scoped to entity_id. One entity's data never mixes with another's.

### 5. Wallet-Scoped Accounts

Most accounts are tied to a specific wallet. This enables per-wallet balance tracking
and reconciliation against on-chain state.

### 6. Account Uniqueness

Each Account subtype defines `unique_key()` -- a tuple used for "create or get" semantics.
This prevents duplicate accounts and ensures idempotent parsing.

### 7. Transaction -> JournalEntry Linking

- Transaction starts with `journal_entry_id = NULL` (unparsed)
- Parser creates JournalEntry + JournalSplits
- Transaction.journal_entry_id set to the new entry
- This allows re-parsing: set journal_entry_id back to NULL, delete old entry, re-parse

### 8. Timestamp as Unix Integer

All timestamps are stored as Unix integers (seconds since epoch), NOT datetime objects.
This simplifies comparison and sorting. Convert to datetime only for display.

---

## What to Port

### [x] PORT -- Core patterns

- [x] **Entity model** -- tax entity, base_currency, soft delete
- [x] **Wallet STI** -- OnChainWallet (chain, address, last_block_loaded)
- [x] **Account STI** -- 4 base types (Asset, Liability, Income, Expense) with subtypes
- [x] **Account.unique_key()** -- dedup/idempotent create-or-get
- [x] **Account.auto_label** -- human-readable hierarchical names
- [x] **Transaction model** -- hash, block_num, timestamp, tx_data JSON, journal_entry_id FK
- [x] **JournalEntry + JournalSplit** -- double-entry journal with splits
- [x] **Double-entry invariant** -- SUM(splits) == 0
- [x] **ProtocolEvent** -- DeFi event tracking with journal_entry link
- [x] **WalletProtocolStatus** -- sync cursor per wallet per protocol
- [x] **AccountBalance** -- time-series balance snapshots
- [x] **ParseError tracking** -- error classification and retry support
- [x] **ParseErrorEnum** -- error type classification
- [x] **AddressBookEntry** -- named addresses per entity
- [x] **TimestampMixin** -- created_at, updated_at on all models
- [x] **UUID primary keys** -- for domain models
- [x] **BigInt PK** -- for high-volume Transaction/ProtocolEvent

### [x] PORT with modifications

- [x] **Account subtypes** -- reduce from 18+ to ~8 (drop Solana/SUI/Stacks/Algorand/Bank/Exchange)
- [x] **JournalSplit** -- add `value_usd` and `value_vnd` columns for dual currency
- [x] **Transaction** -- add `chain` column, add `status` column (pending/parsed/error)
- [x] **JournalReport** -- replace S3 with local file path
- [x] **Session management** -- rewrite from scoped_session to async_sessionmaker
- [x] **Helpers/tools** -- formalize as Repository pattern classes

### [ ] REWRITE

- [ ] **Session/DB infrastructure** -- async SQLAlchemy 2.0 from scratch
- [ ] **Capital gains** -- legacy is broken, rewrite FIFO engine completely
- [ ] **Pricer model** -- replace class_name registry with simpler price cache table
- [ ] **Journal model (db/models/journal.py)** -- this is a reporting config, not the journal entries. Confusing naming. Drop or rename.

### [ ] SKIP (not needed for CryptoTax Vietnam)

- [ ] NavConfig / Nav -- fund NAV calculation (not tax)
- [ ] RawWalletSnapshot / ProcessedBalance -- heavy audit trail, defer
- [ ] UserBalance -- redundant with AccountBalance
- [ ] ExchangeChain -- exchange address mapping (defer to CEX phase)
- [ ] ExchangeWallet -- CEX integration (Phase 9)
- [ ] AuditMixin -- multi-user SaaS pattern (CryptoTax is local single-user)
- [ ] NftToken / NftPrice -- NFT pricing (low priority)
- [ ] SolanaTokenAccount / SuiAssetAccount / StacksAssetAccount / AlgorandAssetAccount -- non-EVM chains (Phase 8)
- [ ] ExternalWalletAccount -- DEPRECATED in source
- [ ] InterestIncomeAccount / InterestExpenseAccount / TransactionFeesAccount -- DEPRECATED

---

## Clean Examples

### Example 1: Creating an Account (simplified for CryptoTax)

```python
# CryptoTax pattern -- inspired by legacy Account hierarchy
class Account(TimestampMixin, Base):
    __tablename__ = "account"
    __mapper_args__ = {"polymorphic_on": "category"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entity.id"), nullable=False)
    wallet_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("wallet.id"))
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)  # ASSET|LIABILITY|INCOME|EXPENSE
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(100))

    # Subtype-specific columns (nullable, shared table)
    token_address: Mapped[Optional[str]] = mapped_column(String(80))
    protocol: Mapped[Optional[str]] = mapped_column(String(40))
    contract_address: Mapped[Optional[str]] = mapped_column(String(120))
    tag: Mapped[Optional[str]] = mapped_column(String(100))

    def unique_key(self) -> tuple:
        raise NotImplementedError

    @property
    def auto_label(self) -> str:
        raise NotImplementedError
```

### Example 2: JournalEntry with Double-Entry Validation

```python
class JournalEntry(TimestampMixin, Base):
    __tablename__ = "journal_entry"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    entry_type: Mapped[Optional[str]] = mapped_column(String(40))
    created_by: Mapped[Optional[str]] = mapped_column(String(60))
    manual_input: Mapped[bool] = mapped_column(default=False)

    splits: Mapped[List["JournalSplit"]] = relationship(
        back_populates="journal_entry", cascade="all, delete-orphan"
    )

    def validate_balanced(self) -> bool:
        """Double-entry invariant: all splits must sum to zero."""
        total = sum(s.quantity for s in self.splits)
        return total == Decimal("0")


class JournalSplit(TimestampMixin, Base):
    __tablename__ = "journal_split"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    journal_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("journal_entry.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(ForeignKey("account.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    value_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    value_vnd: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 0))
    memo: Mapped[Optional[str]] = mapped_column(String(200))

    journal_entry: Mapped["JournalEntry"] = relationship(back_populates="splits")
    account: Mapped["Account"] = relationship()
```

### Example 3: Swap Journal Entry

```python
# Swap 1 ETH -> 2500 USDC on Uniswap
entry = JournalEntry(
    timestamp=1706000000,
    description="Swap 1 ETH -> 2500 USDC via Uniswap V3",
    entry_type="swap",
    created_by="GenericSwapParser",
)
entry.splits = [
    JournalSplit(
        account=eth_asset_account,     # NativeAssetAccount
        quantity=Decimal("-1.0"),       # Decrease ETH
        value_usd=Decimal("-2500.00"),
        value_vnd=Decimal("-62500000"),
    ),
    JournalSplit(
        account=usdc_asset_account,    # ERC20TokenAccount
        quantity=Decimal("2500.0"),     # Increase USDC
        value_usd=Decimal("2500.00"),
        value_vnd=Decimal("62500000"),
    ),
]
assert entry.validate_balanced()  # -1 + 2500 != 0 in qty, but balanced per-symbol
# Note: balance validation is PER SYMBOL, not across symbols
# The value_usd columns should balance: -2500 + 2500 = 0
```

### Example 4: Repository Pattern (replacing legacy helpers.py)

```python
# Replace legacy module-level functions with proper repositories
class WalletRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_chain_address(
        self, chain: str, address: str
    ) -> OnChainWallet | None:
        stmt = select(OnChainWallet).where(
            OnChainWallet.chain == chain,
            OnChainWallet.address == address.lower(),
        )
        return await self._session.scalar(stmt)

    async def create_or_get(
        self, entity_id: UUID, chain: str, address: str
    ) -> OnChainWallet:
        existing = await self.get_by_chain_address(chain, address)
        if existing:
            return existing
        wallet = OnChainWallet(
            entity_id=entity_id,
            chain=chain,
            address=address.lower(),
        )
        self._session.add(wallet)
        await self._session.flush()
        return wallet
```
