# Phase 2 Plan 01: Domain Models + Wallet Manager -- Summary

## One-liner
All core domain models (Entity, Wallet STI, Transaction, Account STI with 8 subtypes, JournalEntry+Splits), repository pattern, Wallets API CRUD, and frontend Wallets page with sync capability.

## What Was Built

### Backend
- **Entity model**: UUID, name, base_currency with soft delete support
- **Wallet model (STI)**: Base Wallet + OnChainWallet (chain, address, last_block_loaded) + CEXWallet (exchange, encrypted API keys)
- **Transaction model**: Full TX metadata (hash, block, from/to, value, gas, status, entry_type, tx_data JSON)
- **Account model (STI)**: 8 polymorphic subtypes — NativeAsset, ERC20Token, ProtocolAsset, ProtocolDebt, WalletIncome, WalletExpense, ExternalTransfer, ManualEntry
- **Journal models**: JournalEntry + JournalSplit with balance validation (splits sum to zero)
- **5 Repositories**: entity_repo, wallet_repo, transaction_repo, account_repo, journal_repo
- **Wallets API**: 6 endpoints (POST add, POST add-cex, GET list, GET detail, DELETE remove, POST sync)

### Frontend
- **Wallets.tsx**: Add on-chain + CEX wallet forms, wallet list with sync status badges, Sync Now and Delete buttons
- **Dashboard.tsx**: Wallet count summary card
- **API client + hook**: useWallets with TanStack Query

## Key Decisions
- Single-Table Inheritance for Wallet and Account (simpler queries, one table per hierarchy)
- UUID primary keys everywhere (not auto-increment)
- CEX wallet credentials encrypted at rest (AES-256)
- JournalSplit balance validation enforced: sum(quantity) = 0 per entry
- Repository pattern for all DB access (no direct session usage in API handlers)

## Files Created
~21 files across models, repos, API, schemas, frontend pages, and tests.
