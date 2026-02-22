---
phase: 12-management-dashboard-comprehensive-analytics
plan: 06
subsystem: ui
tags: [react, tailwind, analytics, dashboard, charts, routing, navigation]

requires:
  - phase: 12-management-dashboard-comprehensive-analytics
    plan: 04
    provides: Chart components (CashFlowChart, CompositionDonut, EntryTypeBar, GainsLossChart, HoldingDistribution, WinnersLosers, ActivityHeatmap, KPICard) and analytics hooks
  - phase: 12-management-dashboard-comprehensive-analytics
    plan: 05
    provides: Page enhancements with filter components, Journal URL drill-down via useSearchParams

provides:
  - Analytics page at /analytics — full management dashboard with 8+ chart/table sections
  - TaxAnalytics page at /tax/analytics — tax-focused dashboard with 8+ sections
  - AIInsight.tsx placeholder component for future AI features
  - Updated App.tsx with routes for /analytics and /tax/analytics
  - Updated Layout.tsx sidebar with 13 nav items including Analytics and Tax Analytics

affects: [routing, navigation, analytics-ui]

tech-stack:
  added: []
  patterns: [section-level-loading-skeleton, section-level-error-retry, drill-down-navigate, navlink-end-flag]

key-files:
  created:
    - web/src/pages/Analytics.tsx
    - web/src/pages/TaxAnalytics.tsx
    - web/src/components/AIInsight.tsx
  modified:
    - web/src/App.tsx
    - web/src/components/Layout.tsx

key-decisions:
  - "AnalyticsFilters imported from api/analytics (not hooks/useAnalytics which does not re-export it)"
  - "NavLink end=true added to /, /analytics, /tax items to prevent parent path matching child routes"
  - "Per-section loading skeletons and error states with retry buttons — each chart section independent"
  - "AIInsight uses _context and _data prefixed params to satisfy TypeScript unused-param without removing public interface"

requirements-completed: [ANAL-14, ANAL-15, ANAL-16]

duration: 12min
completed: 2026-02-22
---

# Phase 12 Plan 06: Analytics Dashboards and AI Insight Placeholder Summary

**Full management analytics dashboard and tax analytics dashboard pages wiring together all chart components, hooks, and filter components built in previous plans**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-02-22
- **Tasks:** 2
- **Files created:** 3
- **Files modified:** 2

## Accomplishments

### Task 1: Create Analytics and TaxAnalytics pages

**Analytics.tsx** — Full management dashboard at `/analytics`:
- FilterBar: DateRangePicker, WalletSelector (populated from useWallets), ChainSelector, GranularitySelector
- 4 KPI cards: Total Inflow, Total Outflow, Net Flow, Unique Tokens (from useOverview)
- 2-column grid: CashFlowChart (left) + CompositionDonut (right)
- 2-column grid: IncomeExpenseChart (left) + EntryTypeBar (right)
- Full-width DataTable: Top Symbols (click row → navigate to /journal?symbol=X)
- 2-column grid: Top Protocols DataTable + Flow by Wallet DataTable
- Full-width ActivityHeatmap
- Per-section loading skeletons (animate-pulse) and error states with Retry button

**TaxAnalytics.tsx** — Tax analytics dashboard at `/tax/analytics`:
- Back to Tax button (navigate to /tax)
- FilterBar: DateRangePicker, SymbolInput, GranularitySelector
- 4 KPI cards: Total Gains, Total Losses, Net Gain, Tax Due (VND) — computed from hook data
- Full-width GainsLossChart (realized gains over time)
- 2-column grid: Gains by Symbol DataTable (click row → /journal?symbol=X) + HoldingDistribution
- Full-width WinnersLosers component
- 2-column grid: Tax Breakdown by Period DataTable + Tax by Category DataTable
- Full-width Unrealized P&L DataTable (open lots)
- Full-width Cost Basis Detail DataTable

### Task 2: Create AIInsight placeholder, update routes and navigation

**AIInsight.tsx** — Placeholder component:
- Sparkles icon from lucide-react
- "AI Insights" title with "Coming soon..." message
- Disabled "Generate Insight" button
- Purple-to-blue gradient card styling (opacity-75)

**App.tsx** — Added two routes:
- `<Route path="/analytics" element={<Analytics />} />`
- `<Route path="/tax/analytics" element={<TaxAnalytics />} />`

**Layout.tsx** — Updated sidebar navigation to 13 items:
- Analytics (BarChart3 icon) inserted after Errors
- Tax Analytics (TrendingUp icon) inserted after Tax
- Added `end` prop to NavLink: `end=true` for /, /analytics, /tax to prevent parent-path active highlight when on child routes

## Task Commits

1. **Task 1: Create Analytics and TaxAnalytics dashboard pages** — `471b936`
   - `feat(12-06): create Analytics and TaxAnalytics dashboard pages`
2. **Task 2: Add AIInsight placeholder, register routes, update sidebar nav** — `cb45683`
   - `feat(12-06): add AIInsight placeholder, register routes, update sidebar nav`

## Files Created
- `web/src/pages/Analytics.tsx` — Full management analytics dashboard (374 lines)
- `web/src/pages/TaxAnalytics.tsx` — Tax analytics dashboard (416 lines)
- `web/src/components/AIInsight.tsx` — AI insight placeholder (28 lines)

## Files Modified
- `web/src/App.tsx` — Added Analytics and TaxAnalytics imports + 2 routes
- `web/src/components/Layout.tsx` — Added BarChart3/TrendingUp icons + 2 nav items + end props

## Verification

- `npx tsc --noEmit` — PASSED (0 errors)
- `npm run build` — PASSED (build successful)
- Routes /analytics and /tax/analytics registered in App.tsx
- Layout sidebar shows 13 nav items including Analytics and Tax Analytics
- AIInsight component renders without errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AnalyticsFilters not exported from useAnalytics.ts**
- **Found during:** Task 1 verification (tsc --noEmit)
- **Issue:** Plan specified `import type { AnalyticsFilters } from '../hooks/useAnalytics'` but the hook file imports AnalyticsFilters from api/analytics and uses it internally — it is NOT re-exported. TypeScript error TS2459.
- **Fix:** Changed both Analytics.tsx and TaxAnalytics.tsx to import `AnalyticsFilters` directly from `'../api/analytics'`
- **Files modified:** Analytics.tsx, TaxAnalytics.tsx
- **Commit:** included in 471b936

**2. [Rule 2 - Missing functionality] NavLink end prop for /tax route**
- **Found during:** Task 2 — UI review of navigation
- **Issue:** Without `end=true`, the `/tax` nav item would highlight as active when visiting `/tax/analytics` since NavLink uses prefix matching. Similarly `/` would match all routes.
- **Fix:** Added `end` field to navItems type and applied `end` prop to NavLink. Set `end: true` for `/`, `/analytics`, `/tax` entries.
- **Files modified:** Layout.tsx
- **Commit:** included in cb45683

## Self-Check: PASSED

Files exist:
- `web/src/pages/Analytics.tsx` — FOUND
- `web/src/pages/TaxAnalytics.tsx` — FOUND
- `web/src/components/AIInsight.tsx` — FOUND
- `web/src/App.tsx` — MODIFIED (routes present)
- `web/src/components/Layout.tsx` — MODIFIED (nav items present)

Commits exist:
- `471b936` — FOUND (feat(12-06): create Analytics and TaxAnalytics dashboard pages)
- `cb45683` — FOUND (feat(12-06): add AIInsight placeholder, register routes, update sidebar nav)

Build: PASSED
TypeScript: PASSED

---
*Phase: 12-management-dashboard-comprehensive-analytics*
*Completed: 2026-02-22*
