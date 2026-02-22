---
phase: 12-management-dashboard-comprehensive-analytics
plan: 05
subsystem: ui
tags: [react, tailwind, filters, journal, transactions, tax, accounts, dashboard, analytics]

requires:
  - phase: 12-management-dashboard-comprehensive-analytics
    plan: 03
    provides: Reusable filter components (FilterBar, DateRangePicker, WalletSelector, etc.)
  - phase: 12-management-dashboard-comprehensive-analytics
    plan: 04
    provides: Chart components and analytics hooks (useCashFlow, useOverview, CashFlowChart)
provides:
  - Transactions page with date/wallet/chain filter controls
  - Journal page with 6 filters, VND column, balance indicator, URL drill-down
  - Tax page with symbol/direction/holding-days filters and analytics link
  - Accounts page with wallet/symbol/protocol/account-type filters + balance-at-date
  - Dashboard with mini CashFlowChart and View Analytics quick action
affects: [all-existing-pages, user-experience]

tech-stack:
  added: []
  patterns: [url-search-params-drill-down, client-side-filter-fallback, filter-hook-params]

key-files:
  created: []
  modified:
    - web/src/pages/Transactions.tsx
    - web/src/pages/Journal.tsx
    - web/src/pages/Tax.tsx
    - web/src/pages/Accounts.tsx
    - web/src/pages/Dashboard.tsx
    - web/src/hooks/useTax.ts
    - web/src/components/filters/ChainSelector.tsx

key-decisions:
  - "Journal URL drill-down uses useSearchParams — filters sync to URL so analytics pages can link with pre-set filters"
  - "Accounts filters applied client-side — avoids API changes for simple wallet/symbol/protocol/type filtering"
  - "Balance indicator in Journal computed from value_usd sum across splits (must be < $0.01 absolute)"
  - "ChainSelector values changed to lowercase to match API expectations (value/label separation)"
  - "Dashboard CashFlowChart wraps last6MonthsRange with granularity=month; falls back to empty state gracefully"

requirements-completed: [ANAL-12, ANAL-13]

duration: 15min
completed: 2026-02-22
---

# Phase 12 Plan 05: Page Enhancements — Filters, VND Column, Analytics Integration Summary

**5 existing pages upgraded with filter controls, VND data display, balance indicators, URL drill-down, and mini analytics chart**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-02-22
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

### Task 1: Transactions and Journal Page Filters
- **Transactions.tsx**: Added FilterBar wrapping DateRangePicker, WalletSelector (populated from useWallets hook), ChainSelector, and Status filter. Filter values merged into `activeFilters` passed to `useTransactions`. Reset handler clears all state.
- **Journal.tsx**: Added 6-filter FilterBar (DateRangePicker, WalletSelector, SymbolInput, EntryTypeSelector, AccountTypeSelector, ProtocolSelector). Added VND column to split detail view with `formatVnd` helper. Added per-entry balance indicator (CheckCircle/XCircle icons) computed from `value_usd` sum client-side. Added URL search params drill-down via `useSearchParams` — filters read from URL on mount, synced back on change via `useEffect`.

### Task 2: Tax, Accounts, Dashboard Enhancements
- **Tax.tsx**: Added per-tab filter section. Gains tab: SymbolInput, Gains/Losses/All toggle, min/max holding days range. Open lots tab: SymbolInput. Updated `useRealizedGains` and `useOpenLots` calls to pass filter objects. Added "View Tax Analytics" button navigating to `/tax/analytics`.
- **Accounts.tsx**: Added FilterBar with WalletSelector, SymbolInput, ProtocolSelector, AccountTypeSelector. Added "Balance at Date" date picker (client-side filtering via `allAccounts.filter()`). AccountHistoryModal enhanced with date range picker for history filtering (client-side).
- **Dashboard.tsx**: Imported `useCashFlow`, `useOverview`, `CashFlowChart`. Added mini CashFlowChart section (last 6 months, granularity=month) with graceful empty state. Updated stats to use `overviewData?.kpi.total_entries` with fallback. Added "View Analytics" quick action button.
- **useTax.ts**: Updated `useRealizedGains(filters)` and `useOpenLots(filters)` hooks to accept and pass filter arguments to API functions.

### Auto-fix: ChainSelector lowercase values
Fixed ChainSelector to use `{value, label}` pairs so option values are lowercase (matching API expectations) while labels remain capitalized for display.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add filters to Transactions and Journal pages** — feat(12-05): add date/wallet/chain filters to Transactions; add 6 filters + VND column + balance indicator + URL drill-down to Journal
2. **Task 2: Add filters to Tax/Accounts and mini chart to Dashboard** — feat(12-05): add symbol/gain-loss/holding filters to Tax; wallet/symbol/protocol filters + balance-at-date to Accounts; mini CashFlowChart to Dashboard

## Files Modified
- `web/src/pages/Transactions.tsx` — FilterBar with DateRangePicker, WalletSelector, ChainSelector, status filter
- `web/src/pages/Journal.tsx` — 6-filter FilterBar, VND column, balance indicator, URL search params drill-down
- `web/src/pages/Tax.tsx` — per-tab filter section, View Tax Analytics button, updated hook calls
- `web/src/pages/Accounts.tsx` — FilterBar with 4 filters, balance-at-date picker, history date range in modal
- `web/src/pages/Dashboard.tsx` — mini CashFlowChart (last 6 months), analytics KPI integration, View Analytics button
- `web/src/hooks/useTax.ts` — useRealizedGains and useOpenLots now accept filter params
- `web/src/components/filters/ChainSelector.tsx` — fixed value/label separation for API compatibility

## Decisions Made
- Journal URL drill-down reads `?entry_type=SWAP&symbol=ETH` from URL params and sets as initial filter state, enabling analytics pages to link directly with pre-set filters
- Accounts filtering is client-side (avoids API changes for simple property-based filtering on small datasets)
- Balance indicator uses `value_usd` sum (must be < $0.01 absolute) matching double-entry accounting invariant
- CashFlowChart gracefully shows "No data" empty state when analytics endpoint returns empty or fails

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ChainSelector option values were capitalized but API expects lowercase**
- **Found during:** Task 1
- **Issue:** ChainSelector from Plan 03 used capitalized chain names as both value and label (e.g., value="Ethereum"), but the backend API and existing transaction table use lowercase (e.g., chain="ethereum"). Sending "Ethereum" to the API would result in no filter match.
- **Fix:** Refactored ChainSelector to use `{value: 'ethereum', label: 'Ethereum'}` pairs, sending lowercase values to API while displaying capitalized labels.
- **Files modified:** `web/src/components/filters/ChainSelector.tsx`

## Issues Encountered
None beyond the auto-fixed ChainSelector bug.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 existing pages now have comprehensive filter controls
- Journal drill-down via URL params enables analytics-to-journal deep links
- Dashboard mini chart demonstrates analytics integration pattern for the full analytics page (plan 06)
- useTax hooks now accept filter params, ready for any further tax analytics integration

## Self-Check: PASSED (manual verification)

All 7 files written/modified:
- `web/src/pages/Transactions.tsx` — MODIFIED
- `web/src/pages/Journal.tsx` — MODIFIED
- `web/src/pages/Tax.tsx` — MODIFIED
- `web/src/pages/Accounts.tsx` — MODIFIED
- `web/src/pages/Dashboard.tsx` — MODIFIED
- `web/src/hooks/useTax.ts` — MODIFIED
- `web/src/components/filters/ChainSelector.tsx` — MODIFIED

---
*Phase: 12-management-dashboard-comprehensive-analytics*
*Completed: 2026-02-22*
