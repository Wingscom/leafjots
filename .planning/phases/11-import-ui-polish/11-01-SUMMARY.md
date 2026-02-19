# Phase 11 Plan 01: Import UI Polish -- Progress, Summary, Error Detail

## One-liner
Auto-parse after CSV upload with expandable import rows showing operation summary stats and per-row error detail.

## Changes Made

### Task 1: Add summary endpoint to backend
- Added `ImportSummaryResponse` schema to `src/cryptotax/api/schemas/imports.py`
- Added `GET /api/imports/{import_id}/summary` endpoint to `src/cryptotax/api/imports.py`
- Endpoint aggregates operation counts and status breakdown from import rows

### Task 2: Verify error rows endpoint
- Confirmed existing `GET /api/imports/{id}/rows?status=error` endpoint returns error_message field
- `CsvImportRowResponse` already includes `error_message: Optional[str]` -- no changes needed

### Task 3: Add frontend API functions
- Added `ImportSummary` and `CsvImportRow` interfaces to `web/src/api/imports.ts`
- Added `getImportSummary()` and `getImportRows()` API client functions

### Task 4: Add frontend hooks
- Added `useImportSummary(importId)` hook to `web/src/hooks/useImports.ts`
- Added `useImportRows(importId, status?)` hook to `web/src/hooks/useImports.ts`

### Task 5-8: Upgrade Imports page (auto-parse, summary panel, error detail, expandable rows)
- **Auto-parse after upload**: Upload success handler now automatically triggers `parseMutation.mutate(data.import_id)`
- **Combined progress indicator**: Shows "Uploading..." then "Parsing rows..." then parse result with counts
- **Expandable import rows**: Each row is clickable with chevron icon; expands to show detail panel below
- **ImportDetail component**: Shows 4 stat cards (Total, Parsed, Errors, Skipped) and operation breakdown pills
- **StatCard component**: Colored stat cards for status breakdown
- **ErrorRows component**: Shows failed rows with row number, operation, CSV data, and error message in red cards
- Parse button has `e.stopPropagation()` to avoid toggling expand when clicking

### Task 9: All checks pass
- 444 tests passing (0 regressions)
- 0 ruff lint errors
- 0 TypeScript errors

## Deviations from Plan

None -- plan executed exactly as written.

## Files Modified

| File | Change |
|------|--------|
| `src/cryptotax/api/schemas/imports.py` | Added `ImportSummaryResponse` schema |
| `src/cryptotax/api/imports.py` | Added `GET /{import_id}/summary` endpoint + import |
| `web/src/api/imports.ts` | Added `ImportSummary`, `CsvImportRow` interfaces + 2 API functions |
| `web/src/hooks/useImports.ts` | Added `useImportSummary`, `useImportRows` hooks |
| `web/src/pages/Imports.tsx` | Full rewrite: auto-parse, expandable rows, summary panel, error detail |

## Verification Results

- `python -m pytest tests/ -x -q` -- 444 passed
- `ruff check src/` -- All checks passed
- `cd web && npx tsc --noEmit` -- 0 errors
