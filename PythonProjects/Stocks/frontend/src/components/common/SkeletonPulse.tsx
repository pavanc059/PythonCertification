import { cn } from '@/lib/utils'

interface SkeletonPulseProps {
  className?: string
}

export function SkeletonPulse({ className }: SkeletonPulseProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn('animate-pulse bg-[#1a2235] rounded', className)}
    />
  )
}
