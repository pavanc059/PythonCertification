# Task Completion: Build stock detail page

**Status:** Completed ✅  
**Date:** 2025-07-13

## Files

- `frontend/src/pages/StockDetailPage.tsx` — New page component (created)
- `frontend/src/App.tsx` — Updated to wire `StockDetailPage` into the `/stock/:ticker` route

## What Was Implemented

A full stock detail page accessible at `/stock/:ticker` (protected, wrapped in `AppShell`).

### Header section
- Ticker badge (`bg-[#6366f1]/20 text-[#6366f1]`) for the symbol
- Company name loaded from the `/market/quote` response
- Current price displayed large and bold (`text-4xl font-bold`)
- Day change amount + percentage with green/red color coding (`text-green-400` / `text-red-400`)
- Buy (green) and Sell (red) buttons in the top-right that open `OrderTicket` pre-filled with the ticker and the correct side

### CandlestickChart
- `CandlestickChart` rendered with `height={480}` occupying ~60% of the vertical viewport
- Receives `ticker` from URL params via `useParams`
- Handles its own data fetching internally (no extra data-fetching in the page)

### AI Prediction card
- Direction badge: Bullish (green + TrendingUp icon) / Bearish (red + TrendingDown) / Neutral (muted + Minus)
- Confidence progress bar with ARIA `role="progressbar"` attributes (0–100%)
- Top-5 SHAP key factors sorted by absolute value, showing factor name, a proportional color bar (green = positive contribution, red = negative), and the raw value
- Loading skeleton while fetching
- Error state if the prediction endpoint fails

### Quick stats row
- 5 stat cards in a responsive grid: P/E Ratio, Market Cap, Volume, Day High, Day Low
- Volume formatted with `formatCompact`; Day High/Low with `formatCurrency`
- P/E and Market Cap gracefully show "—" (not available in the current `Quote` type)
- Loading skeletons while the quote query resolves

### React Query
- `['market', 'quote', ticker]` with `refetchInterval: 30_000`
- `['market', 'prediction', ticker]` with `staleTime: 60_000`
- Used `queryKeys.market.quote` and `queryKeys.market.prediction` from the shared `queryKeys` module

### OrderTicket integration
- `OrderTicket` mounted at page level
- Buy/Sell buttons set the `defaultSide` and toggle `isOpen`

## Tests Written

No unit tests written — this is a UI page component. TypeScript type-checking (`npx tsc --noEmit`) passes with **0 errors**.

## Requirements Satisfied

- **R3.5** — Stock detail page with chart and key stats
- **R3.8** — AI prediction displayed with bull/bear/neutral direction and confidence
- **R5.7** — Buy button on stock detail page pre-fills and opens `OrderTicket`
- **R5.8** — Sell button on stock detail page pre-fills and opens `OrderTicket`

## Notes

- P/E Ratio and Market Cap show "—" because the `Quote` API type does not currently include those fields. They can be added later when the backend returns them without changing the page structure.
- 52W High/Low are not in the `Quote` type either; Day High/Low are shown instead as the closest available fields.
- The route `/stock/:ticker` was already stubbed in `App.tsx`; this task replaced the placeholder with the real component.
