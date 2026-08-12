import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Wallet, TrendingUp, DollarSign, BarChart2, Bookmark,
  ArrowRight, Activity, Newspaper, Zap, Rss, BellRing,
  TrendingDown, Building2, Brain,
} from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import { MetricCard } from '@/components/common/MetricCard'
import { GlassCard } from '@/components/common/GlassCard'
import { EquityCurveChart } from '@/components/portfolio/EquityCurveChart'
import { SkeletonCard } from '@/components/common/SkeletonCard'
import { SkeletonPulse } from '@/components/common/SkeletonPulse'
import { PaperTradingBanner } from '@/components/trading/PaperTradingBanner'
import { getPortfolioSummary, getPositions } from '@/api/portfolio'
import { getOrders } from '@/api/trading'
import { getSnapshot, getMovers, getInstitutional } from '@/api/market'
import { getGuruTrades } from '@/api/ai'
import type { GuruTrade } from '@/api/ai'
import { queryKeys } from '@/api/queryKeys'
import { useAuthStore } from '@/store/authStore'
import { formatCurrency, formatPercent, getPnlClass, formatDate } from '@/lib/formatters'
import { cn } from '@/lib/utils'

// ─── helpers ────────────────────────────────────────────────────────────────

function pctClass(value: number | undefined) {
  if (value === undefined) return 'text-[#94a3b8]'
  return value >= 0 ? 'text-[#00C851]' : 'text-[#FF4444]'
}

function pctLabel(value: number | undefined): string {
  if (value === undefined) return '--'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function formatVol(vol: number): string {
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(0)}K`
  return String(vol)
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)

  // --- Queries ---

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: queryKeys.portfolio.summary(),
    queryFn: getPortfolioSummary,
    staleTime: 30_000,
    refetchInterval: 30_000,
  })

  const { data: positions, isLoading: positionsLoading } = useQuery({
    queryKey: queryKeys.portfolio.positions(),
    queryFn: getPositions,
    staleTime: 30_000,
    refetchInterval: 30_000,
  })

  const { data: orders, isLoading: ordersLoading } = useQuery({
    queryKey: queryKeys.trading.orders(),
    queryFn: getOrders,
    staleTime: 30_000,
  })

  const { data: snapshot, isLoading: snapshotLoading } = useQuery({
    queryKey: queryKeys.market.snapshot(),
    queryFn: getSnapshot,
    staleTime: 30_000,
    refetchInterval: 30_000,
    throwOnError: false,
  })

  const { data: movers, isLoading: moversLoading } = useQuery({
    queryKey: queryKeys.market.movers(),
    queryFn: getMovers,
    staleTime: 60_000,
    refetchInterval: 60_000,
    throwOnError: false,
  })

  // Institutional holdings for a curated watchlist of top S&P 500 stocks
  const TOP_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'BRK-B', 'JPM', 'V']
  const { data: institutionalData, isLoading: instLoading } = useQuery({
    queryKey: ['market', 'institutional', 'top10'],
    queryFn: () => Promise.all(TOP_TICKERS.map((t) => getInstitutional(t, 3))),
    staleTime: 3_600_000,  // 1h — changes daily
    throwOnError: false,
  })

  // Guru daily trades
  const { data: guruTradesData, isLoading: guruTradesLoading } = useQuery({
    queryKey: ['ai', 'guru-trades'],
    queryFn: () => getGuruTrades(7),
    staleTime: 3_600_000,
    throwOnError: false,
  })

  // --- Derived data ---

  const topPositions = [...(positions ?? [])]
    .sort((a, b) => b.market_value - a.market_value)
    .slice(0, 10)

  const recentTrades = [...(orders ?? [])]
    .filter((o) => o.status === 'filled')
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5)

  const topGainers = (movers?.gainers ?? []).slice(0, 10)
  const topLosers = (movers?.losers ?? []).slice(0, 10)

  // Flatten institutional data: collect top holder per ticker
  const topInstitutional = (institutionalData ?? [])
    .flatMap((d) => (d?.holders ?? []).slice(0, 1).map((h) => ({ ...h, ticker: d.ticker })))
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl space-y-6">

          {/* Page header */}
          <header>
            <h1 className="text-2xl font-bold text-[#f1f5f9]">
              Welcome back, {user?.name ?? 'Trader'} 👋
            </h1>
            <p className="mt-1 text-sm text-[#475569]">
              Here's your account overview
            </p>
          </header>

          {/* Paper trading banner */}
          <PaperTradingBanner />

          {/* Metric cards row */}
          <section aria-labelledby="metrics-heading">
            <h2 id="metrics-heading" className="sr-only">Key Metrics</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="Total Account Value"
                value={summary ? formatCurrency(summary.total_value) : '--'}
                icon={<Wallet className="h-4 w-4" />}
                isLoading={summaryLoading}
              />
              <MetricCard
                title="Day P&L"
                value={summary ? formatCurrency(summary.day_pnl ?? summary.unrealized_pnl) : '--'}
                icon={<TrendingUp className="h-4 w-4" />}
                isLoading={summaryLoading}
                className={summary ? cn(getPnlClass(summary.day_pnl ?? summary.unrealized_pnl)) : undefined}
              />
              <MetricCard
                title="Total Return"
                value={summary ? formatPercent(summary.total_return_pct / 100) : '--'}
                icon={<Activity className="h-4 w-4" />}
                isLoading={summaryLoading}
                className={summary ? cn(getPnlClass(summary.total_return_pct)) : undefined}
              />
              <MetricCard
                title="Buying Power"
                value={summary ? formatCurrency(summary.buying_power) : '--'}
                icon={<DollarSign className="h-4 w-4" />}
                isLoading={summaryLoading}
              />
            </div>
          </section>

          {/* ── Market Snapshot ─────────────────────────────────────────────── */}
          <section aria-labelledby="market-snapshot-heading">
            <h2
              id="market-snapshot-heading"
              className="mb-4 text-base font-semibold text-[#f1f5f9]"
            >
              Market Snapshot
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {/* S&P 500 */}
              <GlassCard noHover className="p-5">
                <p className="text-xs font-medium text-[#475569] uppercase tracking-wider mb-2">
                  S&amp;P 500
                </p>
                {snapshotLoading ? (
                  <SkeletonPulse className="h-7 w-20" />
                ) : (
                  <p
                    className={cn(
                      'text-2xl font-bold',
                      pctClass(snapshot?.sp500_change_pct)
                    )}
                  >
                    {pctLabel(snapshot?.sp500_change_pct)}
                  </p>
                )}
                <p className="mt-1 text-xs text-[#475569]">Today's change</p>
              </GlassCard>

              {/* NASDAQ */}
              <GlassCard noHover className="p-5">
                <p className="text-xs font-medium text-[#475569] uppercase tracking-wider mb-2">
                  NASDAQ
                </p>
                {snapshotLoading ? (
                  <SkeletonPulse className="h-7 w-20" />
                ) : (
                  <p
                    className={cn(
                      'text-2xl font-bold',
                      pctClass(snapshot?.nasdaq_change_pct)
                    )}
                  >
                    {pctLabel(snapshot?.nasdaq_change_pct)}
                  </p>
                )}
                <p className="mt-1 text-xs text-[#475569]">Today's change</p>
              </GlassCard>

              {/* VIX */}
              <GlassCard noHover className="p-5">
                <p className="text-xs font-medium text-[#475569] uppercase tracking-wider mb-2">
                  VIX
                </p>
                {snapshotLoading ? (
                  <SkeletonPulse className="h-7 w-20" />
                ) : (
                  <p className="text-2xl font-bold text-[#f1f5f9]">
                    {snapshot?.vix !== undefined ? snapshot.vix.toFixed(2) : '--'}
                  </p>
                )}
                <p className="mt-1 text-xs text-[#475569]">Volatility index</p>
              </GlassCard>
            </div>
          </section>

          {/* ── Top Movers (compact) ─────────────────────────────────────────── */}
          <section aria-labelledby="top-movers-heading">
            <div className="mb-4 flex items-center justify-between">
              <h2
                id="top-movers-heading"
                className="text-base font-semibold text-[#f1f5f9]"
              >
                Top 10 Movers
              </h2>
              <Link
                to="/market"
                className="flex items-center gap-1 text-xs text-[#6366f1] hover:text-[#818cf8] transition-colors"
              >
                See all <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {/* Gainers */}
              <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-4">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="h-4 w-4 text-[#00C851]" aria-hidden="true" />
                  <span className="text-sm font-semibold text-[#00C851]">Top Gainers</span>
                </div>
                {moversLoading ? (
                  <div className="space-y-2">
                    {[0, 1, 2].map((i) => (
                      <SkeletonPulse key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {topGainers.length > 0 ? topGainers.map((mover) => (
                      <div
                        key={mover.ticker}
                        className="flex items-center justify-between rounded-lg bg-[#0a0e1a] px-3 py-2"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-sm font-bold text-[#6366f1] w-14 shrink-0">
                            {mover.ticker}
                          </span>
                          <span className="text-xs text-[#475569] truncate hidden sm:block">
                            {mover.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 shrink-0 ml-2">
                          <span className="text-xs text-[#94a3b8]">
                            ${mover.current_price.toFixed(2)}
                          </span>
                          <span className="text-xs font-semibold text-[#00C851]">
                            +{mover.price_change_pct.toFixed(2)}%
                          </span>
                          {mover.has_unusual_volume && (
                            <span title="Unusual volume" aria-label="Unusual volume">🔥</span>
                          )}
                        </div>
                      </div>
                    )) : (
                      <MoverPlaceholderRows />
                    )}
                  </div>
                )}
              </div>

              {/* Losers */}
              <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-4">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingDown className="h-4 w-4 text-[#FF4444]" aria-hidden="true" />
                  <span className="text-sm font-semibold text-[#FF4444]">Top Losers</span>
                </div>
                {moversLoading ? (
                  <div className="space-y-2">
                    {[0, 1, 2].map((i) => (
                      <SkeletonPulse key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {topLosers.length > 0 ? topLosers.map((mover) => (
                      <div
                        key={mover.ticker}
                        className="flex items-center justify-between rounded-lg bg-[#0a0e1a] px-3 py-2"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-sm font-bold text-[#6366f1] w-14 shrink-0">
                            {mover.ticker}
                          </span>
                          <span className="text-xs text-[#475569] truncate hidden sm:block">
                            {mover.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 shrink-0 ml-2">
                          <span className="text-xs text-[#94a3b8]">
                            ${mover.current_price.toFixed(2)}
                          </span>
                          <span className="text-xs font-semibold text-[#FF4444]">
                            {mover.price_change_pct.toFixed(2)}%
                          </span>
                          <span className="text-xs text-[#475569]">
                            {formatVol(mover.volume)}
                          </span>
                        </div>
                      </div>
                    )) : (
                      <MoverPlaceholderRows />
                    )}
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Equity curve */}
          <section aria-labelledby="equity-curve-heading">
            <h2 id="equity-curve-heading" className="sr-only">Equity Curve</h2>
            <EquityCurveChart />
          </section>

          {/* Bottom row: Top Positions + Recent Trades */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

            {/* Top Positions */}
            <section
              aria-labelledby="top-positions-heading"
              className="rounded-xl border border-[#1f2d40] bg-[#111827] p-5"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2
                  id="top-positions-heading"
                  className="text-base font-semibold text-[#f1f5f9]"
                >
                  Top Positions
                </h2>
                <Link
                  to="/portfolio"
                  className="flex items-center gap-1 text-xs text-[#6366f1] hover:text-[#818cf8] transition-colors"
                >
                  View all <ArrowRight className="h-3 w-3" />
                </Link>
              </div>

              {positionsLoading && (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <SkeletonCard key={i} lines={2} className="h-16" />
                  ))}
                </div>
              )}

              {!positionsLoading && topPositions.length === 0 && (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <BarChart2 className="mb-2 h-8 w-8 text-[#475569]" aria-hidden="true" />
                  <p className="text-sm text-[#94a3b8]">No open positions</p>
                  <Link
                    to="/trading"
                    className="mt-3 text-xs text-[#6366f1] hover:text-[#818cf8] transition-colors"
                  >
                    Start trading →
                  </Link>
                </div>
              )}

              {!positionsLoading && topPositions.length > 0 && (
                <div className="space-y-2">
                  {/* Column headers */}
                  <div className="grid grid-cols-5 gap-2 px-1 pb-1 border-b border-[#1f2d40]">
                    <span className="col-span-2 text-xs text-[#475569]">Ticker</span>
                    <span className="text-xs text-[#475569] text-right">Price</span>
                    <span className="text-xs text-[#475569] text-right">Day%</span>
                    <span className="text-xs text-[#475569] text-right">P&L</span>
                  </div>
                  {topPositions.map((position) => {
                    const pnlPositive = position.unrealized_pnl > 0
                    const pnlNeutral = position.unrealized_pnl === 0
                    const dayPct = position.day_change_pct
                    return (
                      <div
                        key={position.ticker}
                        className="grid grid-cols-5 gap-2 items-center rounded-lg border border-[#1f2d40] bg-[#0a0e1a] px-3 py-2 hover:border-[#2d3f58] transition-colors"
                      >
                        <div className="col-span-2 flex items-center gap-2 min-w-0">
                          <span className="text-sm font-bold text-[#6366f1] shrink-0">{position.ticker}</span>
                          <span className="text-xs text-[#475569] truncate">{position.quantity} sh</span>
                        </div>
                        <span className="text-xs text-[#f1f5f9] text-right tabular-nums">
                          {formatCurrency(position.current_price)}
                        </span>
                        <span className={cn('text-xs font-semibold text-right tabular-nums',
                          dayPct == null ? 'text-[#475569]' : dayPct >= 0 ? 'text-[#00C851]' : 'text-[#FF4444]')}>
                          {dayPct == null ? '--' : `${dayPct >= 0 ? '+' : ''}${dayPct.toFixed(2)}%`}
                        </span>
                        <span className={cn('text-xs font-semibold text-right tabular-nums',
                          pnlPositive ? 'text-[#00C851]' : pnlNeutral ? 'text-[#94a3b8]' : 'text-[#FF4444]')}>
                          {position.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(position.unrealized_pnl)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </section>

            {/* Recent Trades */}
            <section
              aria-labelledby="recent-trades-heading"
              className="rounded-xl border border-[#1f2d40] bg-[#111827] p-5"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2
                  id="recent-trades-heading"
                  className="text-base font-semibold text-[#f1f5f9]"
                >
                  Recent Trades
                </h2>
                <Link
                  to="/trading"
                  className="flex items-center gap-1 text-xs text-[#6366f1] hover:text-[#818cf8] transition-colors"
                >
                  View all <ArrowRight className="h-3 w-3" />
                </Link>
              </div>

              {ordersLoading && (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <SkeletonCard key={i} lines={1} className="h-10" />
                  ))}
                </div>
              )}

              {!ordersLoading && recentTrades.length === 0 && (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <Activity className="mb-2 h-8 w-8 text-[#475569]" aria-hidden="true" />
                  <p className="text-sm text-[#94a3b8]">No filled orders yet</p>
                  <Link
                    to="/trading"
                    className="mt-3 text-xs text-[#6366f1] hover:text-[#818cf8] transition-colors"
                  >
                    Place a trade →
                  </Link>
                </div>
              )}

              {!ordersLoading && recentTrades.length > 0 && (
                <div className="space-y-2">
                  {/* Column headers */}
                  <div className="grid grid-cols-5 gap-2 px-1 pb-1 border-b border-[#1f2d40]">
                    <span className="text-xs text-[#475569]">Date</span>
                    <span className="text-xs text-[#475569]">Ticker</span>
                    <span className="text-xs text-[#475569]">Side</span>
                    <span className="text-xs text-[#475569]">Qty</span>
                    <span className="text-xs text-[#475569] text-right">Fill Price</span>
                  </div>
                  {recentTrades.map((order) => (
                    <div
                      key={order.order_id}
                      className="grid grid-cols-5 gap-2 items-center px-1 py-1.5 rounded hover:bg-[#0a0e1a] transition-colors"
                    >
                      <span className="text-xs text-[#94a3b8] truncate">
                        {formatDate(order.created_at)}
                      </span>
                      <span className="text-xs font-bold text-[#6366f1]">
                        {order.ticker}
                      </span>
                      <span
                        className={cn(
                          'text-xs font-semibold capitalize',
                          order.side === 'buy' ? 'text-[#00C851]' : 'text-[#FF4444]'
                        )}
                      >
                        {order.side === 'buy' ? 'Buy' : 'Sell'}
                      </span>
                      <span className="text-xs text-[#f1f5f9]">
                        {order.quantity}
                      </span>
                      <span className="text-xs text-[#f1f5f9] text-right">
                        {order.filled_price != null
                          ? formatCurrency(order.filled_price)
                          : '--'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* ── Guru Daily Trades ───────────────────────────────────────── */}
          <section aria-labelledby="guru-trades-heading">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-[#6366f1]" aria-hidden="true" />
                <h2 id="guru-trades-heading" className="text-base font-semibold text-[#f1f5f9]">
                  Top 10 Guru Trades
                </h2>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-[#475569]">Last 7 days · Form 4 + 13F + Web</span>
                <Link to="/ai-research" className="flex items-center gap-1 text-xs text-[#6366f1] hover:text-[#818cf8] transition-colors">
                  AI Research <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>

            <div className="rounded-xl border border-[#1f2d40] bg-[#111827] overflow-hidden">
              {/* Column headers */}
              <div className="grid grid-cols-6 gap-2 px-4 py-2 border-b border-[#1f2d40] bg-[#0d1424]">
                <span className="col-span-2 text-xs font-medium text-[#475569] uppercase tracking-wide">Guru</span>
                <span className="text-xs font-medium text-[#475569] uppercase tracking-wide">Ticker</span>
                <span className="text-xs font-medium text-[#475569] uppercase tracking-wide text-center">Action</span>
                <span className="text-xs font-medium text-[#475569] uppercase tracking-wide text-right">Shares / Info</span>
                <span className="text-xs font-medium text-[#475569] uppercase tracking-wide text-right">Source</span>
              </div>

              {guruTradesLoading ? (
                <div className="p-4 space-y-2">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="h-9 animate-pulse rounded bg-[#1a2235]" />
                  ))}
                </div>
              ) : !guruTradesData?.trades?.length ? (
                <div className="p-6 flex flex-col items-center gap-2 text-center">
                  <Brain className="h-8 w-8 text-[#1f2d40]" />
                  <p className="text-sm text-[#475569]">
                    No recent guru filings found. Data updates when new Form 4 or 13F amendments are filed.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-[#1a2235]">
                  {guruTradesData.trades.slice(0, 10).map((trade: GuruTrade, i: number) => {
                    const isBuy = trade.action === 'BUY'
                    const isSell = trade.action === 'SELL'
                    const isFiled = trade.action === 'FILED'
                    const confColor = trade.confidence === 'high'
                      ? 'text-green-400' : trade.confidence === 'medium'
                      ? 'text-amber-400' : 'text-[#475569]'
                    return (
                      <div key={i} className="grid grid-cols-6 gap-2 items-center px-4 py-2.5 hover:bg-[#0a0e1a] transition-colors">
                        {/* Guru name */}
                        <div className="col-span-2 min-w-0">
                          <p className="text-xs font-semibold text-[#f1f5f9] truncate">
                            {trade.guru.includes('(')
                              ? trade.guru.split('(')[1].replace(')', '')
                              : trade.guru.split(' ')[0]}
                          </p>
                          <p className="text-[10px] text-[#475569] truncate">{trade.date}</p>
                        </div>

                        {/* Ticker */}
                        {trade.ticker !== 'portfolio' && trade.ticker !== 'news' ? (
                          <Link to={`/stock/${trade.ticker}`}
                            className="text-sm font-bold text-[#6366f1] hover:text-[#818cf8] transition-colors">
                            {trade.ticker}
                          </Link>
                        ) : (
                          <span className="text-xs text-[#475569]">—</span>
                        )}

                        {/* Action badge */}
                        <div className="flex justify-center">
                          <span className={cn(
                            'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold',
                            isBuy  ? 'bg-green-500/15 text-green-400 border border-green-500/30' :
                            isSell ? 'bg-red-500/15 text-red-400 border border-red-500/30' :
                            isFiled? 'bg-[#6366f1]/15 text-[#6366f1] border border-[#6366f1]/30' :
                                     'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                          )}>
                            {isBuy ? '▲ BUY' : isSell ? '▼ SELL' : isFiled ? '📄 FILED' : '📰 NEWS'}
                          </span>
                        </div>

                        {/* Shares / title */}
                        <div className="text-right min-w-0">
                          {trade.shares ? (
                            <p className="text-xs text-[#94a3b8] tabular-nums">
                              {trade.shares >= 1_000_000
                                ? `${(trade.shares / 1_000_000).toFixed(1)}M`
                                : trade.shares >= 1_000
                                  ? `${(trade.shares / 1_000).toFixed(0)}K`
                                  : trade.shares.toLocaleString()} sh
                            </p>
                          ) : trade.title ? (
                            <p className="text-[10px] text-[#475569] truncate" title={trade.title}>
                              {trade.title.slice(0, 30)}…
                            </p>
                          ) : (
                            <span className="text-xs text-[#475569]">—</span>
                          )}
                          {trade.price ? (
                            <p className="text-[10px] text-[#475569]">${trade.price.toFixed(2)}</p>
                          ) : null}
                        </div>

                        {/* Source + confidence */}
                        <div className="text-right min-w-0">
                          <p className={cn('text-[10px] font-semibold truncate', confColor)}>
                            {trade.confidence === 'high' ? '●' : trade.confidence === 'medium' ? '◑' : '○'}
                            {' '}{trade.source.includes('Finnhub') ? 'Form 4' : trade.source.includes('13F') ? '13F' : 'Web'}
                          </p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </section>

          {/* ── Institutional Holdings (Top Stocks by Smart Money) ──────── */}
          <section aria-labelledby="institutional-heading">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-[#6366f1]" aria-hidden="true" />
                <h2 id="institutional-heading" className="text-base font-semibold text-[#f1f5f9]">
                  Top Stocks by Institutional Holders
                </h2>
              </div>
              <span className="text-xs text-[#475569]">Top 10 S&amp;P 500 by smart-money ownership</span>
            </div>

            <div className="rounded-xl border border-[#1f2d40] bg-[#111827] overflow-hidden">
              {/* Column headers */}
              <div className="grid grid-cols-6 gap-2 px-4 py-2 border-b border-[#1f2d40] bg-[#0d1424]">
                <span className="text-xs font-medium text-[#475569] uppercase tracking-wide">Ticker</span>
                <span className="col-span-2 text-xs font-medium text-[#475569] uppercase tracking-wide">Top Holder</span>
                <span className="text-xs font-medium text-[#475569] uppercase tracking-wide text-right">Shares</span>
                <span className="text-xs font-medium text-[#475569] uppercase tracking-wide text-right">% Held</span>
                <span className="text-xs font-medium text-[#475569] uppercase tracking-wide text-right">Value</span>
              </div>

              {instLoading ? (
                <div className="p-4 space-y-2">
                  {[...Array(8)].map((_, i) => (
                    <div key={i} className="h-8 animate-pulse rounded bg-[#1a2235]" />
                  ))}
                </div>
              ) : (
                <div className="divide-y divide-[#1a2235]">
                  {topInstitutional.length === 0 ? (
                    <p className="p-4 text-xs text-[#475569]">Institutional data unavailable.</p>
                  ) : topInstitutional.map((h, i) => {
                    const isInst = h.type === 'institution'
                    const shares = h.shares ? (h.shares >= 1_000_000 ? `${(h.shares / 1_000_000).toFixed(1)}M` : h.shares >= 1_000 ? `${(h.shares / 1_000).toFixed(0)}K` : String(h.shares)) : '--'
                    const value = h.value ? (h.value >= 1_000_000_000 ? `$${(h.value / 1_000_000_000).toFixed(1)}B` : h.value >= 1_000_000 ? `$${(h.value / 1_000_000).toFixed(0)}M` : `$${h.value.toFixed(0)}`) : '--'
                    return (
                      <div key={i} className="grid grid-cols-6 gap-2 items-center px-4 py-2.5 hover:bg-[#0a0e1a] transition-colors">
                        <Link to={`/stock/${(h as any).ticker}`} className="text-sm font-bold text-[#6366f1] hover:text-[#818cf8] transition-colors">
                          {(h as any).ticker}
                        </Link>
                        <div className="col-span-2 flex items-center gap-2 min-w-0">
                          <span className={cn('shrink-0 rounded px-1 py-px text-[9px] font-bold uppercase tracking-wide',
                            isInst ? 'bg-[#6366f1]/15 text-[#6366f1]' : 'bg-amber-500/15 text-amber-400')}>
                            {isInst ? 'Inst' : 'Fund'}
                          </span>
                          <span className="text-xs text-[#94a3b8] truncate">{h.holder}</span>
                        </div>
                        <span className="text-xs text-[#94a3b8] text-right tabular-nums">{shares}</span>
                        <span className="text-xs text-[#94a3b8] text-right tabular-nums">
                          {h.pct_held != null ? `${h.pct_held.toFixed(2)}%` : '--'}
                        </span>
                        <span className="text-xs font-semibold text-[#f1f5f9] text-right tabular-nums">{value}</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </section>

          {/* ── Quick Links ──────────────────────────────────────────────────── */}
          <section aria-labelledby="quick-links-heading">
            <h2
              id="quick-links-heading"
              className="mb-4 text-base font-semibold text-[#f1f5f9]"
            >
              Quick Links
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">

              {/* Existing: Portfolio */}
              <QuickLinkCard
                to="/portfolio"
                icon={<BarChart2 className="h-5 w-5" aria-hidden="true" />}
                title="Portfolio"
                description="View positions &amp; performance"
              />

              {/* Existing: Watchlist */}
              <QuickLinkCard
                to="/watchlist"
                icon={<Bookmark className="h-5 w-5" aria-hidden="true" />}
                title="Watchlist"
                description="Track stocks you follow"
              />

              {/* Existing: Trading */}
              <QuickLinkCard
                to="/trading"
                icon={<TrendingUp className="h-5 w-5" aria-hidden="true" />}
                title="Trading"
                description="Place orders &amp; view history"
              />

              {/* New: Daily Market Brief */}
              <QuickLinkCard
                to="/market"
                icon={<Newspaper className="h-5 w-5" aria-hidden="true" />}
                title="Daily Market Brief"
                description="Top movers, news &amp; predictions"
                accentColor="#06b6d4"
              />

              {/* New: Penny Stocks */}
              <QuickLinkCard
                to="/penny-stocks"
                icon={<Zap className="h-5 w-5" aria-hidden="true" />}
                title="Penny Stocks"
                description="High-momentum sub-$5 stocks"
                accentColor="#f59e0b"
              />

              {/* New: News Feed */}
              <QuickLinkCard
                to="/news"
                icon={<Rss className="h-5 w-5" aria-hidden="true" />}
                title="News Feed"
                description="NLP-scored market news"
                accentColor="#10b981"
              />

              {/* New: Alerts */}
              <QuickLinkCard
                to="/alerts"
                icon={<BellRing className="h-5 w-5" aria-hidden="true" />}
                title="Alerts"
                description="Real-time market alerts"
                accentColor="#f43f5e"
              />
            </div>
          </section>

        </div>
      </main>
    </PageTransition>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────────────

interface QuickLinkCardProps {
  to: string
  icon: React.ReactNode
  title: string
  description: string
  accentColor?: string
}

function QuickLinkCard({
  to,
  icon,
  title,
  description,
  accentColor = '#6366f1',
}: QuickLinkCardProps) {
  return (
    <Link
      to={to}
      className="group flex items-center gap-4 rounded-xl border border-[#1f2d40] bg-[#111827] p-4 hover:border-[#6366f1]/40 hover:bg-[#1a2235] transition-all duration-200"
      style={{ '--accent': accentColor } as React.CSSProperties}
    >
      <div
        className="flex h-10 w-10 items-center justify-center rounded-lg transition-colors shrink-0"
        style={{
          backgroundColor: `${accentColor}26`,
          color: accentColor,
        }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-[#f1f5f9]">{title}</p>
        <p
          className="text-xs text-[#475569] mt-0.5 truncate"
          dangerouslySetInnerHTML={{ __html: description }}
        />
      </div>
      <ArrowRight className="ml-auto h-4 w-4 text-[#475569] group-hover:text-[#6366f1] transition-colors shrink-0" />
    </Link>
  )
}

/** Three "--" placeholder rows shown when the movers API is unavailable */
function MoverPlaceholderRows() {
  return (
    <>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="flex items-center justify-between rounded-lg bg-[#0a0e1a] px-3 py-2"
        >
          <span className="text-sm font-bold text-[#475569] w-14">--</span>
          <span className="text-xs text-[#475569]">--</span>
        </div>
      ))}
    </>
  )
}
