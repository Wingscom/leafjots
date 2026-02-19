# Phase 3 Plan 01: EVM Infrastructure + TX Viewer -- Summary

## One-liner
Blockchain infrastructure with rate-limited Etherscan client, EVM TX loader with reorg safety, Solana RPC support, Transactions API with pagination/filters, and frontend TX viewer with explorer links.

## What Was Built

### Backend
- **HTTP client**: Rate-limited with retry logic and exponential backoff (tenacity)
- **Etherscan client**: Multi-chain support (Etherscan, BSCScan, Polygonscan, Arbiscan) — get_tx_list, get_token_transfers, get_logs, get_contract_abi
- **EVM TX loader**: Fetches TXs from Etherscan, normalizes to Transaction model, tracks last_block_loaded, 50-block reorg safety margin
- **Solana support**: Helius RPC client + Solana TX loader
- **ChainTxLoader**: Abstract base class for chain-specific loaders
- **Transactions API**: 4 endpoints — list (paginated + filters), detail, events, transfers

### Frontend
- **Transactions.tsx**: Paginated TX list with filters (wallet, chain, status), expandable detail view showing raw TX data, decoded events, transfer list, block explorer links
- **explorer.ts**: URL generator for Etherscan/BSCScan/Polygonscan/Arbiscan/Solscan
- **Status badges**: Parsed/Unparsed/Error visual indicators

## Key Decisions
- Etherscan API for TX fetching (not direct RPC — faster, includes internal TXs)
- Reorg safety: always stay 50 blocks behind chain head
- Multi-chain from day 1: EVM chains + Solana
- TX data stored as JSON blob in tx_data column for flexibility
- Block explorer links per chain (not hardcoded to Etherscan)

## Files Created
~16 files across infra, API, frontend, and tests.
