import { SkeletonCard } from '@/components/common/SkeletonCard'
import { formatCurrency } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import type { PortfolioSummary } from '@/api/portfolio'

interface PerformanceMetricsGridProps {
  summary: PortfolioSummary | undefined
  isLoading: boolean
}

interface MetricItem {
  label: string
  value: string
  subtext: string
  valueClass?: string
  extra?: React.ReactNode
}

/** Thin horizontal progress bar for win rate visualisation */
function WinRateBar({ rate }: { rate: number }) {
  const pct = Math.min(Math.max(rate * 100, 0), 100)
  return (
    <div className="mt-2 h-1.5 w-full bg-muted rounded-full overflow-hidden">
      <div
        className="h-full rounded-full bg-gain transition-all"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export function PerformanceMetricsGrid({ summary, isLoading }: PerformanceMetricsGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card border border-border rounded-lg p-4 h-20" />
        ))}
      </div>
    )
  }

  const winRatePct = (summary.win_rate * 100).toFixed(1)

  const metrics: MetricItem[] = [
    {
      label: 'Win Rate',
      value: `${winRatePct}%`,
      subtext: `${summary.num_winning_trades}W / ${summary.num_losing_trades}L`,
      // No extra color — win rate is neutral metric
    },
    {
      label: 'Total Trades',
      value: `${summary.num_trades}`,
      subtext: 'Completed trades',
    },
    {
      label: 'Avg Win',
      value: formatCurrency(summary.avg_win),
      subtext: 'Per winning trade',
      valueClass: 'text-gain',
    },
    {
      label: 'Avg Loss',
      value: `-${formatCurrency(Math.abs(summary.avg_loss))}`,
      subtext: 'Per losing trade',
      valueClass: 'text-loss',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-4">
      {metrics.map((metric, idx) => (
        <div
          key={metric.label}
          className="bg-card border border-border rounded-lg p-4 flex flex-col gap-1"
        >
          <p className="text-xs text-muted-foreground font-medium">{metric.label}</p>
          <p className={cn('text-xl font-bold text-foreground', metric.valueClass)}>
            {metric.value}
          </p>
          <p className="text-xs text-muted-foreground">{metric.subtext}</p>

          {/* Win rate progress bar on the first card */}
          {idx === 0 && <WinRateBar rate={summary.win_rate} />}
        </div>
      ))}
    </div>
  )
}
