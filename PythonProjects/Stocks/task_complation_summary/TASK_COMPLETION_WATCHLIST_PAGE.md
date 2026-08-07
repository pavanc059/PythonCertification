# Task Completion: Build watchlist page

**Status:** Completed ✅  
**Date:** 2025-07-22

## Files

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/WatchlistPage.tsx` | Created | Full watchlist page implementation |
| `frontend/src/App.tsx` | Modified | Added `WatchlistPage` import; replaced placeholder route |

## What Was Implemented

### WatchlistPage.tsx

1. **Data fetching (React Query)**
   - `useQuery` for `getWatchlist` with `refetchInterval: 30_000` — satisfies R3.6 auto-refresh every 30 s
   - `useQuery` for `getWatchlistNames` — feeds the tab bar
   - `useQueries` for per-ticker `getQuote` calls for the active tab's tickers, each with `refetchInterval: 30_000`
   - `useQueries` for per-ticker `getChart('5d', '1d')` sparkline data

2. **Mutations**
   - `addToWatchlist` mutation — triggered by `AddTickerInput.onAdd`, passes `list_name: activeTab`; on success invalidates watchlist and list-names caches
   - `removeFromWatchlist` mutation — passed to `WatchlistCard.onRemove` via `ConfirmDialog`; invalidates watchlist cache (R3.3)
   - `createWatchlistList` mutation — called from the inline "New List" form; on success invalidates list-names cache and switches to the new tab (R3.4)

3. **Tab UI (R3.4)**
   - Derives unique tab names from `getWatchlistNames` merged with `items[].list_name`; falls back to `['Default']`
   - Plain Tailwind styled tab buttons (`bg-[#6366f1]` active, muted inactive), no external tab library needed since shadcn/ui `Tabs` is not installed
   - `+` / "New List" button at the end of the tab row opens an inline input with validation (non-empty, unique name), Enter/Escape key support

4. **Grid layout**
   - `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4`
   - Each `WatchlistCard` receives `item`, `quote`, `sparklineData`, `isLoading`, `onRemove`, `onClick`
   - `onClick` navigates to `/stock/:ticker` via `useNavigate`

5. **Empty state**
   - Centered `LineChart` icon (64 px, muted), heading "Your watchlist is empty", subtext, and CTA "Add Your First Stock" that focuses the `AddTickerInput`

6. **Loading skeleton**
   - Renders 6 `<WatchlistCard isLoading={true} />` skeleton cards while initial watchlist data loads

7. **Header**
   - Page title "Watchlist" with a count badge showing total items
   - Subtitle "Track stocks and monitor price alerts"

8. **Error handling**
   - Error banner shown when watchlist query fails

### App.tsx changes

- Imported `WatchlistPage` from `@/pages/WatchlistPage`
- Replaced `<div className="text-white p-8">Watchlist (Task 20)</div>` with `<WatchlistPage />`

## Tests

No unit tests written — this is a UI page component that requires a running API and browser environment. Integration testing is deferred to the broader E2E test phase.

## Requirements Satisfied

| Requirement | Description | Satisfied |
|-------------|-------------|-----------|
| R3.3 | Remove stocks from watchlist with confirmation | ✅ via `WatchlistCard.onRemove` → `ConfirmDialog` |
| R3.4 | Multiple named watchlists with tabs; create via "+" | ✅ tab bar + inline new-list form |
| R3.6 | Auto-refresh prices every 30 seconds | ✅ `refetchInterval: 30_000` on items + quote queries |

## Notes / Caveats

- `AddWatchlistRequest` does not include a `company_name` field, so the company name from the `AddTickerInput` validation quote is not forwarded to the backend — the server-side record will be populated by the backend if it resolves the name from the quote.
- No shadcn/ui `Tabs` component is installed (`frontend/src/components/ui` does not exist), so tab styling uses plain Tailwind classes matching the existing dark theme.
- The `/stock/:ticker` route still shows a placeholder (`Stock Detail (Task 26)`) — `WatchlistCard` click-through navigation is wired correctly and will work once Task 26 is implemented.
- `onBuy` is intentionally omitted from `WatchlistCard` calls (passed as `undefined`) pending the `OrderTicket` implementation in Task 24.
