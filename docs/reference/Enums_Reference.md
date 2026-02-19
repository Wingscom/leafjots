# Enums -- Distilled Reference

> Source: `legacy_code/v2/enums/` (16 files), plus chain-specific enums in
> `legacy_code/v2/algorand/enums.py`, `legacy_code/v2/solana/enums.py`,
> `legacy_code/v2/capital_gains.py`, `legacy_code/v2/csv_loader.py`.
>
> External dependencies (source not in repo): `pylib.enums.chain.ChainEnum`,
> `pylib.enums.protocol.ProtocolEnum`, `pylib.enums.symbol.SymbolEnum`.

---

## Patterns -- Design Patterns, Why Good

### 1. `str, Enum` Mixin Everywhere
Every enum in the legacy codebase inherits `(str, Enum)`. This means enum values
serialize to plain strings in JSON, database columns, and log output without any
custom encoder. This is the correct pattern -- port it directly.

```python
class AccountType(str, Enum):
    ASSET = "ASSET"
```

### 2. Separation: Domain Enums vs CEX-Specific Enums
The legacy code cleanly separates:
- **Domain enums** (`AccountType`, `BalanceType`, `ParseErrorEnum`) -- used by the
  accounting core, parsers, and reports.
- **CEX-specific enums** (`OKX*`, `OneToken*`, `OTC*`, `Exchange`, `Binance*`,
  `Bitfinex*`, `Bybit*`, etc.) -- used only by CEX integration modules.

This is a good separation. CryptoTax Vietnam is DeFi-first, so the CEX enums are
NOT needed in the initial build.

### 3. Alias Pattern for External Enums
`Chain`, `Protocol`, and `Symbol` are imported from an external `pylib` package and
re-exported as aliases:

```python
# chain.py
from pylib.enums.chain import ChainEnum
Chain = ChainEnum

# protocol.py
from pylib.enums.protocol import ProtocolEnum
Protocol = ProtocolEnum

# symbol.py
from pylib.enums.symbol import SymbolEnum
Symbol = SymbolEnum
```

The actual enum values live in a shared `pylib` library (not present in
`legacy_code/`). We must define our own `Chain` and `Protocol` enums from scratch,
using the values observed across the codebase.

### 4. SQLAlchemy TypeDecorator for String-backed Enums
The `enums.py` file defines custom `TypeDecorator` classes (`ChainEnumType`,
`ProtocolEnumType`, `SymbolEnumType`, `ParseErrorEnumType`) that store enums as
strings in PostgreSQL, avoiding native DB enums. This means new enum values do NOT
require DB migrations.

```python
class ChainEnumType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return Chain(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Chain(value)
```

**Verdict:** Good pattern but we can simplify with SQLAlchemy 2.0's native string
enum support. Do NOT port these TypeDecorators; use `sa.String` columns with
Pydantic validation instead.

### 5. `__str__` Override
Most enums override `__str__` to return `self.value`. With `str, Enum` mixin this
is redundant in Python 3.11+, but harmless. We can omit it in the rewrite.

---

## Key Interfaces -- All Enum Classes

### TIER 1: Core Domain Enums (MUST PORT)

#### AccountType
```python
class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
```
- File: `enums/account.py`
- Used by: Bookkeeper, Journal splits, Reports, Balance sheets
- Fundamental to double-entry accounting. Every split references one of these four.

#### BalanceType
```python
class BalanceType(str, Enum):
    SUPPLY = "supply"
    BORROW = "borrow"
    REWARD = "reward"
```
- File: `enums/balance_type.py`
- Used by: DeFi protocol positions (Aave, Morpho, etc.)
- Distinguishes supply-side, borrow-side, and reward positions.

#### Chain
```python
# Alias: Chain = pylib.enums.chain.ChainEnum (StrEnum)
# Values observed across legacy codebase:
class Chain(str, Enum):
    # Major EVM chains
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    POLYGON = "polygon"
    BASE = "base"
    BSC = "bsc"
    AVALANCHE = "avalanche"
    MANTLE = "mantle"
    SCROLL = "scroll"
    SONIC = "sonic"
    BERACHAIN = "berachain"
    WORLDCHAIN = "worldchain"
    ETHERLINK = "etherlink"
    PLASMA = "plasma"
    PLUME = "plume"
    PSC = "psc"             # PulseChain or similar
    FLASHA = "flasha"       # [UNCLEAR] exact chain
    HYPEREUM = "hypereum"   # [UNCLEAR] exact chain

    # Non-EVM
    ALGORAND = "algorand"
    BITCOIN = "bitcoin"
    CARDANO = "cardano"
    SOLANA = "solana"
    SUI = "sui"
    STACKS = "stacks"
```
- File: `enums/chain.py` (alias to pylib)
- Used by: Wallets, Transactions, Parsers, Block Explorer routing, Price Feeds
- **NOTE:** Values are lowercase strings (StrEnum style). The case convention
  matters for API keys, RPC URLs, and block explorer routing.

#### Protocol
```python
# Alias: Protocol = pylib.enums.protocol.ProtocolEnum
# Values observed across ~50+ parser files:
class Protocol(str, Enum):
    NULL = "null"               # GenericParser fallback
    UNKNOWN = "unknown"         # Unclassified tokens

    # Lending/Borrowing
    AAVE_V2 = "aave_v2"
    AAVE_V3 = "aave_v3"
    AAVE_STAKE = "aave_stake"
    MORPHO = "morpho"
    COMPOUND = "compound"
    EULER = "euler"
    BENQI = "benqi"
    CLEARPOOL = "clearpool"
    MAPLE = "maple"
    FLUID = "fluid"
    FOLKS = "folks"
    FOLKS_FINANCE_V2 = "folks_finance_v2"
    SILO = "silo"
    AVANT = "avant"
    DOLOMITE = "dolomite"
    CONTANGO = "contango"
    BRACKET = "bracket"

    # DEX / AMM
    CURVE = "curve"
    CAMELOT = "camelot"
    CAMELOT_V3 = "camelot_v3"
    CHRONOS = "chronos"
    SUSHISWAP_V3 = "sushiswap_v3"
    SHADOW = "shadow"
    PHARAOH = "pharaoh"
    HYPERSWAP = "hyperswap"
    RAMSES_V3 = "ramses_v3"
    MAVERICK_V2 = "maverick_v2"
    DEEPBOOK = "deepbook"

    # Yield/Vaults
    CONVEX = "convex"
    BEEFY = "beefy"
    BORING_VAULT = "boring_vault"
    ETHENA = "ethena"
    ELIXIR = "elixir"
    HASHNOTE_VAULT = "hashnote_vault"
    HASHNOTE_PAUSER = "hashnote_pauser"
    PIREX = "pirex"
    TREVEE = "trevee"
    ALPINE = "alpine"
    TURBOS_LIQUID = "turbos_liquid"

    # NFT Lending
    NFTFI = "nftfi"
    ARCADE = "arcade"
    GONDI = "gondi"
    BENDDAO = "benddao"
    ZHARTA = "zharta"
    BLUR = "blur"

    # Other DeFi
    ENS = "ens"
    CRYPTOPUNKS = "cryptopunks"
    BLACKHOLE = "blackhole"
    BEX = "bex"
    BERAPAW = "berapaw"
    AUTONOMOUS = "autonomous"
    HEDRON = "hedron"
    ALADDIN_FX = "aladdin_fx"
    SCALLOP = "scallop"
    AFTERMATH = "aftermath"
    NAVI = "navi"
    BUCKET = "bucket"
    BLUEFIN = "bluefin"
    STASHED = "stashed"
    ENABLE_IP = "enable_ip"
    DINERO = "dinero"

    # Internal/Legacy
    AUGUST = "august"
    AUGUST_LEGACY = "august_legacy"
    FRACTAL = "fractal"
    MAIN = "main"           # [UNCLEAR] exact purpose
    PENDLE = "pendle"
    TERM_FINANCE = "term_finance"
```
- File: `enums/protocol.py` (alias to pylib)
- Used by: Every protocol-specific parser, Token maps, Risk calculators, NFT
  configs, Balance providers
- **NOTE:** This enum has 60+ values. Most are client-specific (Pennyworks
  managed assets across many protocols). CryptoTax Vietnam only needs a subset
  initially (see What to Port).

#### ParseErrorEnum
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
- File: `enums/parse_error.py`
- Used by: Parser engine, Error tracking, Dashboard error page
- Excellent categorization. Maps directly to our Error Dashboard tabs.

#### ScanProvider
```python
class ScanProvider(str, Enum):
    BLOCKSCOUT = "BLOCKSCOUT"
    ETHERSCAN = "ETHERSCAN"
    ROUTESCAN = "ROUTESCAN"
```
- File: `enums/scan.py`
- Used by: Block explorer API routing
- Has a mapping `CHAIN_TO_SCAN_PROVIDER` that maps `Chain -> ScanProvider`.
  Default is `ETHERSCAN` when chain not in map.

#### Currency
```python
class Currency(str, Enum):
    USD = "USD"
```
- File: `enums/currency.py`
- Used by: Capital gains calculator, Reports
- Single value in legacy. We need to add VND for Vietnam tax.

#### GainsMode
```python
class GainsMode(str, Enum):
    GLOBAL_FIFO = "GLOBAL_FIFO"
    PER_WALLET = "PER_WALLET"
```
- File: `capital_gains.py` (inline, not in enums/)
- Used by: `GainsCalculator`
- Vietnam law requires GLOBAL_FIFO. PER_WALLET kept as option.

#### TradeSide
```python
class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
```
- File: `capital_gains.py` (inline)
- Used by: `Trade` model, `GainsCalculator`

### TIER 2: Infrastructure Enums (PORT WITH MODIFICATIONS)

#### DataSource
```python
class DataSource(str, Enum):
    CRYPTONORTH = "CRYPTONORTH"
    ONETOKEN = "ONETOKEN"
    MANUAL = "MANUAL"
```
- File: `enums/data_source.py`
- Used by: Tracking where data came from
- Pennyworks-specific values. Rewrite for CryptoTax: `ONCHAIN`, `CSV_IMPORT`,
  `MANUAL`.

#### NavStatus
```python
class NavStatus(str, Enum):
    DRAFT = "DRAFT"
    FINAL = "FINAL"
```
- File: `enums/nav_status.py`
- Used by: NAV (Net Asset Value) reporting
- Fund management concept. May be useful for report status tracking.

#### ReportingFrequency
```python
class ReportingFrequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
```
- File: `enums/reporting_frequency.py`
- Used by: Report generation scheduling
- Vietnam tax is annual but this is useful for dashboards/charts.

#### PxTransactionType
```python
class PxTransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    INTEREST_PAYMENT = "INTEREST_PAYMENT"
    REDEMPTION = "REDEMPTION"
    FORFEIT = "FORFEIT"
```
- File: `csv_loader.py` (inline)
- Used by: CSV import for off-chain/private transactions
- Useful concept. Merge into a broader `EntryType` enum for the rewrite.

### TIER 3: Chain-Specific Enums (PORT SELECTIVELY)

#### SolanaAction
```python
class SolanaAction(str, Enum):
    CLOSE_ACCOUNT = "closeAccount"
    CREATE_ACCOUNT = "createAccount"
    MINT_TO = "mintTo"
    MINT_TO_COLLECTION_V1 = "mintToCollectionV1"
    MINT_V1 = "mintV1"
    PAY_TX_FEES = "pay_tx_fees"
    PURGE_ACCOUNT = "purgeAccount"
    TRANSFER = "transfer"
    TRANSFER_CHECKED = "transferChecked"
```
- File: `solana/enums.py`
- Used by: Solana transaction parser
- Port when adding Solana support (Phase 8).

#### Algorand TxType
```python
class TxType(str, Enum):
    PAYMENT = "pay"
    ASSET_TRANSFER = "axfer"
    APPLICATION = "appl"
```
- File: `algorand/enums.py`
- Used by: Algorand transaction parser
- Low priority. Algorand not in initial roadmap.

### TIER 4: CEX-Specific Enums (DO NOT PORT)

#### Exchange
```python
class Exchange(str, Enum):
    # 30+ CEX values: BINANCE, BITFINEX, BYBIT, COINBASE, DERIBIT, FTX, KRAKEN, OKX, ...
    # 30+ Bridge values: ACROSS_BRIDGE, ARBITRUM_BRIDGE, WORMHOLE_BRIDGE, ...
    # Has a @property label for display names
```
- File: `enums/exchange.py`
- **DO NOT PORT.** This is a Pennyworks concept mixing CEX accounts with bridge
  protocols. Our architecture separates these concerns:
  - Chain enum handles blockchain identity
  - Protocol enum handles DeFi protocol identity
  - Bridge detection is a parser concern, not an enum

#### OKX Enums (5 classes)
```
OKXAccountType, OKXDepositWithdrawalType, OKXFundingAction,
OKXTradeAction, OKXTradeTradeType
```
- File: `enums/okx.py`
- **DO NOT PORT.** OKX CEX integration not needed.

#### OneToken Enums (7 classes)
```
OneTokenAccountType, OneTokenLedgerBusinessType,
OneTokenDepositWithdrawalBusinessType, OneTokenEarnBusinessType,
OneTokenTradeExecType, OneTokenTradeInstrument, OneTokenTradeSide
```
- File: `enums/onetoken.py`
- **DO NOT PORT.** 1Token is a Pennyworks data provider.

#### OTCTradeAction
```python
class OTCTradeAction(str, Enum):
    BUY = "Buy"
    SELL = "Sell"
```
- File: `enums/otc.py`
- **DO NOT PORT.** OTC desk integration not needed.

#### Binance/Bitfinex/Bybit/Coinbase/Deribit Enums (20+ classes)
Referenced in `enums.py` import from `exchange_enums` (file not in legacy_code/).
```
BinanceDepositWithdrawalStatus, BinanceTransferType, BinanceTradeOrderType,
BinanceTradeOrderSide, BinanceUSDMPaymentType, BitfinexDepositWithdrawalStatus,
BitfinexPaymentTransferStatus, BitfinexLedgerCurrency, BitfinexLedgerWalletType,
BitfinexMovement, BitfinexTradeOrderType, BitfinexTradeOrderSide,
CoinbaseDepositType, CoinbaseTradeProductType, CoinbaseTradeOrderSide,
CoinbaseTradeLiquidity, DeribitBlockTradeRoleType, DeribitDepositWithdrawalState,
DeribitDepositWithdrawalType, DeribitLedgerType, DeribitTradeLiquidity,
DeribitTradeOrderSide, DeribitTradeDirection, BybitWithdrawalStatus,
BybitTransferType, BybitTransferStatus, BybitTradeOrderType,
BybitTradeOrderSide, BybitTradeLiquidity
```
- **DO NOT PORT.** All CEX-specific.

### TIER 5: Supporting Enums in enums.py (REWRITE)

#### SQLAlchemy Enum Bindings
```python
enum_account_type = sa.Enum(AccountType, name="enum_account_type")
enum_exchange = sa.Enum(Exchange, name="enum_exchange", native_enum=False, length=30)
enum_data_source = sa.Enum(DataSource, ...)
enum_reporting_frequency = sa.Enum(ReportingFrequency, ...)
enum_chain = ChainEnumType(20)           # custom TypeDecorator
enum_parse_error = ParseErrorEnumType()  # custom TypeDecorator
enum_protocol = ProtocolEnumType(20)     # custom TypeDecorator
enum_symbol = SymbolEnumType(50)         # custom TypeDecorator
```
- File: `enums/enums.py`
- **REWRITE.** Use SQLAlchemy 2.0 `mapped_column(String)` with Pydantic
  validation instead. Simpler, no custom TypeDecorators needed.

#### Exchange Mapping Dicts
```python
EXCHANGE_CLASS_TO_EXCHANGE_ENUM = { ... }
EXCHANGE_ENUM_TO_EXCHANGE_NAME = { ... }
account_type_mappings = { ... }
primary_key_mappings = { ... }
NEW_CEX_COLUMNS_TO_DATABASE_COLS = { ... }
```
- **DO NOT PORT.** CEX-specific data mappings.

---

## Domain Rules -- Business/Accounting Rules Encoded in Enums

1. **Four account types only:** ASSET, LIABILITY, INCOME, EXPENSE. This is
   standard double-entry. Every journal split must reference exactly one of these.

2. **DeFi positions have three balance types:** SUPPLY (deposited), BORROW
   (borrowed), REWARD (earned). These map to AccountType as:
   - SUPPLY -> ASSET (protocol deposit)
   - BORROW -> LIABILITY (debt)
   - REWARD -> INCOME (yield earned)

3. **Parse errors are categorized for actionability:**
   - `TxParseError` / `InternalParseError` -> bugs to fix
   - `HandlerParseError` / `UnhandledFunctionError` -> need new handler
   - `UnknownChainError` / `UnknownContractError` -> need new chain/contract support
   - `UnknownTokenError` -> token registry gap
   - `UnsupportedEventsError` -> need event handler
   - `MissingPriceError` -> price feed gap (user can enter manually)

4. **Chain determines scan provider:** Default is Etherscan API; some chains use
   Blockscout or Routescan. This routing belongs in infra config, not enums.

5. **Capital gains mode:** Vietnam requires GLOBAL_FIFO per entity. PER_WALLET is
   an alternative for other jurisdictions.

6. **Currency is USD-only in legacy.** Vietnam needs dual: USD + VND.

---

## What to Port

### PORT DIRECTLY (copy values, update style)

- [x] `AccountType` -- ASSET, LIABILITY, INCOME, EXPENSE. No changes needed.
- [x] `BalanceType` -- SUPPLY, BORROW, REWARD. No changes needed.
- [x] `ParseErrorEnum` -- All 10 values. Consider renaming to `ParseError` and
      adding `BALANCE_ERROR` for unbalanced journal entries.
- [x] `ScanProvider` -- BLOCKSCOUT, ETHERSCAN, ROUTESCAN. No changes needed.
- [x] `TradeSide` -- BUY, SELL. No changes needed.
- [x] `GainsMode` -- GLOBAL_FIFO, PER_WALLET. No changes needed.
- [x] `ReportingFrequency` -- All 5 values. No changes needed.

### REWRITE (keep concept, change values)

- [ ] `Chain` -- Define our own with EVM chains only for Phase 1-7. Add Solana
      in Phase 8. Use UPPERCASE values to match our convention. Start with:
      `ETHEREUM, ARBITRUM, OPTIMISM, POLYGON, BASE, BSC, AVALANCHE`.
- [ ] `Protocol` -- Define our own with only Phase 5 protocols:
      `AAVE_V3, UNISWAP_V3, PANCAKESWAP, CURVE`. Add more as parsers are built.
      Include `UNKNOWN` and `GENERIC` as defaults.
- [ ] `Currency` -- Add VND: `USD, VND`. These are the dual reporting currencies
      required by Vietnam tax law.
- [ ] `DataSource` -- Replace with: `ONCHAIN, CSV_IMPORT, MANUAL`.
- [ ] `NavStatus` -- Rename to `ReportStatus`: `DRAFT, FINAL, GENERATING`.

### NEW ENUMS TO CREATE (not in legacy)

- [ ] `EntryType` -- Journal entry classification. Legacy uses free-form strings
      for `entry_type`. We should formalize:
      ```python
      class EntryType(str, Enum):
          SWAP = "SWAP"
          TRANSFER = "TRANSFER"
          DEPOSIT = "DEPOSIT"         # DeFi protocol deposit
          WITHDRAWAL = "WITHDRAWAL"   # DeFi protocol withdrawal
          BORROW = "BORROW"
          REPAY = "REPAY"
          LIQUIDATION = "LIQUIDATION"
          YIELD = "YIELD"             # Interest, rewards
          GAS_FEE = "GAS_FEE"
          MINT = "MINT"
          BURN = "BURN"
          BRIDGE = "BRIDGE"
          APPROVAL = "APPROVAL"       # No accounting impact, tracking only
          UNKNOWN = "UNKNOWN"
      ```

- [ ] `TxStatus` -- Transaction processing status:
      ```python
      class TxStatus(str, Enum):
          LOADED = "LOADED"           # Raw TX loaded from chain
          PARSED = "PARSED"           # Successfully parsed
          ERROR = "ERROR"             # Parse failed
          IGNORED = "IGNORED"         # Manually marked as irrelevant
      ```

- [ ] `WalletSyncStatus` -- Wallet sync state:
      ```python
      class WalletSyncStatus(str, Enum):
          IDLE = "IDLE"
          SYNCING = "SYNCING"
          SYNCED = "SYNCED"
          ERROR = "ERROR"
      ```

- [ ] `TaxExemptionReason` -- Why a transfer is tax-exempt:
      ```python
      class TaxExemptionReason(str, Enum):
          BELOW_THRESHOLD = "BELOW_THRESHOLD"    # Single TX > VND 20M
          SELF_TRANSFER = "SELF_TRANSFER"         # Between own wallets
          GAS_FEE = "GAS_FEE"                     # Gas is expense, not transfer
      ```

### DO NOT PORT

- [ ] `Exchange` -- 60+ values mixing CEX and bridges. Not needed for DeFi-first.
- [ ] `OKX*` (5 enums) -- CEX-specific.
- [ ] `OneToken*` (7 enums) -- Data provider-specific.
- [ ] `OTCTradeAction` -- OTC desk.
- [ ] `Binance*/Bitfinex*/Bybit*/Coinbase*/Deribit*` (20+ enums) -- CEX-specific.
- [ ] `Symbol` -- Token symbols should be dynamic strings, not an enum. The legacy
      `SymbolEnum` from pylib tried to enumerate all tokens, which is not scalable.
      Use a `Token` domain model with `symbol: str` instead.
- [ ] `PxTransactionType` -- Absorbed into `EntryType`.
- [ ] `Algorand TxType` -- Not in roadmap.
- [ ] SQLAlchemy `TypeDecorator` classes -- Use SQLAlchemy 2.0 patterns instead.
- [ ] Exchange mapping dicts -- CEX-specific data.

---

## Clean Examples

### Recommended Enum Module Structure for CryptoTax Vietnam

```
src/cryptotax/domain/enums/
    __init__.py          # Re-exports all enums
    account.py           # AccountType
    chain.py             # Chain
    protocol.py          # Protocol
    entry_type.py        # EntryType (NEW)
    balance_type.py      # BalanceType
    parse_error.py       # ParseError
    tax.py               # GainsMode, TradeSide, TaxExemptionReason (NEW)
    currency.py          # Currency (USD + VND)
    status.py            # TxStatus, WalletSyncStatus, ReportStatus (NEW)
    scan.py              # ScanProvider
    reporting.py         # ReportingFrequency
    data_source.py       # DataSource
```

### Example: account.py
```python
from enum import Enum


class AccountType(str, Enum):
    """Four fundamental account types for double-entry bookkeeping.

    Rules:
    - Every journal split references exactly one AccountType
    - ASSET + EXPENSE are debit-normal (positive = increase)
    - LIABILITY + INCOME are credit-normal (negative = increase)
    - Sum of all splits in a journal entry MUST equal zero
    """

    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
```

### Example: chain.py
```python
from enum import Enum


class Chain(str, Enum):
    """Supported blockchain networks.

    Values are lowercase to match RPC/API conventions.
    Add new chains as support is implemented.
    """

    # Phase 1-7: EVM chains
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    POLYGON = "polygon"
    BASE = "base"
    BSC = "bsc"
    AVALANCHE = "avalanche"

    # Phase 8: Non-EVM
    # SOLANA = "solana"
```

### Example: entry_type.py (NEW -- does not exist in legacy)
```python
from enum import Enum


class EntryType(str, Enum):
    """Classification of journal entries by DeFi operation type.

    Legacy used free-form strings for entry_type in journal entries.
    We formalize these for filtering, reporting, and tax calculation.
    """

    SWAP = "SWAP"
    TRANSFER = "TRANSFER"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BORROW = "BORROW"
    REPAY = "REPAY"
    LIQUIDATION = "LIQUIDATION"
    YIELD = "YIELD"
    GAS_FEE = "GAS_FEE"
    MINT = "MINT"
    BURN = "BURN"
    BRIDGE = "BRIDGE"
    APPROVAL = "APPROVAL"
    UNKNOWN = "UNKNOWN"
```

### Example: currency.py (REWRITTEN for Vietnam)
```python
from enum import Enum


class Currency(str, Enum):
    """Reporting currencies. Vietnam tax requires dual USD + VND reporting."""

    USD = "USD"
    VND = "VND"
```

### Example: parse_error.py
```python
from enum import Enum


class ParseError(str, Enum):
    """Categorized parse errors for the Error Dashboard.

    Each category maps to a user action:
    - TX_PARSE / INTERNAL_PARSE: Bug report (developer fixes)
    - HANDLER / UNHANDLED_FUNCTION: Need new parser handler
    - UNKNOWN_CHAIN / UNKNOWN_CONTRACT: Need new chain/contract support
    - UNKNOWN_TOKEN: Token registry gap (auto-resolve or manual)
    - UNSUPPORTED_EVENTS: Need event handler
    - MISSING_PRICE: User can enter manual price
    - BALANCE_ERROR: Journal entry doesn't balance (sum != 0)
    """

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
    BALANCE_ERROR = "BalanceError"  # NEW: journal entry unbalanced
```

---

## Summary Statistics

| Category | Legacy Count | Port | Rewrite | New | Skip |
|----------|-------------|------|---------|-----|------|
| Core Domain | 7 enums | 5 | 2 | 0 | 0 |
| Infrastructure | 5 enums | 1 | 4 | 0 | 0 |
| Chain-specific | 2 enums | 0 | 0 | 0 | 2 (later) |
| CEX-specific | 33+ enums | 0 | 0 | 0 | 33+ |
| New for CryptoTax | -- | 0 | 0 | 4 | 0 |
| **Total** | **47+** | **6** | **6** | **4** | **35+** |

Approximately 87% of legacy enums are CEX-related and not needed for DeFi-first.
The core accounting enums (AccountType, BalanceType, ParseErrorEnum) are clean and
can be ported with minimal changes.
