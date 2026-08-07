# Task Completion: 19. Build watchlist components

**Status:** Completed ✅  
**Date:** 2025-07-22

---

## Files Created

| File | Description |
|------|-------------|
| `frontend/src/components/watchlist/PriceAlertBadge.tsx` | Amber pulsing badge with bell icon shown when current price meets/exceeds the configured alert price |
| `frontend/src/components/watchlist/WatchlistCard.tsx` | Full watchlist stock card with ticker, price, day-change badge, stats row, sparkline, buy button, and remove confirmation |
| `frontend/src/components/watchlist/AddTickerInput.tsx` | Controlled input that validates the ticker via `/market/quote` before calling `onAdd`; shows inline error on bad tickers |

---

## What Was Implemented

### `PriceAlertBadge`
- Props: `alertPrice`, `currentPrice`, `ticker?`, `className?`
- Returns `null` when `currentPrice === 0` (not loaded) or `alertPrice` is falsy
- Shows an amber badge with a `Bell` icon and the formatted alert price only when `currentPrice >= alertPrice`
- Uses Tailwind `animate-pulse` for the visual pulse effect
- Exported as both named and default export

### `WatchlistCard`
- Props: `item` (WatchlistItem), `quote?` (Quote), `sparklineData?`, `isLoading?`, `onRemove?`, `onBuy?`, `onClick?`
- Shows `<SkeletonCard lines={4} />` while `isLoading=true`
- Card layout:
  - **Header**: bold ticker + muted company name; × remove button visible only on `group-hover`
  - **Price row**: large current price + green/red day-change badge (`±$X.XX (±Y.YY%)`)
  - **Stats row**: Day High / Day Low / Volume in muted text
  - **Alert badge**: `PriceAlertBadge` rendered below stats when `item.alert_price` is set
  - **Footer**: 5-day `SparklineChart` (left) + outline Buy button (right)
- Entire card is clickable (calls `onClick(ticker)`); remove and buy buttons call `e.stopPropagation()`
- Uses `ConfirmDialog` for remove action with message `"Remove {TICKER} from your watchlist?"`
- `group` class on outer div enables hover-reveal delete button via `group-hover:opacity-100`

### `AddTickerInput`
- Props: `onAdd`, `isLoading?`, `className?`
- Input is uppercase-forced and strips non-valid ticker characters on each keystroke
- Submit fires on Enter key or "Add" button click
- Calls `getQuote(ticker)` from `api/market.ts` to validate the ticker exists
- On success: calls `onAdd(ticker, quote.company_name)` and clears the input
- On error: displays `"Invalid ticker symbol. Please try again."` via `role="alert"` paragraph
- Shows a `Loader2` spinner in the button while validating; disables input+button during loading
- Clears error immediately when user starts typing again

---

## Tests Written

No automated tests were written for this task — these are pure UI components requiring a browser/DOM environment. Integration-level testing is recommended as part of Task 20 (watchlist page assembly).

---

## Requirements Satisfied

| Requirement | Description |
|-------------|-------------|
| **R3.1** | Users can add stocks to the watchlist by typing a ticker symbol (`AddTickerInput` validates via `/market/quote`) |
| **R3.2** | Each card displays ticker, company name, current price, day change ($ and %), day high, day low, volume, and 5-day sparkline |
| **R3.3** | Remove button (with `ConfirmDialog` confirmation) removes stocks from the watchlist |
| **R3.7** | `PriceAlertBadge` visually highlights the card with a pulsing amber badge when the alert price is breached |

---

## Notes & Integration Points for Task 20

- **No shadcn/ui** `<Button>` or `<Input>` components are installed in the project. All interactive elements use native HTML elements styled with Tailwind — consistent with the existing codebase (`LoginForm.tsx` pattern).
- **`formatCompact` volume display**: `formatCompact` returns a `$` prefix (e.g. `$1.23M`). The card strips the `$` for volume display since volume is a raw share count, not a currency value.
- **`change_pct` field**: The API returns `change_pct` as a raw decimal (e.g. `0.0523` = 5.23%). The card multiplies by 100 for display rather than calling `formatPercent` to keep the badge label consistent.
- **Sparkline data**: The `WatchlistCard` accepts `sparklineData` as a prop. Task 20 will need to fetch 5-day chart data (via `getChart(ticker, '5d', '1d')`) and extract `data.map(d => d.close)` to pass here.
- **Alert price editing**: `PriceAlertBadge` only displays the triggered alert. Setting/editing alert prices is a separate concern (likely a modal or inline edit in Task 20).
- **TypeScript**: `npx tsc --noEmit` passed with zero errors after implementation.
