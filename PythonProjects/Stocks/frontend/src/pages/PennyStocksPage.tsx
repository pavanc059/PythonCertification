import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { AlertTriangle, TrendingUp, BarChart2, Zap } from 'lucide-react'
import { getPennyStocks } from '@/api/market'
import type { PennyStock } from '@/api/market'
import { queryKeys } from '@/api/queryKeys'
import { MomentumTable } from '@/components/market/MomentumTable'
import { SkeletonPulse, GlassCard } from '@/components/common'
import { PageTransition } from '@/components/common/PageTransition'
import { cn } from '@/lib/utils'
import { selectTopPennyStocks } from '@/utils/pennyStockUtils'

// ─── Types ────────────────────────────────────────────────────────────────────

type TabPeriod = '1D' | '5D' | '30D'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SECTOR_COLORS = [
  '#6366f1', '#06b6d4', '#10b981', '#f59e0b',
  '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6',
]

const RISK_CLASSES: Record<PennyStock['risk_level'], string> = {
  low:     'bg-green-500/15 text-green-400 border border-green-500/30',
  medium:  'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  high:    'bg-orange-500/15 text-orange-400 border border-orange-500/30',
  extreme: 'bg-red-500/15 text-red-400 border border-red-500/30',
}

function formatVolume(vol: number): string {
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(1)}K`
  return String(vol)
}

/**
 * Generate synthetic price-history data from a PennyStock record.
 * In production this would come from a dedicated chart endpoint.
 */
function generatePriceHistory(
  stock: PennyStock,
  period: TabPeriod
): { date: string; price: number }[] {
  const points = period === '1D' ? 24 : period === '5D' ? 30 : 60
  const seed = stock.ticker.charCodeAt(0) / 100
  const result: { date: string; price: number }[] = []
  let price = stock.price * (1 - stock.price_change_pct / 100)

  for (let i = 0; i < points; i++) {
    const noise = (Math.sin(i * seed + 1.4) * 0.015 + Math.cos(i * 0.3) * 0.01)
    price = price * (1 + noise)
    const label =
      period === '1D'
        ? `${i}h`
        : period === '5D'
        ? `D${Math.floor(i / 6) + 1}`
        : `D${i + 1}`
    result.push({ date: label, price: Math.max(0.01, +price.toFixed(3)) })
  }

  // Ensure last point matches current price
  result[result.length - 1].price = stock.price
  return result
}

function buildSectorDistribution(stocks: PennyStock[]): { name: string; value: number }[] {
  const map = new Map<string, number>()
  for (const s of stocks) {
    map.set(s.sector, (map.get(s.sector) ?? 0) + 1)
  }
  return Array.from(map.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value }))
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface StaleBannerProps {
  show: boolean
}

function StaleBanner({ show }: StaleBannerProps) {
  if (!show) return null
  return (
    <div
      role="alert"
      aria-live="polite"
      className="flex items-center gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-2.5 text-sm text-yellow-400"
    >
      <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
      Showing last-known data — live feed temporarily unavailable.
    </div>
  )
}

interface TabSelectorProps {
  active: TabPeriod
  onChange: (t: TabPeriod) => void
}

function TabSelector({ active, onChange }: TabSelectorProps) {
  const tabs: TabPeriod[] = ['1D', '5D', '30D']
  return (
    <div className="flex gap-1 rounded-lg bg-[#0a0e1a] border border-[#1f2d40] p-1 w-fit">
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={cn(
            'px-3 py-1 rounded-md text-xs font-medium transition-colors',
            active === t
              ? 'bg-[#6366f1] text-white'
              : 'text-slate-400 hover:text-slate-200'
          )}
          aria-pressed={active === t}
        >
          {t}
        </button>
      ))}
    </div>
  )
}

interface PriceChartProps {
  stock: PennyStock
  period: TabPeriod
}

function PriceChart({ stock, period }: PriceChartProps) {
  const data = useMemo(() => generatePriceHistory(stock, period), [stock, period])
  const changePositive = stock.price_change_pct >= 0
  const lineColor = changePositive ? '#10b981' : '#ef4444'

  return (
    <GlassCard noHover className="p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <span className="font-semibold text-white">{stock.ticker}</span>
          <span className="ml-2 text-sm text-slate-400">${stock.price.toFixed(2)}</span>
        </div>
        <span className={cn(
          'text-xs font-semibold',
          changePositive ? 'text-green-400' : 'text-red-400'
        )}>
          {changePositive ? '+' : ''}{stock.price_change_pct.toFixed(2)}%
        </span>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="date"
            tick={{ fill: '#475569', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#475569', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `$${v.toFixed(2)}`}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{
              background: '#111827',
              border: '1px solid #1f2d40',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            labelStyle={{ color: '#94a3b8' }}
            itemStyle={{ color: lineColor }}
            formatter={(value) => {
              const v = typeof value === 'number' ? value : Number(value ?? 0)
              return [`$${v.toFixed(3)}`, 'Price']
            }}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke={lineColor}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 4, fill: lineColor }}
          />
        </LineChart>
      </ResponsiveContainer>
    </GlassCard>
  )
}

interface SectorDonutProps {
  stocks: PennyStock[]
}

function SectorDonut({ stocks }: SectorDonutProps) {
  const data = useMemo(() => buildSectorDistribution(stocks), [stocks])
  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  if (data.length === 0) {
    return (
      <GlassCard noHover className="p-4">
        <p className="text-sm text-slate-500 text-center py-8">No sector data available.</p>
      </GlassCard>
    )
  }

  return (
    <GlassCard noHover className="p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-200">Sector Distribution</h3>
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <ResponsiveContainer width={180} height={180}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              dataKey="value"
              strokeWidth={0}
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
            >
              {data.map((_, index) => (
                <Cell
                  key={index}
                  fill={SECTOR_COLORS[index % SECTOR_COLORS.length]}
                  opacity={activeIndex === null || activeIndex === index ? 1 : 0.5}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: '#111827',
                border: '1px solid #1f2d40',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value, name) => {
                const v = typeof value === 'number' ? value : Number(value ?? 0)
                return [`${v} stock${v !== 1 ? 's' : ''}`, name]
              }}
            />
          </PieChart>
        </ResponsiveContainer>

        {/* Legend */}
        <ul className="flex flex-col gap-1.5 flex-1 min-w-0">
          {data.map((entry, index) => (
            <li key={entry.name} className="flex items-center gap-2 text-xs">
              <span
                className="h-2.5 w-2.5 rounded-full shrink-0"
                style={{ backgroundColor: SECTOR_COLORS[index % SECTOR_COLORS.length] }}
              />
              <span className="text-slate-300 truncate">{entry.name}</span>
              <span className="ml-auto text-slate-500 tabular-nums">{entry.value}</span>
            </li>
          ))}
        </ul>
      </div>
    </GlassCard>
  )
}

interface RiskCardProps {
  stock: PennyStock
  rank: number
}

function RiskCard({ stock, rank }: RiskCardProps) {
  const isPumpDump = stock.suspicion_score > 0.65

  return (
    <GlassCard noHover className="p-4">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 tabular-nums w-5">#{rank}</span>
          <span className="font-bold text-[#6366f1]">{stock.ticker}</span>
          <span className={cn(
            'rounded-full px-2 py-0.5 text-xs font-medium capitalize',
            RISK_CLASSES[stock.risk_level]
          )}>
            {stock.risk_level}
          </span>
        </div>

        {isPumpDump && (
          <span className="flex items-center gap-1 rounded-full bg-red-500/20 border border-red-500/40 px-2 py-0.5 text-xs font-semibold text-red-400 shrink-0">
            <AlertTriangle className="h-3 w-3" aria-hidden="true" />
            Pump &amp; Dump Risk
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <p className="text-slate-500">Price</p>
          <p className="font-medium text-slate-200">${stock.price.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-slate-500">Momentum</p>
          <p className={cn(
            'font-semibold tabular-nums',
            stock.momentum_score >= 80 ? 'text-green-400'
              : stock.momentum_score >= 50 ? 'text-yellow-400'
              : 'text-slate-400'
          )}>
            {stock.momentum_score.toFixed(1)}
          </p>
        </div>
        <div>
          <p className="text-slate-500">Volume</p>
          <p className="font-medium text-slate-200">{formatVolume(stock.volume)}</p>
        </div>
        <div>
          <p className="text-slate-500">Suspicion</p>
          <p className={cn(
            'font-semibold tabular-nums',
            stock.suspicion_score > 0.65 ? 'text-red-400'
              : stock.suspicion_score > 0.35 ? 'text-yellow-400'
              : 'text-green-400'
          )}>
            {(stock.suspicion_score * 100).toFixed(0)}%
          </p>
        </div>
        <div className="col-span-2">
          <p className="text-slate-500">Catalyst</p>
          <p className="text-slate-300 truncate">{stock.catalyst || '—'}</p>
        </div>
        {(stock.insider_buys > 0 || stock.insider_sells > 0) && (
          <div className="col-span-2">
            <p className="text-slate-500">Insider Activity</p>
            <p className="text-slate-300">
              <span className="text-green-400">{stock.insider_buys}B</span>
              {' / '}
              <span className="text-red-400">{stock.insider_sells}S</span>
            </p>
          </div>
        )}
      </div>
    </GlassCard>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PennyStocksPage() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [period, setPeriod] = useState<TabPeriod>('1D')

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isRefetchError,
    dataUpdatedAt,
  } = useQuery({
    queryKey: queryKeys.market.pennyStocks(),
    queryFn: getPennyStocks,
    staleTime: 60_000,
    refetchInterval: 120_000,
    // Keep previous data on refetch failure so we can show stale banner
    placeholderData: (prev) => prev,
  })

  // Show stale banner only when a background refetch has failed (we have old data)
  const isShowingStaleData = isRefetchError && !!data

  // The displayed stocks list capped at 20
  const stocks = useMemo(
    () => selectTopPennyStocks(data ?? [], 20),
    [data]
  )

  // Default selected ticker: highest-ranked (first after sorting by momentum_score desc)
  const defaultTicker = stocks[0]?.ticker ?? null
  const activeTicker = selectedTicker ?? defaultTicker
  const activeStock = stocks.find((s) => s.ticker === activeTicker) ?? stocks[0]

  // Top 5 for risk cards
  const top5 = useMemo(() => stocks.slice(0, 5), [stocks])

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl space-y-6">

          {/* Page header */}
          <header className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-[#6366f1]" aria-hidden="true" />
              <h1 className="text-2xl font-bold text-[#f1f5f9]">Low-Price Stocks</h1>
              <span className="text-xs text-[#475569] mt-0.5">Under $15</span>
            </div>
            {dataUpdatedAt > 0 && (
              <span className="text-xs text-slate-500">
                Updated {new Date(dataUpdatedAt).toLocaleTimeString()}
              </span>
            )}
          </header>

          {/* Stale data banner */}
          <StaleBanner show={isShowingStaleData} />

          {/* Hard error — no cached data available */}
          {isError && !data && (
            <GlassCard noHover className="p-6 text-center">
              <BarChart2 className="mx-auto mb-3 h-10 w-10 text-slate-600" aria-hidden="true" />
              <p className="mb-1 font-semibold text-slate-300">Failed to load penny stocks</p>
              <p className="mb-4 text-sm text-slate-500">
                {(error as Error)?.message ?? 'An unexpected error occurred.'}
              </p>
              <button
                onClick={() => refetch()}
                className="rounded-lg bg-[#6366f1] px-4 py-2 text-sm font-medium text-white hover:bg-[#818cf8] transition-colors"
              >
                Retry
              </button>
            </GlassCard>
          )}

          {/* Main content */}
          {(isLoading || !!data) && (
            <>
              {/* ── Momentum Table ───────────────────────────────────────── */}
              <section aria-labelledby="momentum-table-heading">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h2
                    id="momentum-table-heading"
                    className="text-base font-semibold text-slate-200"
                  >
                    Momentum Rankings
                    {!isLoading && stocks.length > 0 && (
                      <span className="ml-2 text-xs font-normal text-slate-500">
                        ({stocks.length} stocks)
                      </span>
                    )}
                  </h2>
                </div>

                {isLoading ? (
                  <div className="rounded-xl border border-[#1f2d40] overflow-hidden">
                    <div className="bg-[#0a0e1a] px-3 py-2.5 border-b border-[#1f2d40]">
                      <SkeletonPulse className="h-4 w-48" />
                    </div>
                    {Array.from({ length: 8 }).map((_, i) => (
                      <div key={i} className="flex gap-3 px-3 py-2.5 border-b border-[#1f2d40] bg-[#111827]">
                        <SkeletonPulse className="h-4 flex-1" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <MomentumTable
                    rows={stocks}
                    isLoading={false}
                  />
                )}
              </section>

              {/* ── Price Chart + Sector Donut ────────────────────────────── */}
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

                {/* Price history chart */}
                <section aria-labelledby="price-chart-heading">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <h2
                      id="price-chart-heading"
                      className="text-base font-semibold text-slate-200"
                    >
                      Price History
                    </h2>
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Ticker selector */}
                      {stocks.length > 1 && (
                        <div className="flex gap-1 flex-wrap">
                          {stocks.slice(0, 6).map((s) => (
                            <button
                              key={s.ticker}
                              onClick={() => setSelectedTicker(s.ticker)}
                              className={cn(
                                'px-2.5 py-1 rounded-md text-xs font-medium transition-colors border',
                                activeTicker === s.ticker
                                  ? 'bg-[#6366f1] border-[#6366f1] text-white'
                                  : 'border-[#1f2d40] text-slate-400 hover:text-slate-200 hover:border-[#2d3f58]'
                              )}
                              aria-pressed={activeTicker === s.ticker}
                            >
                              {s.ticker}
                            </button>
                          ))}
                        </div>
                      )}
                      <TabSelector active={period} onChange={setPeriod} />
                    </div>
                  </div>

                  {isLoading ? (
                    <GlassCard noHover className="p-4">
                      <SkeletonPulse className="h-[200px] w-full" />
                    </GlassCard>
                  ) : activeStock ? (
                    <PriceChart stock={activeStock} period={period} />
                  ) : (
                    <GlassCard noHover className="p-6 text-center">
                      <TrendingUp className="mx-auto mb-2 h-8 w-8 text-slate-600" aria-hidden="true" />
                      <p className="text-sm text-slate-500">No stock selected.</p>
                    </GlassCard>
                  )}
                </section>

                {/* Sector distribution donut */}
                <section aria-labelledby="sector-donut-heading">
                  <h2
                    id="sector-donut-heading"
                    className="mb-3 text-base font-semibold text-slate-200"
                  >
                    Sector Distribution
                  </h2>
                  {isLoading ? (
                    <GlassCard noHover className="p-4">
                      <SkeletonPulse className="h-[220px] w-full" />
                    </GlassCard>
                  ) : (
                    <SectorDonut stocks={stocks} />
                  )}
                </section>
              </div>

              {/* ── Risk Metric Cards ─────────────────────────────────────── */}
              <section aria-labelledby="risk-cards-heading">
                <h2
                  id="risk-cards-heading"
                  className="mb-3 text-base font-semibold text-slate-200"
                >
                  Top 5 Risk Metrics
                </h2>

                {isLoading ? (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <GlassCard key={i} noHover className="p-4">
                        <SkeletonPulse className="h-32 w-full" />
                      </GlassCard>
                    ))}
                  </div>
                ) : top5.length === 0 ? (
                  <GlassCard noHover className="p-6 text-center">
                    <p className="text-sm text-slate-500">No risk data available.</p>
                  </GlassCard>
                ) : (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
                    {top5.map((stock, i) => (
                      <RiskCard key={stock.ticker} stock={stock} rank={i + 1} />
                    ))}
                  </div>
                )}
              </section>
            </>
          )}

        </div>
      </main>
    </PageTransition>
  )
}
