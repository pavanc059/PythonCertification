import { SkeletonCard } from '@/components/common/SkeletonCard'
import { SparklineChart } from '@/components/charts/SparklineChart'
import { formatCurrency, formatPercent } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import type { Position } from '@/api/portfolio'

interface PositionCardProps {
  position: Position
  isLoading?: boolean
  onSell?: () => void
  /** Optional sparkline price series */
  sparklineData?: number[]
}

export function PositionCard({
  position,
  isLoading = false,
  onSell,
  sparklineData,
}: PositionCardProps) {
  if (isLoading) {
    return <SkeletonCard lines={5} className="h-56" />
  }

  const {
    ticker,
    quantity,
    avg_entry_price,
    current_price,
    market_value,
    unrealized_pnl,
    unrealized_pnl_pct,
  } = position

  const pnlPositive = unrealized_pnl > 0
  const pnlSign = unrealized_pnl >= 0 ? '+' : ''

  return (
    <article
      className={cn(
        'bg-[#111827] border border-[#1f2d40] rounded-xl p-5 flex flex-col gap-3',
        'transition-all duration-200 hover:border-[#2d3f58] hover:bg-[#1a2235]',
        'focus-within:ring-2 focus-within:ring-[#6366f1]/40'
      )}
      aria-label={`Position: ${ticker}`}
    >
      {/* Header row: ticker + sell button */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-lg font-bold text-[#6366f1] tracking-wide leading-none">
            {ticker}
          </span>
        </div>
        <button
          type="button"
          onClick={onSell}
          aria-label={`Sell ${ticker}`}
          className={cn(
            'shrink-0 text-xs font-semibold px-3 py-1.5 rounded-md',
            'bg-[#FF4444]/15 text-[#FF4444] border border-[#FF4444]/30',
            'hover:bg-[#FF4444]/25 hover:border-[#FF4444]/50',
            'transition-colors duration-150',
            'focus:outline-none focus:ring-2 focus:ring-[#FF4444]/40'
          )}
        >
          Sell
        </button>
      </div>

      {/* Price row */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs text-[#475569] mb-0.5">Current</p>
          <p className="text-xl font-bold text-[#f1f5f9] leading-none">
            {formatCurrency(current_price)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-[#475569] mb-0.5">Avg entry</p>
          <p className="text-sm font-medium text-[#94a3b8] leading-none">
            {formatCurrency(avg_entry_price)}
          </p>
        </div>
      </div>

      {/* Shares + market value row */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs text-[#475569] mb-0.5">Shares</p>
          <p className="text-sm font-semibold text-[#f1f5f9]">{quantity}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-[#475569] mb-0.5">Market value</p>
          <p className="text-sm font-semibold text-[#f1f5f9]">{formatCurrency(market_value)}</p>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-[#1f2d40]" />

      {/* Unrealized P&L badge */}
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-[#475569]">Unrealized P&amp;L</p>
        <span
          className={cn(
            'inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full',
            pnlPositive
              ? 'bg-[#00C851]/15 text-[#00C851] border border-[#00C851]/25'
              : unrealized_pnl < 0
                ? 'bg-[#FF4444]/15 text-[#FF4444] border border-[#FF4444]/25'
                : 'bg-[#94a3b8]/10 text-[#94a3b8] border border-[#94a3b8]/20'
          )}
        >
          <span>
            {pnlSign}
            {formatCurrency(unrealized_pnl)}
          </span>
          <span className="opacity-75">
            ({pnlSign}
            {formatPercent(unrealized_pnl_pct)})
          </span>
        </span>
      </div>

      {/* Sparkline */}
      {sparklineData && sparklineData.length > 1 && (
        <div className="mt-1 -mx-1">
          <SparklineChart
            data={sparklineData}
            positive={unrealized_pnl >= 0}
            height={36}
          />
        </div>
      )}
    </article>
  )
}
