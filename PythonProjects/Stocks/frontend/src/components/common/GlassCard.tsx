import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface GlassCardProps {
  children: React.ReactNode
  className?: string
  /** Disable hover-scale animation. Default: false */
  noHover?: boolean
  onClick?: () => void
}

export function GlassCard({ children, className, noHover = false, onClick }: GlassCardProps) {
  return (
    <motion.div
      whileHover={noHover ? undefined : { scale: 1.02 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
      onClick={onClick}
      className={cn(
        'relative bg-[#111827]/80 backdrop-blur-md border border-[#1f2d40] rounded-xl overflow-hidden',
        'before:absolute before:inset-0 before:rounded-xl before:pointer-events-none',
        'before:bg-gradient-to-br before:from-[#6366f1]/20 before:via-transparent before:to-[#06b6d4]/20',
        onClick && 'cursor-pointer',
        className
      )}
    >
      {children}
    </motion.div>
  )
}
