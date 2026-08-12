import { SkeletonCard } from '@/components/common/SkeletonCard'
import { formatPercent, getPnlClass } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import type { PortfolioSummary } from '@/api/portfolio'

interface BenchmarkCardProps {
  summary: PortfolioSummary | undefined
  isLoading: boolean
}

// The backend BenchmarkComparison schema has different field names than the frontend Benchmark type.
// We handle both shapes here.
interface BenchmarkShape {
  // Frontend Benchmark type fields
  ticker?: string
  return_pct?: number
  // Backend BenchmarkComparison schema fields
  benchmark_ticker?: string
  benchmark_return_pct?: number
  portfolio_return_pct?: number
  alpha?: number
  performance?: string
}

function getBenchmarkReturn(bm: BenchmarkShape): number {
  if (typeof bm.return_pct === 'number') return bm.return_pct
  if (typeof bm.benchmark_return_pct === 'number') return bm.benchmark_return_pct
  return 0
}

function getBenchmarkTicker(bm: BenchmarkShape): string {
  return bm.ticker ?? bm.benchmark_ticker ?? 'SPY'
}

function getAlpha(bm: BenchmarkShape, portfolioReturnPct: number): number {
  if (typeof bm.alpha === 'number') return bm.alpha
  return portfolioReturnPct - getBenchmarkReturn(bm)
}

function getPerformance(bm: BenchmarkShape): string | undefined {
  return bm.performance
}

const PERFORMANCE_BADGE: Record<string, { label: string; className: string }> = {
  outperforming: { label: 'Outperforming', className: 'bg-gain/15 text-gain' },
  underperforming: { label: 'Underperforming', className: 'bg-loss/15 text-loss' },
  matching: { label: 'Matching', className: 'bg-muted text-muted-foreground' },
}

export function BenchmarkCard({ summary, isLoading }: BenchmarkCardProps) {
  if (isLoading) {
    return <SkeletonCard lines={4} />
  }

  // No benchmark data available
  if (!summary?.benchmark) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <p className="text-sm text-muted-foreground font-medium mb-4">Benchmark Comparison</p>
        <div className="flex items-center justify-center h-24">
          <p className="text-sm text-muted-foreground">Benchmark data unavailable</p>
        </div>
      </div>
    )
  }

  const bm = summary.benchmark as unknown as BenchmarkShape
  const benchmarkReturn = getBenchmarkReturn(bm)
  const benchmarkTicker = getBenchmarkTicker(bm)
  const alpha = getAlpha(bm, summary.total_return_pct)
  const performance = getPerformance(bm)

  const portfolioClass = getPnlClass(summary.total_return_pct)
  const benchmarkClass = getPnlClass(benchmarkReturn)
  const alphaClass = getPnlClass(alpha)

  const perfBadge =
    performance && PERFORMANCE_BADGE[performance]
      ? PERFORMANCE_BADGE[performance]
      : undefined

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground font-medium">Benchmark Comparison</p>
        {perfBadge && (
          <span className={cn('text-xs font-semibold px-2 py-0.5 rounded-full', perfBadge.className)}>
            {perfBadge.label}
          </span>
        )}
      </div>

      {/* Side-by-side returns */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Your Portfolio</p>
          <p className={cn('text-2xl font-bold', portfolioClass)}>
            {formatPercent(summary.total_return_pct)}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">{benchmarkTicker}</p>
          <p className={cn('text-2xl font-bold', benchmarkClass)}>
            {formatPercent(benchmarkReturn)}
          </p>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-border mb-3" />

      {/* Alpha row */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">Alpha</span>
        <span className={cn('text-sm font-semibold', alphaClass)}>
          {alpha >= 0 ? '+' : ''}
          {formatPercent(alpha)}
        </span>
      </div>
    </div>
  )
}
