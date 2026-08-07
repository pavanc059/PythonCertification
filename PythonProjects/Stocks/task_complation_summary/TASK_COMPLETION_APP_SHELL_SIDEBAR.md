# Task Completion: Build App Shell and Sidebar Navigation

**Status:** Completed ✅
**Date:** 2025-07-16

## Files

- `frontend/src/components/layout/AppShell.tsx` — Updated: added `min-h-screen` to both the wrapper div and the `<main>` element for correct full-height layout
- `frontend/src/components/layout/Sidebar.tsx` — Updated: added Stock Search nav item, user avatar initials circle, account value from React Query with color indicator, and proper collapsed-state behavior
- `frontend/src/components/layout/MobileNav.tsx` — No changes required (already complete with 4 tabs)

## What Was Implemented

### Sidebar.tsx
- Added 5th nav item: **Stock Search** (`Search` icon, path `/stock/search`)
- Added **user avatar circle** showing initials (first letter of first + last name, or first 2 chars) styled with `bg-primary/20 text-primary`
- Added **account value** in sidebar footer using `useQuery` from `@tanstack/react-query`:
  - `queryKey: ['portfolioSummary']`, `staleTime: 60_000`, `refetchInterval: 60_000`
  - Calls `getPortfolioSummary()` from `@/api/portfolio`
  - Displays `total_value` via `formatCurrency()` from `@/lib/formatters`
  - Color: `text-gain` (`#00C851`) when `total_return_pct >= 0`, `text-loss` (`#FF4444`) when negative
  - Shows `--` placeholder while loading or on error
  - Return percentage shown alongside value in parentheses
- Collapsed state shows only the avatar circle + logout icon (no name/value text)
- Nav items centered in collapsed state with `title` tooltip for hover label

### AppShell.tsx
- Added `min-h-screen` to both the outer flex wrapper and the `<main>` element to ensure proper full-viewport layout

## Tests

No unit tests written — these are pure presentational layout components. Visual behavior is verified via the TypeScript build (`npm run build` passes with 0 errors).

## Requirements Satisfied

- **R9.4** — App shell with sidebar + main content area wrapping all authenticated pages
- **R9.5** — Sidebar with logo, all 5 nav links (Dashboard, Portfolio, Watchlist, Trading, Stock Search), user avatar + logout, collapsible behavior (240px / 64px icon-only), active route highlighting, user display name and account value in footer

## Notes

- The `formatPercent` utility multiplies by 100 internally, so `total_return_pct` (already a decimal fraction from the API, e.g. `0.05` for 5%) is passed as `returnPct / 100` to avoid double-scaling. If the backend returns whole numbers (e.g. `5` for 5%), adjust accordingly.
- `/stock/search` route will be added in Task 26 (StockDetailPage). The nav item renders correctly today; it just won't match an active route until that route exists.
- MobileNav already had 4 correct primary tabs — no changes were needed.
