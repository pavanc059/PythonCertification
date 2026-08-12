import { cn } from '@/lib/utils'

interface PaperTradingBannerProps {
  className?: string
}

export function PaperTradingBanner({ className }: PaperTradingBannerProps) {
  return (
    <div
      role="status"
      aria-label="Paper trading mode active"
      className={cn(
        'flex items-center gap-2 rounded-lg border px-4 py-2.5',
        'bg-amber-500/10 border-amber-500/30 text-amber-400',
        'text-sm font-medium',
        className
      )}
    >
      <span aria-hidden="true">📋</span>
      <span>Paper Trading Mode — No real money involved</span>
    </div>
  )
}
