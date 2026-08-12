import { useState } from 'react'
import { X, ShoppingCart } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatCurrency, formatCompact } from '@/lib/formatters'
import { SkeletonCard } from '@/components/common/SkeletonCard'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { SparklineChart } from '@/components/charts/SparklineChart'
import { PriceAlertBadge } from './PriceAlertBadge'
import type { WatchlistItem } from '@/api/watchlist'
import type { Quote } from '@/api/market'

interface WatchlistCardProps {
  item: WatchlistItem
  /** Live quote data — may be undefined while loading */
  quote?: Quote
  /** 5-day closing prices for the sparkline */
  sparklineData?: number[]
  isLoading?: boolean
  onRemove?: (ticker: string) => void
  onBuy?: (ticker: string) => void
  onClick?: (ticker: string) => void
  className?: string
}

/**
 * Watchlist card displaying a tracked stock's key metrics, sparkline, and
 * optional price alert indicator.
 *
 * Satisfies R3.2: ticker, company name, price, day change, high/low,
 *   volume, 5-day sparkline.
 * Satisfies R3.3: remove action with confirmation dialog.
 * Satisfies R3.7: price alert visual highlight via PriceAlertBadge.
 */
export function WatchlistCard({
  item,
  quote,
  sparklineData,
  isLoading = false,
  onRemove,
  onBuy,
  onClick,
  className,
}: WatchlistCardProps) {
  const [showConfirm, setShowConfirm] = useState(false)

  if (isLoading) {
    return <SkeletonCard lines={4} className={className} />
  }

  const ticker = item.ticker
  const companyName = quote?.company_name ?? item.company_name ?? ''
  const price = quote?.price ?? 0
  const change = quote?.change ?? 0
  const changePct = quote?.change_pct ?? 0
  const dayHigh = quote?.day_high ?? 0
  const dayLow = quote?.day_low ?? 0
  const volume = quote?.volume ?? 0

  // Determine day-change sign for colouring
  const changeSign = change >= 0 ? '+' : ''

  // Sparkline is positive when net change is non-negative
  const sparklinePositive = change >= 0

  const handleCardClick = () => {
    onClick?.(ticker)
  }

  const handleRemoveClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowConfirm(true)
  }

  const handleBuyClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onBuy?.(ticker)
  }

  const handleConfirmRemove = () => {
    onRemove?.(ticker)
  }

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        aria-label={`${ticker} — ${companyName}. Current price ${formatCurrency(price)}`}
        onClick={handleCardClick}
        onKeyDown={(e) => e.key === 'Enter' && handleCardClick()}
        className={cn(
          // Base card styles
          'group relative bg-card border border-border rounded-lg p-4 flex flex-col gap-3',
          // Cursor and interaction
          onClick ? 'cursor-pointer' : 'cursor-default',
          // Hover state
          'hover:border-border/80 hover:shadow-md transition-all duration-200',
          className
        )}
      >
        {/* ── Header row ── */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-col min-w-0">
            <span className="text-base font-bold text-foreground leading-tight">{ticker}</span>
            {companyName && (
              <span className="text-xs text-muted-foreground truncate">{companyName}</span>
            )}
          </div>

          {/* Remove button — visible only on hover */}
          {onRemove && (
            <button
              type="button"
              aria-label={`Remove ${ticker} from watchlist`}
              onClick={handleRemoveClick}
              className={cn(
                'opacity-0 group-hover:opacity-100 transition-opacity duration-150',
                'p-1 rounded-md text-muted-foreground',
                'hover:bg-destructive/10 hover:text-destructive',
                'flex-shrink-0 -mt-0.5 -mr-1'
              )}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>

        {/* ── Price row ── */}
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-xl font-semibold text-foreground">
            {price > 0 ? formatCurrency(price) : '—'}
          </span>

          {quote && (
            <span
              className={cn(
                'text-xs font-medium px-1.5 py-0.5 rounded',
                change > 0
                  ? 'bg-gain/10 text-gain'
                  : change < 0
                    ? 'bg-loss/10 text-loss'
                    : 'bg-muted text-muted-foreground'
              )}
            >
              {changeSign}{formatCurrency(change)} ({changeSign}{(changePct * 100).toFixed(2)}%)
            </span>
          )}
        </div>

        {/* ── Stats row ── */}
        {quote && (
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs text-muted-foreground">
              H: <span className="text-foreground">{formatCurrency(dayHigh)}</span>
            </span>
            <span className="text-xs text-muted-foreground">
              L: <span className="text-foreground">{formatCurrency(dayLow)}</span>
            </span>
            <span className="text-xs text-muted-foreground">
              Vol: <span className="text-foreground">{formatCompact(volume).replace('$', '')}</span>
            </span>
          </div>
        )}

        {/* ── Alert badge ── */}
        {item.alert_price !== undefined && item.alert_price > 0 && (
          <PriceAlertBadge
            alertPrice={item.alert_price}
            currentPrice={price}
            ticker={ticker}
          />
        )}

        {/* ── Footer: sparkline + buy button ── */}
        <div className="flex items-center justify-between gap-2 pt-1">
          {/* Sparkline */}
          <div className="flex items-center">
            {sparklineData && sparklineData.length > 1 ? (
              <SparklineChart
                data={sparklineData}
                positive={sparklinePositive}
                width={80}
                height={32}
              />
            ) : (
              <div className="w-20 h-8 flex items-center justify-center">
                <span className="text-xs text-muted-foreground">—</span>
              </div>
            )}
          </div>

          {/* Buy button */}
          {onBuy && (
            <button
              type="button"
              aria-label={`Buy ${ticker}`}
              onClick={handleBuyClick}
              className={cn(
                'px-3 py-1.5 text-xs font-medium rounded-md',
                'border border-border text-foreground',
                'hover:bg-primary hover:text-primary-foreground hover:border-primary',
                'transition-colors duration-150',
                'flex items-center gap-1.5'
              )}
            >
              <ShoppingCart className="h-3 w-3" aria-hidden="true" />
              Buy
            </button>
          )}
        </div>
      </div>

      {/* Confirm removal dialog */}
      <ConfirmDialog
        open={showConfirm}
        onOpenChange={setShowConfirm}
        title="Remove from Watchlist"
        description={`Remove ${ticker} from your watchlist?`}
        confirmLabel="Remove"
        cancelLabel="Cancel"
        onConfirm={handleConfirmRemove}
        destructive
      />
    </>
  )
}

export default WatchlistCard
