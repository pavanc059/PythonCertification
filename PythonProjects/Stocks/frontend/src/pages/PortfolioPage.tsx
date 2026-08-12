import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart2, RefreshCw } from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import { AccountSummaryCard } from '@/components/portfolio/AccountSummaryCard'
import { BenchmarkCard } from '@/components/portfolio/BenchmarkCard'
import { PerformanceMetricsGrid } from '@/components/portfolio/PerformanceMetricsGrid'
import { EquityCurveChart } from '@/components/portfolio/EquityCurveChart'
import { PositionCard } from '@/components/positions/PositionCard'
import { SkeletonCard } from '@/components/common/SkeletonCard'
import { PaperTradingBanner } from '@/components/trading/PaperTradingBanner'
import { getPortfolioSummary, getPositions, getPortfolioHistory } from '@/api/portfolio'
import { queryKeys } from '@/api/queryKeys'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import { useAuthStore } from '@/store/authStore'

/** Auto-refresh interval in milliseconds (60 seconds) */
const POSITIONS_REFETCH_INTERVAL = 60 * 1000

export default function PortfolioPage() {
  const user = useAuthStore((s) => s.user)
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date())

  // --- Queries ---

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useQuery({
    queryKey: queryKeys.portfolio.summary(),
    queryFn: getPortfolioSummary,
  })

  const {
    data: positions,
    isLoading: positionsLoading,
    isError: positionsError,
    dataUpdatedAt: positionsUpdatedAt,
  } = useQuery({
    queryKey: queryKeys.portfolio.positions(),
    queryFn: getPositions,
    refetchInterval: POSITIONS_REFETCH_INTERVAL,
  })

  const {
    data: history,
    isLoading: historyLoading,
    isError: historyError,
  } = useQuery({
    queryKey: queryKeys.portfolio.history(),
    queryFn: getPortfolioHistory,
  })

  // Update "last refreshed" stamp whenever positions data updates
  useEffect(() => {
    if (positionsUpdatedAt) {
      setLastRefreshed(new Date(positionsUpdatedAt))
    }
  }, [positionsUpdatedAt])

  // --- Derived values ---

  const openPositions = positions ?? []
  const closedTrades = history?.closed_trades ?? []
  const hasClosedTrades = closedTrades.length > 0

  // Realized P&L totals
  const realizedGains = closedTrades
    .filter((t) => t.realized_pnl > 0)
    .reduce((acc, t) => acc + t.realized_pnl, 0)
  const realizedLosses = closedTrades
    .filter((t) => t.realized_pnl < 0)
    .reduce((acc, t) => acc + t.realized_pnl, 0)
  const netRealizedPnl = realizedGains + realizedLosses

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl space-y-6">

          {/* Page header */}
          <header className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-[#f1f5f9]">
                Portfolio{user?.name ? ` — ${user.name}` : ''}
              </h1>
              <p className="mt-1 flex items-center gap-1.5 text-xs text-[#475569]">
                <RefreshCw className="h-3 w-3" aria-hidden="true" />
                Last refreshed: {formatDateTime(lastRefreshed)}
                <span className="ml-1 text-[#475569]">
                  (auto-refreshes every 60 s)
                </span>
              </p>
            </div>
          </header>

          {/* Paper trading banner */}
          <PaperTradingBanner />

          {/* Error banners */}
          {summaryError && (
            <div
              role="alert"
              className="rounded-lg border border-[#FF4444]/30 bg-[#FF4444]/10 px-4 py-3 text-sm text-[#FF4444]"
            >
              Failed to load account summary. Please try again.
            </div>
          )}
          {positionsError && (
            <div
              role="alert"
              className="rounded-lg border border-[#FF4444]/30 bg-[#FF4444]/10 px-4 py-3 text-sm text-[#FF4444]"
            >
              Failed to load positions data. Please try again.
            </div>
          )}
          {historyError && (
            <div
              role="alert"
              className="rounded-lg border border-[#FF4444]/30 bg-[#FF4444]/10 px-4 py-3 text-sm text-[#FF4444]"
            >
              Failed to load portfolio history. Please try again.
            </div>
          )}

          {/* Account summary — full width */}
          <section aria-labelledby="account-summary-heading">
            <h2 id="account-summary-heading" className="sr-only">Account Summary</h2>
            <AccountSummaryCard summary={summary} isLoading={summaryLoading} />
          </section>

          {/* Benchmark + Performance metrics — two columns on md+ */}
          <section
            aria-labelledby="performance-heading"
            className="grid grid-cols-1 gap-6 md:grid-cols-2"
          >
            <h2 id="performance-heading" className="sr-only">Performance</h2>
            <BenchmarkCard summary={summary} isLoading={summaryLoading} />
            <PerformanceMetricsGrid summary={summary} isLoading={summaryLoading} />
          </section>

          {/* Equity curve — full width */}
          <section aria-labelledby="equity-curve-heading">
            <h2 id="equity-curve-heading" className="sr-only">Equity Curve</h2>
            <EquityCurveChart />
          </section>

          {/* Open positions */}
          <section aria-labelledby="positions-heading">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <h2
                  id="positions-heading"
                  className="text-lg font-semibold text-[#f1f5f9]"
                >
                  Open Positions
                </h2>
                {!positionsLoading && (
                  <span className="rounded-full bg-[#6366f1]/15 px-2.5 py-0.5 text-xs font-semibold text-[#6366f1]">
                    {openPositions.length}{' '}
                    {openPositions.length === 1 ? 'position' : 'positions'}
                  </span>
                )}
              </div>
            </div>

            {/* Loading skeleton */}
            {positionsLoading && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <SkeletonCard key={i} lines={5} className="h-56" />
                ))}
              </div>
            )}

            {/* Empty state */}
            {!positionsLoading && openPositions.length === 0 && (
              <div className="flex flex-col items-center justify-center rounded-xl border border-[#1f2d40] bg-[#111827] px-8 py-16 text-center">
                <BarChart2
                  className="mb-4 h-12 w-12 text-[#475569]"
                  aria-hidden="true"
                />
                <h3 className="text-base font-semibold text-[#94a3b8]">
                  No Open Positions
                </h3>
                <p className="mt-2 text-sm text-[#475569]">
                  Place your first trade to get started.
                </p>
                <Link
                  to="/trading"
                  className="mt-6 inline-flex items-center rounded-lg bg-[#6366f1] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#4f52d9] focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50"
                >
                  Go to Trading
                </Link>
              </div>
            )}

            {/* Position cards grid */}
            {!positionsLoading && openPositions.length > 0 && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {openPositions.map((position) => (
                  <PositionCard
                    key={position.ticker}
                    position={position}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Realized P&L section */}
          {(hasClosedTrades || historyLoading) && (
            <section aria-labelledby="realized-pnl-heading">
              <h2
                id="realized-pnl-heading"
                className="mb-4 text-lg font-semibold text-[#f1f5f9]"
              >
                Realized P&amp;L
              </h2>

              {historyLoading ? (
                <SkeletonCard lines={3} />
              ) : (
                <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-6">
                  <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                    <div>
                      <p className="text-xs text-[#475569] mb-1">Total Gains</p>
                      <p className="text-xl font-bold text-[#00C851]">
                        +{formatCurrency(realizedGains)}
                      </p>
                      <p className="mt-1 text-xs text-[#475569]">
                        From {closedTrades.filter((t) => t.realized_pnl > 0).length} winning trade(s)
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[#475569] mb-1">Total Losses</p>
                      <p className="text-xl font-bold text-[#FF4444]">
                        {formatCurrency(realizedLosses)}
                      </p>
                      <p className="mt-1 text-xs text-[#475569]">
                        From {closedTrades.filter((t) => t.realized_pnl < 0).length} losing trade(s)
                      </p>
                    </div>
                    <div className="sm:border-l sm:border-[#1f2d40] sm:pl-6">
                      <p className="text-xs text-[#475569] mb-1">Net Realized P&amp;L</p>
                      <p
                        className={`text-xl font-bold ${
                          netRealizedPnl > 0
                            ? 'text-[#00C851]'
                            : netRealizedPnl < 0
                              ? 'text-[#FF4444]'
                              : 'text-[#94a3b8]'
                        }`}
                      >
                        {netRealizedPnl >= 0 ? '+' : ''}
                        {formatCurrency(netRealizedPnl)}
                      </p>
                      <p className="mt-1 text-xs text-[#475569]">
                        Across {closedTrades.length} closed trade(s)
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </section>
          )}

        </div>
      </main>
    </PageTransition>
  )
}
