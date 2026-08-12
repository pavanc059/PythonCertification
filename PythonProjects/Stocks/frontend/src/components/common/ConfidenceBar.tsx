import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface ConfidenceBarProps {
  /** Integer 0–100 */
  value: number
  /** Valid CSS color string, e.g. '#6366f1' */
  color: string
  className?: string
  showLabel?: boolean
}

export function ConfidenceBar({ value, color, className, showLabel = false }: ConfidenceBarProps) {
  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-slate-400">Confidence</span>
          <span className="text-xs font-medium text-slate-300">{value}%</span>
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 w-full rounded-full bg-[#1a2235] overflow-hidden"
      >
        <motion.div
          data-testid="confidence-fill"
          initial={{ width: '0%' }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.45, ease: 'easeOut', delay: 0.1 }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
    </div>
  )
}
