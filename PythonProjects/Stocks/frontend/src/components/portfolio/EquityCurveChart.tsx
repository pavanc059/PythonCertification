import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { SkeletonCard } from '@/components/common/SkeletonCard'
import { getPortfolioHistory } from '@/api/portfolio'
import { formatCurrency, formatCompact } from '@/lib/formatters'
import { cn } from '@/lib/utils'

// Period options for slicing the equity curve
type Period = '7D' | '30D' | '90D' | 'All'

const PERIOD_DAYS: Record<Period, number | null> = {
  '7D': 7,
  '30D': 30,
  '90D': 90,
  All: null,
}

const PERIODS: Period[] = ['7D', '30D', '90D', 'All']

// Normalise the raw snapshot to { date: string, value: number }
// Backend sends { date, total_value }; frontend type has { timestamp, equity }
interface NormalisedSnapshot {
  date: string
  value: number
}

function normaliseSnapshot(raw: Record<string, unknown>): NormalisedSnapshot {
  // Backend shape: { date: string, total_value: number }
  if (typeof raw.date === 'string' && typeof raw.total_value === 'number') {
    return { date: raw.date, value: raw.total_value }
  }
  // Frontend type shape: { timestamp: string, equity: number }
  if (typeof raw.timestamp === 'string' && typeof raw.equity === 'number') {
    return { date: raw.timestamp.slice(0, 10), value: raw.equity }
  }
  // Fallback — shouldn't happen
  return { date: String(raw.date ?? raw.timestamp ?? ''), value: Number(raw.total_value ?? raw.equity ?? 0) }
}

// Abbreviate a date string (YYYY-MM-DD or ISO) to "Jan 15" format
function abbreviateDate(dateStr: string): string {
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// Custom tooltip shown when hovering the chart
interface TooltipPayload {
  value: number
  payload: { date: string; value: number }
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: TooltipPayload[]
}) {
  if (!active || !payload?.length) return null
  const { date, value } = payload[0].payload
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="text-muted-foreground mb-0.5">{abbreviateDate(date)}</p>
      <p className="text-foreground font-semibold">{formatCurrency(value)}</p>
    </div>
  )
}

export function EquityCurveChart() {
  const [activePeriod, setActivePeriod] = useState<Period>('30D')

  const { data: history, isLoading } = useQuery({
    queryKey: ['portfolio-history'],
    queryFn: getPortfolioHistory,
  })

  if (isLoading) {
    return <SkeletonCard lines={5} className="h-64" />
  }

  // Normalise snapshots (handle both backend and frontend field names)
  const rawSnapshots = (history?.equity_snapshots ?? []) as unknown as Record<string, unknown>[]
  const allData: NormalisedSnapshot[] = rawSnapshots.map(normaliseSnapshot)

  // Slice data by selected period
  const days = PERIOD_DAYS[activePeriod]
  const slicedData =
    days === null
      ? allData
      : allData.slice(-days)

  const isEmpty = slicedData.length === 0

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      {/* Card header: title + period selector */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-muted-foreground font-medium">Equity Curve</span>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setActivePeriod(p)}
              className={cn(
                'px-2 py-0.5 text-xs rounded font-medium transition-colors',
                activePeriod === p
                  ? 'bg-brand/20 text-brand'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Empty state */}
      {isEmpty ? (
        <div className="h-[300px] flex items-center justify-center">
          <p className="text-sm text-muted-foreground">No history yet</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={slicedData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tickFormatter={abbreviateDate}
              tick={{ fontSize: 10, fill: '#475569' }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={formatCompact}
              tick={{ fontSize: 10, fill: '#475569' }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#6366f1"
              strokeWidth={2}
              fill="url(#equityGradient)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
