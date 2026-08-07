# Task Completion: Implement WebSocket hook and price updates

**Status:** Completed ✅  
**Date:** 2025-07-23

---

## Files

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/hooks/useWebSocket.ts` | Created | Core WebSocket hook — connects to backend, manages lifecycle, updates React Query cache |
| `frontend/src/hooks/usePriceUpdate.ts` | Created | Framer Motion animation hook — detects price direction and returns flash variants |

---

## What Was Implemented

### `useWebSocket.ts`

- Connects to `WS /ws/prices?token=<jwt>` on mount when `isAuthenticated === true` (R8.2)
- Builds the WebSocket URL from `VITE_WS_URL` env var if defined, otherwise falls back to `ws://localhost:8000` in dev and `wss://<host>/ws/prices` in production
- Sends a `{ type: "subscribe", tickers: [...] }` message immediately on `onopen` for the initial ticker list
- Exposes `subscribe(tickers)` and `unsubscribe(tickers)` functions for dynamic subscription changes
- On each `{ type: "prices", data: {...} }` message:
  - Updates `['market', 'quote', TICKER]` in the React Query cache (patches only the `price` field, preserves all other Quote fields)
  - Updates `['portfolio', 'positions']` — recalculates `market_value`, `unrealized_pnl`, and `unrealized_pnl_pct` for any affected position
  - Calls the optional `onPriceUpdate` callback
- Auto-reconnects with exponential backoff (1s → 2s → 4s → … → 30s cap) on unintentional close (R8.4)
- Disconnects cleanly (sets `intentionalCloseRef = true`, cancels any pending reconnect timer) when `isAuthenticated` becomes false or on unmount (R8.2)

### `usePriceUpdate.ts`

- Subscribes to the React Query query cache for `['market', 'quote', TICKER]` using `queryClient.getQueryCache().subscribe()`
- Detects price direction on each cache update: `up` / `down` / `neutral`
- Returns `flashVariants` (Framer Motion `Variants` object) with:
  - `'up'`: green pulse — `rgba(0, 200, 81, 0.2)` over 600ms (R8.3)
  - `'down'`: red pulse — `rgba(255, 68, 68, 0.2)` over 600ms (R8.3)
  - `'neutral'`: instant transparent (no animation)
- Returns `animateKey` (ticker + timestamp) that changes on every price update, so Framer Motion re-triggers the animation even when the direction is the same
- Returns `displayPrice` (latest cached price) and `priceDirection` for conditional styling in components

### Usage Example

```tsx
// In a price card component:
const { displayPrice, priceDirection, flashVariants, animateKey } = usePriceUpdate('AAPL', 192.40)

<motion.div
  variants={flashVariants}
  animate={animateKey}
  key={animateKey}
>
  <span className={priceDirection === 'up' ? 'text-green-400' : priceDirection === 'down' ? 'text-red-400' : 'text-white'}>
    {displayPrice ? formatCurrency(displayPrice) : '—'}
  </span>
</motion.div>
```

```tsx
// Mount once at app-level (e.g. in AppShell):
const { subscribe, unsubscribe } = useWebSocket({
  tickers: [...watchlistTickers, ...positionTickers],
  onPriceUpdate: (prices) => console.debug('prices', prices),
})
```

---

## Tests Written

No automated tests were written for this task. The hooks rely on browser-native `WebSocket`, Framer Motion, and React Query internals that require a DOM environment. Integration testing would be done via the running app or with a mocked WebSocket (e.g. `jest-websocket-mock`). Manual verification can be done by starting the full stack and observing price flashes on the Watchlist and Portfolio pages.

---

## Requirements Satisfied

| Requirement | Description | Status |
|-------------|-------------|--------|
| R8.1 | WebSocket endpoint streams live price updates | ✅ (client connects to existing endpoint) |
| R8.2 | Connect on login, disconnect on logout | ✅ (`isAuthenticated` guard + cleanup |
| R8.3 | Price cards animate on update (green/red pulse) | ✅ (`usePriceUpdate` Framer Motion variants) |
| R8.4 | Auto-reconnect with exponential backoff, max 30s | ✅ (1s → 2s → … → 30s cap) |
| R8.5 | Prices update at least every 30 seconds during market hours | ✅ (backend broadcasts every 30s; snapshot sent on subscribe) |
| R3.6 | Watchlist prices update every 30 seconds during market hours | ✅ (same broadcast loop) |

---

## Notes

- **Integration point**: `useWebSocket` should be mounted once at the `AppShell` level (or a dedicated `WebSocketProvider`) so the single connection is shared across all pages. Individual components use `usePriceUpdate` to consume cache updates without needing direct WebSocket access.
- **`isConnected` reactivity**: The hook returns `isConnected` as a getter over a ref. It won't trigger React re-renders by itself. If you need reactive connection-status UI, lift it into state via the `onPriceUpdate` callback or add a dedicated state variable.
- **Production URL**: Set `VITE_WS_URL=wss://your-domain.com` in `frontend/.env.production` so the hook targets the production backend. The Nginx config in `frontend/Dockerfile` must proxy `/ws/` to the backend.
- **Framer Motion `animate` + `key`**: The `animateKey` must be passed as **both** `animate` and `key` on the `motion.div` to guarantee re-animation on repeated updates in the same direction.
