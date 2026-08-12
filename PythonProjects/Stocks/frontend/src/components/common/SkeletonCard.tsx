import { cn } from '@/lib/utils'

interface SkeletonCardProps {
  className?: string
  lines?: number
}

export function SkeletonCard({ className, lines = 3 }: SkeletonCardProps) {
  // Width pattern: title is widest, subsequent lines shrink progressively
  const lineWidths = ['w-2/3', 'w-1/2', 'w-1/3', 'w-1/4', 'w-1/5']

  return (
    <div
      className={cn(
        'bg-card border border-border rounded-lg p-4 animate-pulse',
        className
      )}
    >
      {/* Title skeleton — wider */}
      <div className="h-3 bg-muted rounded w-1/2 mb-3" />

      {/* Value skeleton — tall, prominent */}
      <div className="h-7 bg-muted rounded w-2/3 mb-3" />

      {/* Additional lines — progressively narrower */}
      {lines > 1 &&
        Array.from({ length: lines - 1 }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'h-3 bg-muted rounded mt-2',
              lineWidths[Math.min(i + 1, lineWidths.length - 1)]
            )}
          />
        ))}
    </div>
  )
}
