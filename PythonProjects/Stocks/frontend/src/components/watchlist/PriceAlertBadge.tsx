import { Bell } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatCurrency } from '@/lib/formatters'

interface PriceAlertBadgeProps {
  alertPrice: number
  currentPrice: number
  ticker?: string
  className?: string
}

/**
 * Visual badge shown on a watchlist card when the current price meets or
 * exceeds the user-configured alert price.
 *
 * Returns null when:
 *  - currentPrice is 0 (not yet loaded)
 *  - alertPrice is 0 / falsy (no alert set)
 *  - currentPrice has not yet reached alertPrice
 */
export function PriceAlertBadge({
  alertPrice,
  currentPrice,
  ticker,
  className,
}: PriceAlertBadgeProps) {
  // Guard: nothing to show if no alert is configured or price hasn't loaded
  if (!alertPrice || currentPrice === 0) return null

  // Only show when price has breached (met or exceeded) the alert level
  if (currentPrice < alertPrice) return null

  return (
    <div
      role="status"
      aria-label={`Price alert triggered${ticker ? ` for ${ticker}` : ''}: ${formatCurrency(alertPrice)}`}
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-semibold',
        'bg-amber-500/15 text-amber-400 border border-amber-500/30',
        'animate-pulse',
        className
      )}
    >
      <Bell className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
      <span>Alert: {formatCurrency(alertPrice)}</span>
    </div>
  )
}

export default PriceAlertBadge
