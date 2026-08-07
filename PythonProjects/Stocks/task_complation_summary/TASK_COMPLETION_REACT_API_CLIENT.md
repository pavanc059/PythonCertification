# Task Completion: Implement API Client Layer (Task 11)

**Status:** Completed ✅  
**Date:** 2025-07-22

## Files Created

| File | Description |
|------|-------------|
| `frontend/src/api/client.ts` | Axios instance with base URL `/api`, JWT request interceptor, and 401→redirect response interceptor |
| `frontend/src/api/auth.ts` | Typed auth API: `registerUser`, `loginUser`, `logoutUser`, `refreshToken` + request/response interfaces |
| `frontend/src/api/portfolio.ts` | Typed portfolio API: `getPortfolioSummary`, `getPositions`, `getPortfolioHistory` + all response interfaces |
| `frontend/src/api/trading.ts` | Typed trading API: `getAccount`, `placeOrder`, `getOrders`, `cancelOrder`, `resetAccount` + interfaces |
| `frontend/src/api/watchlist.ts` | Typed watchlist API: `getWatchlist`, `addToWatchlist`, `removeFromWatchlist`, `getWatchlistNames`, `createWatchlistList` + interfaces |
| `frontend/src/api/market.ts` | Typed market API: `getQuote`, `getChart`, `getPrediction` + `Quote`, `ChartData`, `Prediction` interfaces |
| `frontend/src/api/queryKeys.ts` | Typed React Query key factory covering portfolio, trading, watchlist, and market namespaces |

## What Was Implemented

### `api/client.ts`
- Axios instance targeting `/api` (Vite proxy rewrites to `http://localhost:8000`)
- `withCredentials: true` for HTTP-only cookie support (refresh token flow)
- Request interceptor reads `stockiq-token` from `localStorage` and attaches `Authorization: Bearer <token>`
- Response interceptor catches 401 responses, clears the token, and redirects to `/login`

### Typed API modules
Each module (`auth`, `portfolio`, `trading`, `watchlist`, `market`) exports:
- TypeScript interfaces for all request bodies and response shapes
- Async functions that call `apiClient` and return the typed `data` payload directly

### `api/queryKeys.ts`
Typed factory following the React Query recommended pattern with `as const` tuples, covering all five data domains. The `QueryClient` stale time (30 s) was already configured in `main.tsx` (Task 9).

## Build Verification

```
tsc -b && vite build
✓ 85 modules transformed.
✓ built in 4.92s
Exit Code: 0
```

Zero TypeScript errors.

## Tests Written

No unit tests — this layer is pure HTTP glue with no business logic. Integration tests belong at the component/hook level (future tasks).

## Requirements Satisfied

- **R7.7** — JWT attached to every authenticated request via Axios interceptor
- **R7.9** — Typed API client functions for all backend endpoints (auth, portfolio, trading, watchlist, market)

## Notes

- The vite proxy (`/api` → `http://localhost:8000`, stripping `/api`) is already configured in `vite.config.ts`.
- `refreshToken` calls `/auth/refresh` using the HTTP-only cookie sent automatically via `withCredentials: true`.
- The 401 interceptor does **not** attempt token refresh before redirecting — a silent refresh flow can be layered in a future task if needed.
- `queryKeys.ts` is ready for use with `useQuery` / `useMutation` hooks in subsequent UI tasks.
