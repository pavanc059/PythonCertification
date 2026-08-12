import { cn } from '@/lib/utils'

interface SentimentBadgeProps {
  score: number // SentimentScore in [-1, 1]
  className?: string
}

type SentimentLevel = 'positive' | 'neutral' | 'negative'

function getSentimentLevel(score: number): SentimentLevel {
  if (score > 0.15) return 'positive'
  if (score < -0.15) return 'negative'
  return 'neutral'
}

const sentimentClasses: Record<SentimentLevel, string> = {
  positive: 'bg-green-500/15 text-green-400 border border-green-500/30',
  neutral: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  negative: 'bg-red-500/15 text-red-400 border border-red-500/30',
}

const sentimentLabels: Record<SentimentLevel, string> = {
  positive: 'Positive',
  neutral: 'Neutral',
  negative: 'Negative',
}

export function SentimentBadge({ score, className }: SentimentBadgeProps) {
  const level = getSentimentLevel(score)

  return (
    <span
      data-testid="sentiment-badge"
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
        sentimentClasses[level],
        className
      )}
    >
      {sentimentLabels[level]}
    </span>
  )
}
