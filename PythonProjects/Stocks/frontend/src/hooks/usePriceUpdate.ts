/**
 * usePriceUpdate — tracks live price changes for a single ticker and
 * returns Framer Motion animation variants for green/red flash effects.
 *
 * The hook subscribes to the React Query cache for ['market', 'quote', ticker]
 * so it reacts to both REST-fetched updates and WebSocket cache patches from
 * useWebSocket without any additional wiring.
 *
 * Requirements: R8.3, R3.6
 */

import { useRef, useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { Variants } from 'framer-motion'
import type { Quote } from '@/api/market'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PriceDirection = 'up' | 'down' | 'neutral'

export interface UsePriceUpdateReturn {
  /** The latest price from the cache (undefined until first load) */
  displayPrice: number | undefined
  /** Direction of the most recent price change */
  priceDirection: PriceDirection
  /**
   * Framer Motion variants — pass as `variants` prop to a `motion.div`.
   *
   * Usage:
   *   <motion.div variants={flashVariants} animate={animateKey} />
   *
   * The background pulses briefly on each price update, then fades back to
   * transparent.
   */
  flashVariants: Variants
  /**
   * Pass this as the `animate` prop to `motion.div` (along with `variants`).
   * Changes on every price update so Framer Motion re-triggers the animation.
   */
  animateKey: string
}

// ---------------------------------------------------------------------------
// Flash variant definitions (R8.3)
// ---------------------------------------------------------------------------

const FLASH_VARIANTS: Variants = {
  up: {
    backgroundColor: [
      'rgba(0, 200, 81, 0)',
      'rgba(0, 200, 81, 0.2)',
      'rgba(0, 200, 81, 0)',
    ],
    transition: { duration: 0.6, ease: 'easeInOut' },
  },
  down: {
    backgroundColor: [
      'rgba(255, 68, 68, 0)',
      'rgba(255, 68, 68, 0.2)',
      'rgba(255, 68, 68, 0)',
    ],
    transition: { duration: 0.6, ease: 'easeInOut' },
  },
  neutral: {
    backgroundColor: 'rgba(0, 0, 0, 0)',
    transition: { duration: 0 },
  },
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function usePriceUpdate(
  ticker: string,
  initialPrice?: number
): UsePriceUpdateReturn {
  const queryClient = useQueryClient()
  const upperTicker = ticker.toUpperCase()

  // Read the current cached value (or fall back to initialPrice)
  const getCachedPrice = (): number | undefined => {
    const cached = queryClient.getQueryData<Quote>(['market', 'quote', upperTicker])
    return cached?.price ?? initialPrice
  }

  const [displayPrice, setDisplayPrice] = useState<number | undefined>(getCachedPrice)
  const [priceDirection, setPriceDirection] = useState<PriceDirection>('neutral')
  const [animateKey, setAnimateKey] = useState<string>(`${upperTicker}-0`)

  // Track previous price to derive direction
  const prevPriceRef = useRef<number | undefined>(getCachedPrice())

  // Subscribe to React Query cache updates for this ticker
  useEffect(() => {
    // Sync with any price already in cache when the ticker changes
    const currentPrice = getCachedPrice()
    prevPriceRef.current = currentPrice
    setDisplayPrice(currentPrice)
    setPriceDirection('neutral')
    setAnimateKey(`${upperTicker}-${Date.now()}`)

    // React Query v5: subscribe to cache changes
    const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
      // We only care about updates to our specific query key
      if (event.type !== 'updated') return

      const key = event.query.queryKey
      if (
        !Array.isArray(key) ||
        key[0] !== 'market' ||
        key[1] !== 'quote' ||
        key[2] !== upperTicker
      ) {
        return
      }

      const newData = event.query.state.data as Quote | undefined
      if (!newData) return

      const newPrice = newData.price
      const prevPrice = prevPriceRef.current

      let direction: PriceDirection = 'neutral'
      if (prevPrice !== undefined && newPrice !== prevPrice) {
        direction = newPrice > prevPrice ? 'up' : 'down'
      }

      prevPriceRef.current = newPrice
      setDisplayPrice(newPrice)
      setPriceDirection(direction)
      // Change the key on every price update so Framer Motion re-fires the animation
      setAnimateKey(`${upperTicker}-${Date.now()}`)
    })

    return unsubscribe
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [upperTicker, queryClient])

  return {
    displayPrice,
    priceDirection,
    flashVariants: FLASH_VARIANTS,
    animateKey,
  }
}
