# Phase 1 Plan 01: Foundation + Dashboard Shell -- Summary

## One-liner
Full project scaffold with config, DI, DB session, 12 domain enums, initial Alembic migration, FastAPI app, and React+Vite dashboard shell with sidebar navigation.

## What Was Built

### Backend
- **Config**: Pydantic Settings with DB, Redis, API keys, USD/VND rate
- **DI Container**: dependency-injector with Settings, engine, session_factory providers
- **Database**: Async SQLAlchemy 2.0 + asyncpg, Base with TimestampMixin and UUIDPrimaryKey
- **Enums**: 12 domain enum files covering AccountType, Chain, EntryType, Protocol, Tax rules, etc.
- **Alembic**: Initial migration creating 6 core tables (entities, wallets, transactions, accounts, journal_entries, journal_splits)
- **FastAPI**: App with CORS, health endpoint, deps.py for DB session injection
- **Exceptions**: Custom hierarchy (ParseError, PriceNotFoundError, BalanceError, etc.)

### Frontend
- **Vite + React 18** + TypeScript scaffold
- **Tailwind CSS** configuration
- **Layout.tsx**: Sidebar navigation with all planned page links
- **Dashboard.tsx**: Empty state home page
- **API client**: Fetch wrapper with base URL and error handling
- **Router**: react-router-dom with all route placeholders

### Infrastructure
- `docker-compose.yml`: PostgreSQL 16 + Redis 7
- `pyproject.toml`: All dependencies + dev tools (pytest, ruff)
- `.env.example`: Template for environment variables
- pytest + ruff configuration

## Key Decisions
- SQLAlchemy 2.0 async with asyncpg (not psycopg2)
- UUID primary keys throughout (not auto-increment)
- TimestampMixin for created_at/updated_at on all models
- dependency-injector for DI (not manual wiring)
- Tailwind CSS (not CSS modules or styled-components)
- TanStack Query for frontend data fetching

## Files Created
~30+ files across `src/cryptotax/`, `web/src/`, `tests/`, `alembic/`, and root config files.
