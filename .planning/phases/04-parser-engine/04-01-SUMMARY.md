# Phase 4 Plan 01: Parser Engine + Journal/Error Views -- Summary

## One-liner
Full parser engine with GenericEVM/GenericSwap parsers, ParserRegistry, Bookkeeper orchestrator, AccountMapper, plus 4 new frontend pages (Parser Debug, Journal, Accounts, Errors) and 13 new API endpoints.

## What Was Built

### Backend — Parser Engine
- **BaseParser**: Abstract class with can_parse/parse interface
- **GenericEVMParser** (Layer 1): Fallback parser handling gas fees + simple transfers
- **GenericSwapParser** (Layer 2): Detects A-to-B token pattern, creates balanced SWAP entries
- **ParserRegistry**: (chain, address) -> [protocol_parser, ...fallbacks] with build_default_registry()
- **Parser utilities**: TransactionContext, gas split helpers, transfer extraction (ERC20/native/NFT), wrap handler

### Backend — Accounting
- **Bookkeeper**: Orchestrates TX -> Parser -> AccountMapper -> JournalEntry, captures diagnostics, validates balance
- **AccountMapper**: Lazy get-or-create accounts by hierarchical label (native_asset, erc20_token, protocol_asset, etc.)
- **ParseErrorRecord**: Model for storing parse failures with error type, message, stack trace

### Backend — API (13 new endpoints)
- **/api/parse**: test parse, wallet re-parse, coverage stats, errors, unknown TXs
- **/api/journal**: list entries, entry detail with splits, unbalanced validation
- **/api/accounts**: tree view with balances, account history, reconciliation
- **/api/errors**: list by type, summary counts, retry, ignore, manual price entry

### Frontend (4 new pages)
- **ParserDebug.tsx**: Test parse by TX hash, parser selection display, journal splits preview, stats panel
- **Journal.tsx**: Paginated entries with expandable splits, color-coded by account type, balance check
- **Accounts.tsx**: Tree view grouped by ASSET/LIABILITY/INCOME/EXPENSE with balances
- **Errors.tsx**: Tabbed view (Parse Errors, Unknown, Missing Prices, Unbalanced), retry/ignore actions, summary bar

## Key Decisions
- Horizontal parser strategy: GenericEVM (60%) -> GenericSwap (80%) -> Protocol-specific (95%)
- Parser registry uses (chain, contract_address) as lookup key
- Bookkeeper creates journal entries atomically (parse + persist in one transaction)
- Account labels are hierarchical: `Ethereum:Wallet1:ERC20:USDC`
- Parse errors stored separately from transactions (not on TX model)

## Files Created
~38 files — the largest phase, establishing the core accounting pipeline.
