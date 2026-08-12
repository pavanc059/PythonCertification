import { useQuery } from '@tanstack/react-query'
import { RefreshCw, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react'
import {
  PageTransition,
  SentimentBadge,
  ConfidenceBar,
  SkeletonPulse,
  GlassCard,
} from '@/components/common'
import { TopMoverCard } from '@/components/market/TopMoverCard'
import { StockSearchBox } from '@/components/market/StockSearchBox'
import {
  getMovers,
  getNews,
  getPredictions,
  getTickerNews,
  getPrediction,
} from '@/api/market'
import type { EnsemblePrediction, TopMover } from '@/api/market'
import { queryKeys } from '@/api/queryKeys'
import { cn } from '@/lib/utils'

// ─── Inline relative-time helper (no date-fns dependency) ───────────────────

function relativeTime(isoString: string): string {
  try {
    const diffMs = Date.now() - new Date(isoString).getTime()
    const diffSec = Math.floor(diffMs / 1000)
    if (diffSec < 60) return 'just now'
    const diffMin = Math.floor(diffSec / 60)
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHr = Math.floor(diffMin / 60)
    if (diffHr < 24) return `${diffHr}h ago`
    const diffDay = Math.floor(diffHr / 24)
    return `${diffDay}d ago`
  } catch {
    return isoString
  }
}

// ─── Signal badge colours ────────────────────────────────────────────────────

const SIGNAL_CLASSES: Record<EnsemblePrediction['category'], string> = {
  'Strong Buy':  'bg-green-500/20 text-green-300 border border-green-500/30',
  'Buy':         'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
  'Hold':        'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30',
  'Sell':        'bg-orange-500/20 text-orange-300 border border-orange-500/30',
  'Strong Sell': 'bg-red-500/20 text-red-300 border border-red-500/30',
}

const SIGNAL_COLORS: Record<EnsemblePrediction['category'], string> = {
  'Strong Buy':  '#22c55e',
  'Buy':         '#10b981',
  'Hold':        '#eab308',
  'Sell':        '#f97316',
  'Strong Sell': '#ef4444',
}

// ─── Lazy ticker detail (loaded when accordion opens) ────────────────────────

function LazyTickerDetail({ ticker }: { ticker: string }) {
  const { data: news, isLoading: newsLoading } = useQuery({
    queryKey: queryKeys.market.tickerNews(ticker),
    queryFn: () => getTickerNews(ticker, 3),
    staleTime: 60_000,
  })

  const { data: prediction, isLoading: predLoading } = useQuery({
    queryKey: queryKeys.market.prediction(ticker),
    queryFn: () => getPrediction(ticker),
    staleTime: 120_000,
  })

  const loading = newsLoading || predLoading

  if (loading) {
    return (
      <div className="space-y-2 p-1">
        <SkeletonPulse className="h-4 w-3/4" />
        <SkeletonPulse className="h-4 w-1/2" />
        <SkeletonPulse className="h-4 w-2/3" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Prediction signal */}
      {prediction && (
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs text-slate-400">Signal:</span>
          <span className={cn(
            'text-xs font-semibold',
            prediction.direction === 'up' ? 'text-green-400'
              : prediction.direction === 'down' ? 'text-red-400'
              : 'text-slate-400'
          )}>
            {prediction.direction === 'up' ? '▲ Bullish'
              : prediction.direction === 'down' ? '▼ Bearish'
              : '— Neutral'}
          </span>
          <span className="text-xs text-slate-500">
            {Math.round(prediction.confidence * 100)}% confidence
          </span>
        </div>
      )}

      {/* Ticker news */}
      {news && news.length > 0 ? (
        <div className="space-y-2">
          {news.map((article) => (
            <div key={article.id} className="flex items-start gap-2">
              <SentimentBadge score={article.sentiment_score} className="mt-0.5 flex-shrink-0" />
              <div className="min-w-0">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-slate-300 hover:text-white line-clamp-2 transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  {article.title}
                </a>
                <p className="text-xs text-slate-600 mt-0.5">{article.source}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-500">No recent news for {ticker}.</p>
      )}
    </div>
  )
}

// ─── Mover sub-list ──────────────────────────────────────────────────────────

function MoverList({ movers, label }: { movers: TopMover[]; label: string }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
        {label}
      </h3>
      <div className="space-y-1">
        {movers.slice(0, 10).map((mover) => (
          <TopMoverCard key={mover.ticker} {...mover}>
            <LazyTickerDetail ticker={mover.ticker} />
          </TopMoverCard>
        ))}
      </div>
    </div>
  )
}

// ─── Skeleton helpers ────────────────────────────────────────────────────────

function MoversSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <SkeletonPulse key={i} className="h-12 w-full" />
      ))}
    </div>
  )
}

function NewsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="space-y-1.5">
          <SkeletonPulse className="h-4 w-3/4" />
          <SkeletonPulse className="h-3 w-1/2" />
          <SkeletonPulse className="h-3 w-2/3" />
        </div>
      ))}
    </div>
  )
}

function PredictionsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="space-y-1.5">
          <SkeletonPulse className="h-4 w-1/3" />
          <SkeletonPulse className="h-2 w-full" />
        </div>
      ))}
    </div>
  )
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function DailyBriefPage() {
  // Movers query
  const {
    data: moversData,
    isLoading: moversLoading,
    isError: moversError,
    refetch: refetchMovers,
  } = useQuery({
    queryKey: queryKeys.market.movers(),
    queryFn: getMovers,
    staleTime: 300_000,
  })

  // News query (centre column)
  const {
    data: newsArticles,
    isLoading: newsLoading,
  } = useQuery({
    queryKey: queryKeys.market.news({ limit: 5 }),
    queryFn: () => getNews({ limit: 5 }),
    staleTime: 60_000,
  })

  // Predictions query (right column)
  const {
    data: predictions,
    isLoading: predictionsLoading,
  } = useQuery({
    queryKey: queryKeys.market.predictions(),
    queryFn: () => getPredictions(),
    staleTime: 120_000,
  })

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[1600px] space-y-6">

          {/* Page header */}
          <header>
            <h1 className="text-2xl font-bold text-[#f1f5f9]">Daily Market Brief</h1>
            <p className="mt-1 text-sm text-[#475569]">
              Top movers, breaking news, and AI predictions — refreshed every 5 minutes
            </p>
          </header>

          {/* Stock search */}
          <section aria-labelledby="search-heading">
            <h2 id="search-heading" className="sr-only">Stock Search</h2>
            <div className="max-w-md">
              <StockSearchBox />
            </div>
          </section>

          {/* Three-column layout */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

            {/* ── Left column: Top Movers ─────────────────────────────── */}
            <section
              aria-labelledby="movers-heading"
              className="flex flex-col"
            >
              <GlassCard noHover className="flex-1 p-4">
                <h2
                  id="movers-heading"
                  className="mb-4 text-base font-semibold text-[#f1f5f9] flex items-center gap-2"
                >
                  <TrendingUp className="h-4 w-4 text-[#6366f1]" aria-hidden="true" />
                  Top Movers
                </h2>

                {/* Loading */}
                {moversLoading && <MoversSkeleton />}

                {/* Error */}
                {moversError && !moversLoading && (
                  <div
                    className="flex flex-col items-center gap-3 py-8 text-center"
                    role="alert"
                  >
                    <AlertCircle
                      className="h-8 w-8 text-red-400"
                      aria-hidden="true"
                    />
                    <p className="text-sm text-slate-400">
                      Failed to load market movers.
                    </p>
                    <button
                      type="button"
                      onClick={() => refetchMovers()}
                      className={cn(
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium',
                        'bg-[#6366f1]/20 text-[#6366f1] border border-[#6366f1]/30',
                        'hover:bg-[#6366f1]/30 transition-colors'
                      )}
                    >
                      <RefreshCw className="h-3 w-3" aria-hidden="true" />
                      Retry
                    </button>
                  </div>
                )}

                {/* Success */}
                {!moversLoading && !moversError && moversData && (
                  <div className="space-y-5">
                    <MoverList movers={moversData.gainers} label="Gainers" />
                    <MoverList movers={moversData.losers} label="Losers" />
                  </div>
                )}
              </GlassCard>
            </section>

            {/* ── Centre column: Market News ───────────────────────────── */}
            <section
              aria-labelledby="news-heading"
              className="flex flex-col"
            >
              <GlassCard noHover className="flex-1 p-4">
                <h2
                  id="news-heading"
                  className="mb-4 text-base font-semibold text-[#f1f5f9]"
                >
                  Market News
                </h2>

                {newsLoading && <NewsSkeleton />}

                {!newsLoading && newsArticles && newsArticles.length === 0 && (
                  <p className="text-sm text-slate-500 py-8 text-center">
                    No news available.
                  </p>
                )}

                {!newsLoading && newsArticles && newsArticles.length > 0 && (
                  <div className="space-y-4">
                    {newsArticles.map((article) => {
                      const timeAgo = relativeTime(article.published_at)

                      const summary = article.summary.length > 300
                        ? article.summary.slice(0, 297) + '…'
                        : article.summary

                      return (
                        <article
                          key={article.id}
                          className="border-b border-[#1f2d40] pb-4 last:border-0 last:pb-0"
                        >
                          {/* Breaking pill + sentiment */}
                          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                            {article.is_breaking && (
                              <span
                                className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-red-600/90 text-white uppercase tracking-wide"
                                aria-label="Breaking news"
                              >
                                BREAKING
                              </span>
                            )}
                            <SentimentBadge score={article.sentiment_score} />
                          </div>

                          {/* Title */}
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block text-sm font-medium text-slate-200 hover:text-white mb-1 transition-colors leading-snug"
                          >
                            {article.title}
                          </a>

                          {/* Meta: source + time */}
                          <div className="flex items-center gap-2 mb-1.5 text-xs text-slate-500">
                            <span>{article.source}</span>
                            <span>·</span>
                            <time dateTime={article.published_at}>{timeAgo}</time>
                          </div>

                          {/* Summary (≤300 chars) */}
                          {summary && (
                            <p className="text-xs text-slate-400 leading-relaxed">
                              {summary}
                            </p>
                          )}
                        </article>
                      )
                    })}
                  </div>
                )}
              </GlassCard>
            </section>

            {/* ── Right column: Predictions ────────────────────────────── */}
            <section
              aria-labelledby="predictions-heading"
              className="flex flex-col"
            >
              <GlassCard noHover className="flex-1 p-4">
                <h2
                  id="predictions-heading"
                  className="mb-4 text-base font-semibold text-[#f1f5f9] flex items-center gap-2"
                >
                  <TrendingDown className="h-4 w-4 text-[#06b6d4]" aria-hidden="true" />
                  AI Predictions
                </h2>

                {predictionsLoading && <PredictionsSkeleton />}

                {!predictionsLoading && predictions && predictions.length === 0 && (
                  <p className="text-sm text-slate-500 py-8 text-center">
                    No predictions available.
                  </p>
                )}

                {!predictionsLoading && predictions && predictions.length > 0 && (
                  <div className="space-y-3">
                    {predictions.slice(0, 8).map((pred) => {
                      const returnSign = pred.expected_return >= 0 ? '+' : ''
                      const returnPct = (pred.expected_return * 100).toFixed(2)
                      const confidencePct = Math.round(pred.confidence * 100)
                      const barColor = SIGNAL_COLORS[pred.category]

                      return (
                        <div
                          key={pred.ticker}
                          className="rounded-lg border border-[#1f2d40] bg-[#0a0e1a]/60 p-3"
                        >
                          {/* Ticker + signal */}
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="font-bold text-[#6366f1] text-sm tracking-wide">
                              {pred.ticker}
                            </span>
                            <span className={cn(
                              'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                              SIGNAL_CLASSES[pred.category]
                            )}>
                              {pred.category}
                            </span>
                          </div>

                          {/* Confidence bar */}
                          <ConfidenceBar
                            value={confidencePct}
                            color={barColor}
                            showLabel
                            className="mb-2"
                          />

                          {/* Expected return */}
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-500">Expected return</span>
                            <span className={cn(
                              'font-semibold tabular-nums',
                              pred.expected_return >= 0 ? 'text-green-400' : 'text-red-400'
                            )}>
                              {returnSign}{returnPct}%
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </GlassCard>
            </section>

          </div>
        </div>
      </main>
    </PageTransition>
  )
}
