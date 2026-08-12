/**
 * useWebSocket — connects to WS /ws/prices?token=<jwt>
 *
 * Features:
 * - Connects only when the user is authenticated (R8.2)
 * - Sends subscribe/unsubscribe messages to the server
 * - Updates React Query cache on price messages (R8.1, R3.6)
 * - Auto-reconnects with exponential backoff: 1s → 2s → 4s → … → 30s max (R8.4)
 * - Disconnects cleanly on logout or component unmount (R8.2)
 *
 * Requirements: R8.1, R8.2, R8.4, R8.5, R3.6
 */

import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import type { Quote } from '@/api/market'
import type { Position } from '@/api/portfolio'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BACKOFF_INITIAL_MS = 1_000
const BACKOFF_MAX_MS = 30_000
const BACKOFF_MULTIPLIER = 2

// ---------------------------------------------------------------------------
// URL helper
// ---------------------------------------------------------------------------

function buildWsUrl(token: string): string {
  // Use VITE_WS_URL env var if defined, otherwise fall back to direct backend URL.
  // In production, Nginx proxies /ws/* to the backend, so we switch protocol
  // based on the page's own protocol.
  const envWsUrl = import.meta.env.VITE_WS_URL as string | undefined

  if (envWsUrl) {
    return `${envWsUrl}/ws/prices?token=${encodeURIComponent(token)}`
  }

  // Development default: hit the backend directly on port 8000
  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${wsProtocol}://localhost:8000/ws/prices?token=${encodeURIComponent(token)}`
}

// ---------------------------------------------------------------------------
// Hook types
// ---------------------------------------------------------------------------

export interface UseWebSocketOptions {
  /** Tickers to subscribe to immediately on connect */
  tickers?: string[]
  /** Called with latest prices map on each price update */
  onPriceUpdate?: (prices: Record<string, number>) => void
  /** When false the WebSocket connection is not opened (feature flag gate) */
  enabled?: boolean
}

export interface UseWebSocketReturn {
  isConnected: boolean
  subscribe: (tickers: string[]) => void
  unsubscribe: (tickers: string[]) => void
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { tickers = [], onPriceUpdate, enabled = true } = options

  const queryClient = useQueryClient()
  const { accessToken, isAuthenticated } = useAuthStore()

  // Refs so callbacks always close over the latest values without re-creating
  // the WebSocket on every render.
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const backoffMsRef = useRef(BACKOFF_INITIAL_MS)
  const isConnectedRef = useRef(false)
  const intentionalCloseRef = useRef(false)
  const tickersRef = useRef<string[]>(tickers)
  const onPriceUpdateRef = useRef(onPriceUpdate)

  // Keep refs in sync with latest prop values
  useEffect(() => { tickersRef.current = tickers }, [tickers])
  useEffect(() => { onPriceUpdateRef.current = onPriceUpdate }, [onPriceUpdate])

  // ------------------------------------------------------------------
  // Cache updater: called on every "prices" message
  // ------------------------------------------------------------------
  const updateQueryCache = useCallback(
    (prices: Record<string, number>) => {
      for (const [ticker, newPrice] of Object.entries(prices)) {
        const upperTicker = ticker.toUpperCase()

        // 1. Update individual quote cache
        queryClient.setQueryData<Quote>(
          ['market', 'quote', upperTicker],
          (prev) => {
            if (!prev) return prev
            return { ...prev, price: newPrice }
          }
        )

        // 2. Update positions cache — recalculate derived fields
        queryClient.setQueryData<Position[]>(
          ['portfolio', 'positions'],
          (prev) => {
            if (!prev) return prev
            return prev.map((pos) => {
              if (pos.ticker !== upperTicker) return pos
              const marketValue = pos.quantity * newPrice
              const unrealizedPnl = marketValue - pos.cost_basis
              const unrealizedPnlPct =
                pos.cost_basis > 0 ? (unrealizedPnl / pos.cost_basis) * 100 : 0
              return {
                ...pos,
                current_price: newPrice,
                market_value: marketValue,
                unrealized_pnl: unrealizedPnl,
                unrealized_pnl_pct: unrealizedPnlPct,
              }
            })
          }
        )
      }
    },
    [queryClient]
  )

  // ------------------------------------------------------------------
  // Send helper — only sends if socket is open
  // ------------------------------------------------------------------
  const sendMessage = useCallback((payload: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }, [])

  // ------------------------------------------------------------------
  // Public subscribe / unsubscribe
  // ------------------------------------------------------------------
  const subscribe = useCallback(
    (tickers: string[]) => {
      if (tickers.length > 0) {
        sendMessage({ type: 'subscribe', tickers })
      }
    },
    [sendMessage]
  )

  const unsubscribe = useCallback(
    (tickers: string[]) => {
      if (tickers.length > 0) {
        sendMessage({ type: 'unsubscribe', tickers })
      }
    },
    [sendMessage]
  )

  // ------------------------------------------------------------------
  // Connect logic
  // ------------------------------------------------------------------
  const connect = useCallback(() => {
    if (!accessToken) return

    intentionalCloseRef.current = false

    const url = buildWsUrl(accessToken)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      isConnectedRef.current = true
      backoffMsRef.current = BACKOFF_INITIAL_MS // reset backoff on successful connect

      // Subscribe to initial tickers
      if (tickersRef.current.length > 0) {
        ws.send(JSON.stringify({ type: 'subscribe', tickers: tickersRef.current }))
      }
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string)

        if (msg.type === 'prices' && msg.data) {
          const prices = msg.data as Record<string, number>
          updateQueryCache(prices)
          onPriceUpdateRef.current?.(prices)
        }
        // "ack" and "error" messages are informational — we silently ignore them here.
        // A future enhancement could log them or surface them to the UI.
      } catch {
        // Malformed JSON from server — ignore
      }
    }

    ws.onclose = () => {
      isConnectedRef.current = false
      wsRef.current = null

      if (intentionalCloseRef.current) return

      // Schedule reconnect with exponential backoff (R8.4)
      const delay = backoffMsRef.current
      backoffMsRef.current = Math.min(
        backoffMsRef.current * BACKOFF_MULTIPLIER,
        BACKOFF_MAX_MS
      )

      reconnectTimerRef.current = setTimeout(() => {
        if (!intentionalCloseRef.current) {
          connect()
        }
      }, delay)
    }

    ws.onerror = () => {
      // The onclose handler fires immediately after onerror; reconnect logic
      // lives there so we don't need to do anything extra here.
    }
  }, [accessToken, updateQueryCache])

  // ------------------------------------------------------------------
  // Disconnect logic
  // ------------------------------------------------------------------
  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    backoffMsRef.current = BACKOFF_INITIAL_MS
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    isConnectedRef.current = false
  }, [])

  // ------------------------------------------------------------------
  // Lifecycle: connect when authenticated AND streaming enabled
  // ------------------------------------------------------------------
  useEffect(() => {
    if (isAuthenticated && accessToken && enabled) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
    // Re-run only when auth state changes, not on every connect/disconnect
    // reference change (those are stable useCallback refs).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, accessToken, enabled])

  return {
    // Expose a reactive connected flag by reading from the ref.
    // Note: because this is a ref, React won't re-render on change.
    // Components that need reactive state should poll or use the onPriceUpdate callback.
    get isConnected() {
      return isConnectedRef.current
    },
    subscribe,
    unsubscribe,
  }
}
