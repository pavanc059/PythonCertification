# Task Completion: Build Candlestick Chart Component

**Status:** Completed ✅
**Date:** 2025-07-22

## Files

- `frontend/src/components/charts/CandlestickChart.tsx` — Full implementation of the candlestick chart component (new file, ~350 lines)

## What Was Implemented

A full-featured candlestick chart component built on TradingView's `lightweight-charts` v5.2.0 with the following capabilities:

### Core Chart
- OHLCV candlestick rendering with dark theme matching the app's color tokens (`#0a0e1a` bg, `#00C851` gain, `#FF4444` loss, `#6366f1` brand/crosshair)
- Volume histogram overlay on a separate price scale (semi-transparent gain/loss colors)
- Crosshair OHLCV tooltip bar (shows O/H/L/C/V values as the user hovers)
- ResizeObserver-based responsive sizing — chart reflows when the container resizes
- Proper cleanup via `chart.remove()` on unmount and on data changes

### Time Range Selector
- 1D / 1W / 1M / 3M / 1Y toggle buttons above the chart
- Each range maps to the correct `period` and `interval` for the `/market/chart` API
- Data fetched via React Query (`useQuery`) keyed by `[ticker, period, interval]`; 60-second stale time

### Toggleable Overlays
- **Bollinger Bands (BB)** — rendered on the main chart as three line series (upper/middle/lower bands using SMA-20 ± 2σ)
- **RSI (14)** — rendered in a separate 100px pane below the main chart with overbought (70) and oversold (30) reference lines
- **MACD (12,26,9)** — rendered in a separate 100px pane with MACD line, signal line, and histogram bars

### Indicator Calculations (client-side)
- `calcEMA(values, period)` — exponential moving average with standard k=2/(n+1) smoothing
- `calcSMA(values, period)` — simple moving average
- `calcRSI(closes, period=14)` — Wilder smoothing RSI
- `calcMACD(closes)` — EMA(12) − EMA(26) with EMA(9) signal
- `calcBollingerBands(closes, period=20)` — SMA ± 2 standard deviations

### Loading & Error States
- Animated skeleton div while data is loading (matches card dimensions)
- Inline error message when the API returns an error

### Component Interface
```ts
interface CandlestickChartProps {
  ticker: string
  height?: number  // default 400
  className?: string
}
```

## Tests

No automated tests written for this task — the component is a pure UI/charting component that relies on the DOM canvas API and is not practically unit-testable without a browser environment. Visual verification is the appropriate testing method.

## Requirements Satisfied

- **R3.9** — Stock detail view includes a candlestick chart with RSI, MACD, and Bollinger Bands toggleable overlays ✅

## Notes

- Uses `lightweight-charts` v5 API (breaking changes from v4): `createChart`, `addCandlestickSeries`, `addLineSeries`, `addHistogramSeries`, `subscribeCrosshairMove`.
- RSI and MACD are rendered as separate `createChart` instances on separate `<div>` elements (simpler than the v5 `addPane()` API, and gives full layout control).
- All indicator math runs client-side — no extra API calls needed.
- The component is ready to drop into `StockDetailPage.tsx` (Task 26) via `<CandlestickChart ticker={ticker} />`.
- TypeScript compilation passes with zero errors (`npx tsc --noEmit`).
