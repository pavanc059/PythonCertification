import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatPercent } from '@/lib/formatters'
import { SkeletonCard } from './SkeletonCard'

interface MetricCardProps {
  title: string
  value: string | number
  /** Raw decimal change, e.g. 0.035 = +3.5% */
  change?: number
  changeLabel?: string
  icon?: React.ReactNode
  isLoading?: boolean
  className?: string
}

export function MetricCard({
  title,
  value,
  change,
  changeLabel,
  icon,
  isLoading = false,
  className,
}: MetricCardProps) {
  if (isLoading) {
    return <SkeletonCard className={className} lines={3} />
  }

  const changeColorClass =
    change === undefined
      ? ''
      : change > 0
        ? 'text-gain'
        : change < 0
          ? 'text-loss'
          : 'text-muted-foreground'

  const ChangeIcon =
    change !== undefined && change > 0
      ? TrendingUp
      : change !== undefined && change < 0
        ? TrendingDown
        : null

  return (
    <div
      className={cn(
        'bg-card border border-border rounded-lg p-4 flex flex-col gap-2',
        className
      )}
    >
      {/* Header row: title + optional icon */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground font-medium">{title}</span>
        {icon && <span className="text-muted-foreground">{icon}</span>}
      </div>

      {/* Value */}
      <span className="text-2xl font-semibold text-foreground">{value}</span>

      {/* Change row */}
      {change !== undefined && (
        <div className={cn('flex items-center gap-1 text-sm font-medium', changeColorClass)}>
          {ChangeIcon && <ChangeIcon className="h-4 w-4" />}
          <span>{formatPercent(change)}</span>
          {changeLabel && (
            <span className="text-muted-foreground font-normal ml-1">{changeLabel}</span>
          )}
        </div>
      )}
    </div>
  )
}
