---
phase: 12-management-dashboard-comprehensive-analytics
plan: 04
subsystem: ui
tags: [react, recharts, tanstack-query, analytics, charts, typescript]

requires:
  - phase: 12-management-dashboard-comprehensive-analytics
    plan: 02
    provides: "Analytics API router (19 endpoints) + Pydantic response schemas"
  - phase: 12-management-dashboard-comprehensive-analytics
    plan: 03
    provides: "Shared filter components + DataTable + Pagination"

provides:
  - "Analytics TypeScript API client (analytics.ts) with 19 fetch functions and all response interfaces"
  - "TanStack Query hooks (useAnalytics.ts) for all 19 analytics endpoints with entity context"
  - "10 Recharts chart components + KPICard in web/src/components/charts/"
  - "Barrel export via web/src/components/charts/index.ts"
  - "Extended TransactionFilters, JournalFilters, and tax API with new filter params"

affects: [12-05, 12-06]

tech-stack:
  added: []
  patterns:
    - "analyticsPath() helper builds URL with filter query string + entityId injection"
    - "BalanceOverTimeChart groups BalancePeriod[] by symbol to build LineChart with one Line per symbol"
    - "CompositionDonut aggregates CompositionItem[] by account_type before rendering PieChart"
    - "ActivityHeatmap uses pure Tailwind CSS grid (52 cols x 7 rows) with intensity coloring"
    - "WinnersLosers uses two-column Tailwind layout (no Recharts)"

key-files:
  created:
    - web/src/api/analytics.ts
    - web/src/hooks/useAnalytics.ts
    - web/src/components/charts/CashFlowChart.tsx
    - web/src/components/charts/IncomeExpenseChart.tsx
    - web/src/components/charts/BalanceOverTimeChart.tsx
    - web/src/components/charts/CompositionDonut.tsx
    - web/src/components/charts/EntryTypeBar.tsx
    - web/src/components/charts/GainsLossChart.tsx
    - web/src/components/charts/HoldingDistribution.tsx
    - web/src/components/charts/WinnersLosers.tsx
    - web/src/components/charts/ActivityHeatmap.tsx
    - web/src/components/charts/KPICard.tsx
    - web/src/components/charts/index.ts
  modified:
    - web/src/api/transactions.ts
    - web/src/api/journal.ts
    - web/src/api/tax.ts

key-decisions:
  - "buildQueryString() skips undefined/null/empty values to keep URLs clean"
  - "BalanceOverTimeChart groups raw BalancePeriod[] into period->symbol map before building recharts data"
  - "CompositionDonut uses Math.abs() on balance_usd before aggregation so LIABILITY negatives don't cancel ASSET"
  - "ActivityHeatmap starts grid from Sunday of the earliest data point's week for consistent alignment"

requirements-completed: [ANAL-09, ANAL-10, ANAL-11]

duration: 15min
completed: 2026-02-22
---

# Phase 12 Plan 04: Chart Components & Analytics Hooks Summary

**Recharts chart library for all 11 analytics visualizations, TypeScript API client with 19 typed fetch functions, and TanStack Query hooks — all wired to the analytics backend from Plan 02**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-22T02:13:52Z
- **Completed:** 2026-02-22
- **Tasks:** 2
- **Files modified:** 16 (13 created, 3 modified)

## Accomplishments

- Created `web/src/api/analytics.ts` with `AnalyticsFilters` interface, 19 TypeScript response interfaces (KPISummary, CashFlowPeriod, SymbolVolume, ProtocolVolume, CompositionItem, ActivityDay, EntryTypeBreakdown, IncomeExpensePeriod, BalancePeriod, WalletFlow, ChainFlow, OverviewResponse, RealizedGainsPeriod, GainsBySymbol, HoldingBucket, WinnersLosers, TaxBreakdownPeriod, TaxByCategory, UnrealizedPosition, CostBasisItem), and 19 typed fetch functions using `apiFetch` + `withEntityId` + `analyticsPath()` helper
- Created `web/src/hooks/useAnalytics.ts` with 19 TanStack Query hooks (useOverview, useCashFlow, useIncomeExpense, useBalanceOverTime, useTopSymbols, useTopProtocols, useComposition, useActivity, useEntryTypes, useFlowByWallet, useFlowByChain, useGainsOverTime, useGainsBySymbol, useHoldingDistribution, useWinnersLosers, useTaxBreakdown, useTaxByCategory, useUnrealized, useCostBasis) — all use `useEntity()` for entityId in query keys
- Extended `TransactionFilters` in `transactions.ts` with `date_from`/`date_to`
- Extended `JournalFilters` in `journal.ts` with `date_from`, `date_to`, `symbol`, `account_type`, `wallet_id`, `protocol`, `account_subtype`
- Extended `tax.ts` with `RealizedGainsFilters` (symbol, date_from, date_to, gain_only, loss_only) and `OpenLotsFilters` (symbol, min_quantity)
- Created `CashFlowChart`: stacked BarChart (green=inflow, red=outflow) with ResponsiveContainer height=300
- Created `IncomeExpenseChart`: AreaChart with gradient fills (green=income, orange=expense)
- Created `BalanceOverTimeChart`: LineChart grouping BalancePeriod[] by symbol into multi-line chart with 8-color palette
- Created `CompositionDonut`: PieChart (donut) aggregating CompositionItem[] by account_type with fixed color coding
- Created `EntryTypeBar`: horizontal BarChart (layout="vertical") with color-coded bars per entry type
- Created `GainsLossChart`: ComposedChart with green gain bars, red loss bars, and blue net line overlay
- Created `HoldingDistribution`: BarChart colored green/red per bucket based on total_gain_usd sign
- Created `WinnersLosers`: Two-column pure Tailwind layout (no Recharts) with green winners / red losers lists
- Created `ActivityHeatmap`: Pure CSS grid 52 weeks x 7 days with intensity coloring (gray-50 to green-500) from volume percentile
- Created `KPICard`: Reusable stat card with label, large bold value, optional icon, and optional change indicator (green/red)
- Created `web/src/components/charts/index.ts`: barrel export for all 10 components

## Task Commits

Each task was committed atomically:

1. **Task 1: Create analytics API client and TanStack Query hooks** - `1f5bf89` (feat)
2. **Task 2: Create 10 Recharts chart components + KPICard** - `f1c644a` (feat)

## Files Created/Modified

- `web/src/api/analytics.ts` - Full analytics TypeScript client (19 interfaces + 19 fetch functions)
- `web/src/hooks/useAnalytics.ts` - 19 TanStack Query hooks with entity context
- `web/src/api/transactions.ts` - Extended TransactionFilters with date_from/date_to
- `web/src/api/journal.ts` - Extended JournalFilters with 7 new filter params
- `web/src/api/tax.ts` - Added RealizedGainsFilters + OpenLotsFilters interfaces and param passing
- `web/src/components/charts/CashFlowChart.tsx` - Stacked bar chart for cash flow periods
- `web/src/components/charts/IncomeExpenseChart.tsx` - Area chart for income vs expense
- `web/src/components/charts/BalanceOverTimeChart.tsx` - Multi-line chart per symbol
- `web/src/components/charts/CompositionDonut.tsx` - Donut chart aggregated by account type
- `web/src/components/charts/EntryTypeBar.tsx` - Horizontal bar chart for entry types
- `web/src/components/charts/GainsLossChart.tsx` - Composed chart for realized gains/losses
- `web/src/components/charts/HoldingDistribution.tsx` - Bar chart for holding period buckets
- `web/src/components/charts/WinnersLosers.tsx` - Two-column winners/losers list
- `web/src/components/charts/ActivityHeatmap.tsx` - CSS grid activity calendar
- `web/src/components/charts/KPICard.tsx` - Reusable KPI stat card
- `web/src/components/charts/index.ts` - Barrel export

## Decisions Made

- `buildQueryString()` in analytics.ts iterates `Object.entries(filters)` and skips any undefined/null/empty values — keeps URLs clean and avoids sending empty params
- `BalanceOverTimeChart` groups raw `BalancePeriod[]` into a period->symbol value map before rendering — Recharts needs one object per period with all symbol values as keys
- `CompositionDonut` uses `Math.abs(item.balance_usd)` before aggregation — LIABILITY balances are negative and would otherwise cancel ASSET balances, distorting the donut
- `ActivityHeatmap` walks back the start date to the previous Sunday for consistent week alignment regardless of which day of week the data starts on

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All chart components are ready for use in analytics pages (Plans 05-06)
- Clean barrel import: `import { CashFlowChart, KPICard, ActivityHeatmap } from '../components/charts'`
- All hooks provide loading/error state via TanStack Query for consistent UI handling
- Extended filter interfaces allow analytics pages to use full filter capability

## Self-Check: PASSED

- All 13 created files: FOUND (verified via Glob)
- TypeScript: zero errors (npx tsc --noEmit passed)
- Commit 1f5bf89: analytics API client + hooks
- Commit f1c644a: chart components + KPICard

---
*Phase: 12-management-dashboard-comprehensive-analytics*
*Completed: 2026-02-22*
