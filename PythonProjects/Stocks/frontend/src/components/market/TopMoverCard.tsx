import { GlassCard, AccordionRow } from '@/components/common'
import { cn } from '@/lib/utils'

interface TopMoverCardProps {
  ticker: string
  name: string
  price_change_pct: number
  current_price: number
  volume: number
  avg_volume: number
  has_unusual_volume: boolean
  sector: string
  /** Expanded slot rendered inside AccordionRow */
  children?: React.ReactNode
}

function formatVolume(vol: number): string {
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(1)}K`
  return String(vol)
}

export function TopMoverCard({
  ticker,
  name,
  price_change_pct,
  current_price,
  volume,
  avg_volume,
  has_unusual_volume,
  sector,
  children,
}: TopMoverCardProps) {
  const changePositive = price_change_pct >= 0
  const changeClass = changePositive ? 'text-green-400' : 'text-red-400'
  const changeSign = changePositive ? '+' : ''

  const header = (
    <div className="flex items-center gap-3 w-full">
      {/* Ticker + name */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-white text-sm">{ticker}</span>
          {has_unusual_volume && (
            <span
              role="img"
              aria-label="Unusual volume"
              className="text-base leading-none"
            >
              🔥
            </span>
          )}
        </div>
        <p className="text-xs text-slate-400 truncate">{name}</p>
      </div>

      {/* Price + change */}
      <div className="text-right flex-shrink-0">
        <p className="text-sm font-medium text-white">
          ${current_price.toFixed(2)}
        </p>
        <p className={cn('text-xs font-medium', changeClass)}>
          {changeSign}{price_change_pct.toFixed(2)}%
        </p>
      </div>

      {/* Volume + sector */}
      <div className="text-right flex-shrink-0 hidden sm:block">
        <p className="text-xs text-slate-300">{formatVolume(volume)}</p>
        <p className="text-xs text-slate-500 truncate max-w-[80px]">{sector}</p>
      </div>
    </div>
  )

  return (
    <AccordionRow header={header}>
      <GlassCard noHover className="m-2 p-3">
        {children ?? (
          <div className="flex gap-4 text-xs text-slate-400">
            <span>Vol: {formatVolume(volume)}</span>
            <span>Avg: {formatVolume(avg_volume)}</span>
            <span className="hidden sm:inline">Sector: {sector}</span>
          </div>
        )}
      </GlassCard>
    </AccordionRow>
  )
}
