import { BarChart2 } from 'lucide-react'
import { SkeletonCard } from '@/components/common/SkeletonCard'
import { formatCurrency, formatPercent, getPnlClass } from '@/lib/formatters'
import type { PortfolioSummary } from '@/api/portfolio'

interface AccountSummaryCardProps {
  summary: PortfolioSummary | undefined
  isLoading: boolean
}

export function AccountSummaryCard({ summary, isLoading }: AccountSummaryCardProps) {
  if (isLoading) {
    return <SkeletonCard lines={4} className="h-40" />
  }

  if (!summary) {
    return (
      <div className="bg-card border border-border rounded-xl p-6 flex items-center justify-center h-40">
        <p className="text-muted-foreground text-sm">Unable to load account data</p>
      </div>
    )
  }

  const returnPctClass = getPnlClass(summary.total_return_pct)
  const unrealizedClass = getPnlClass(summary.unrealized_pnl)
  const returnSign = summary.total_return >= 0 ? '+' : '-'
  const returnAbsolute = formatCurrency(Math.abs(summary.total_return))

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      {/* Header row */}
      <div className="flex items-start justify-between mb-3">
        <span className="text-sm text-muted-foreground font-medium">Total Account Value</span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/40 px-2 py-1 rounded-md">
          <BarChart2 className="h-3.5 w-3.5" />
          Paper Trading Mode
        </span>
      </div>

      {/* Hero value + total return */}
      <div className="flex items-end gap-4 mb-5">
        <span className="text-3xl font-bold text-foreground tracking-tight">
          {formatCurrency(summary.total_value)}
        </span>
        <span className={`text-sm font-semibold mb-0.5 ${returnPctClass}`}>
          {summary.total_return_pct >= 0 ? '▲' : '▼'}{' '}
          {formatPercent(summary.total_return_pct)} ({returnSign}{returnAbsolute})
        </span>
      </div>

      {/* Divider */}
      <div className="border-t border-border mb-4" />

      {/* Bottom metrics row */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Cash Available</p>
          <p className="text-sm font-semibold text-foreground">{formatCurrency(summary.cash)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Buying Power</p>
          <p className="text-sm font-semibold text-foreground">
            {formatCurrency(summary.buying_power)}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Unrealized P&amp;L</p>
          <p className={`text-sm font-semibold ${unrealizedClass}`}>
            {summary.unrealized_pnl >= 0 ? '+' : ''}
            {formatCurrency(summary.unrealized_pnl)}
          </p>
        </div>
      </div>
    </div>
  )
}
