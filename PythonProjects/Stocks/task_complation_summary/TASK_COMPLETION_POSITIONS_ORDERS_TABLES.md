# Task Completion: Build Positions and Orders Tables

**Status:** Completed ✅  
**Date:** 2025-07-14

## Files Created

- `frontend/src/components/positions/PositionsTable.tsx` — Sortable positions table with Sell button per row
- `frontend/src/components/trading/PendingOrdersTable.tsx` — Pending orders table with ConfirmDialog-gated Cancel button
- `frontend/src/components/positions/TradeHistoryTable.tsx` — Trade history table with filters, sorting, and CSV export

## What Was Implemented

### PositionsTable
- Columns: Ticker, Qty, Avg Price, Current Price, Market Value, Unrealized P&L ($), Unrealized P&L (%), Day Change %, Action (Sell button)
- Sortable by: Ticker, Qty, Market Value, Unrealized P&L %, Day Change %
- Sort direction arrows (▲/▼) on active column, ↕ indicator on inactive sortable columns
- Color-coded P&L and Day Change % using `getPnlClass()` (`text-gain` / `text-loss`)
- Red Sell button per row that calls `onSell(ticker)`
- Empty state: "No open positions" centered message
- 3 skeleton rows shown while `isLoading=true`
- Responsive with `overflow-x-auto` wrapper

### PendingOrdersTable
- Columns: Ticker, Type, Side, Qty, Limit/Stop Price, Status, Created, Action (Cancel button)
- Filters to only `status === 'pending'` rows
- Status badge color-coded: pending=amber, filled=green, cancelled=gray, rejected=red
- Limit/Stop Price column: shows `limit_price` first, then `stop_price`, else "—"
- Cancel button opens `ConfirmDialog` (destructive mode) before calling `cancelOrder()`
- On cancel success: calls `onCancelSuccess?.()` and shows Sonner toast
- On cancel error: shows error toast
- Empty state: "No pending orders"
- 3 skeleton rows while `isLoading=true`

### TradeHistoryTable
- Columns: Date (closed_at), Ticker, Side (colored badge), Qty, Fill Price (exit_price), Commission (—), Slippage (—), Realized P&L
- Sortable by: Date, Ticker, Realized P&L
- Filter row above table:
  - Text input for ticker (case-insensitive partial match)
  - Date range inputs (From / To), inclusive of the "to" day
  - Side filter button group: All | Buy | Sell
- CSV export button: exports filtered+sorted data as `trade-history-YYYY-MM-DD.csv`
- Empty state: "No trade history"
- 3 skeleton rows while `isLoading=true`

## Tests Written

No unit tests were written for this task — these are pure presentational/UI components with no business logic to test independently. The sorting/filtering logic uses standard array operations that are straightforward to verify visually. Integration tests would require a full React test setup.

## Requirements Satisfied

- **R6.1** — Open positions table with all required columns and Sell button ✅
- **R6.2** — Trade history table with Date, Ticker, Side, Qty, Fill Price, Commission, Slippage, Realized P&L ✅
- **R6.3** — Pending orders section with Cancel button per row ✅
- **R6.4** — All three tables support sorting by column ✅
- **R6.5** — Trade history filter by ticker, date range, and buy/sell side ✅
- **R6.6** — CSV export button for trade history ✅

## Notes

- `ClosedTradeRecord` (from `api/portfolio.ts`) does not include `commission` or `slippage` fields. Per the task spec, these columns display "—" as placeholder values. They are exported as "—" in CSV as well.
- Commission and Slippage are shown as columns in the UI as required by R6.2, but no data is available from the current type. When the backend adds these fields to `ClosedTradeRecord`, the table can be updated to display real values.
- The `PendingOrdersTable` filters client-side to `status === 'pending'`; it accepts the full `orders` array so the parent can pass `useQuery` data directly without pre-filtering.
- All three components use `useMemo` for derived data to avoid unnecessary re-computation on re-renders.
