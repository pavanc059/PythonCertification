import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Brain, AlertTriangle, RefreshCw, Loader2, TrendingUp } from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import { GlassCard, ConfidenceBar, SkeletonPulse } from '@/components/common'
import { getPredictions } from '@/api/market'
import type { EnsemblePrediction } from '@/api/market'
import { getWatchlist } from '@/api/watchlist'
import { queryKeys } from '@/api/queryKeys'
import { useAuthStore } from '@/store/authStore'
import apiClient from '@/api/client'
import { cn } from '@/lib/utils'

// ── Category filter types ──────────────────────────────────────────────────

type CategoryFilter = 'all' | 'bullish' | 'bearish' | 'neutral'

const FILTER_LABELS: Record<CategoryFilter, string> = {
  all: 'All',
  bullish: 'Bullish',
  bearish: 'Bearish',
  neutral: 'Neutral',
}

const BULLISH_CATEGORIES = new Set(['Strong Buy', 'Buy'])
const BEARISH_CATEGORIES = new Set(['Sell', 'Strong Sell'])
const NEUTRAL_CATEGORIES = new Set(['Hold'])

function matchesFilter(prediction: EnsemblePrediction, filter: CategoryFilter): boolean {
  if (filter === 'all') return true
  if (filter === 'bullish') return BULLISH_CATEGORIES.has(prediction.category)
  if (filter === 'bearish') return BEARISH_CATEGORIES.has(prediction.category)
  if (filter === 'neutral') return NEUTRAL_CATEGORIES.has(prediction.category)
  return true
}

// ── Signal category badge colour mapping ──────────────────────────────────

function getSignalClasses(category: EnsemblePrediction['category']): string {
  switch (category) {
    case 'Strong Buy':
      return 'bg-green-500/15 text-green-400 border border-green-500/30'
    case 'Buy':
      return 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
    case 'Hold':
      return 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30'
    case 'Sell':
      return 'bg-orange-500/15 text-orange-400 border border-orange-500/30'
    case 'Strong Sell':
      return 'bg-red-500/15 text-red-400 border border-red-500/30'
    default:
      return 'bg-slate-500/15 text-slate-400 border border-slate-500/30'
  }
}

function getConfidenceBarColor(category: EnsemblePrediction['category']): string {
  switch (category) {
    case 'Strong Buy':
    case 'Buy':
      return '#22c55e'
    case 'Sell':
    case 'Strong Sell':
      return '#ef4444'
    default:
      return '#eab308'
  }
}

// ── Skeleton cards ─────────────────────────────────────────────────────────

function PredictionSkeleton() {
  return (
    <div className="rounded-xl border border-[#1f2d40] bg-[#111827]/80 p-5 space-y-3">
      <div className="flex items-center justify-between">
        <SkeletonPulse className="h-6 w-16 rounded-md" />
        <SkeletonPulse className="h-5 w-20 rounded-full" />
      </div>
      <SkeletonPulse className="h-2 w-full rounded-full" />
      <div className="flex justify-between">
        <SkeletonPulse className="h-4 w-24 rounded" />
        <SkeletonPulse className="h-4 w-28 rounded" />
      </div>
    </div>
  )
}

// ── Prediction card ────────────────────────────────────────────────────────

interface PredictionCardProps {
  prediction: EnsemblePrediction
}

function PredictionCard({ prediction }: PredictionCardProps) {
  const confidencePct = Math.round(prediction.confidence * 100)
  const expectedReturnPct = (prediction.expected_return * 100).toFixed(2)
  const lowerBoundPct = (prediction.lower_bound * 100).toFixed(2)
  const upperBoundPct = (prediction.upper_bound * 100).toFixed(2)
  const isPositiveReturn = prediction.expected_return >= 0

  // Freshness label from computed_at timestamp
  const freshness = prediction.computed_at
    ? (() => {
        const diffMin = Math.round((Date.now() - new Date(prediction.computed_at).getTime()) / 60000)
        if (diffMin < 2) return 'just now'
        if (diffMin < 60) return `${diffMin}m ago`
        const diffH = Math.floor(diffMin / 60)
        if (diffH < 24) return `${diffH}h ago`
        return `${Math.floor(diffH / 24)}d ago`
      })()
    : null

  // SMA cross label
  const smaCross = prediction.sma_cross
  const smaLabel = smaCross === 'golden_cross' ? '↑ Golden X' : smaCross === 'death_cross' ? '↓ Death X' : null

  return (
    <GlassCard noHover className="relative p-5 space-y-4">
      {/* Low confidence chip */}
      {prediction.is_low_confidence && (
        <div className="absolute top-3 right-3 flex items-center gap-1 rounded-full bg-yellow-500/15 border border-yellow-500/30 px-2.5 py-1 text-xs font-medium text-yellow-400">
          <AlertTriangle className="h-3 w-3" aria-hidden="true" />
          Low Confidence
        </div>
      )}

      {/* Header: ticker + signal badge */}
      <div className="flex items-start gap-3 pr-24">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-[#6366f1]/15 border border-[#6366f1]/30 px-2.5 py-1 text-sm font-bold text-[#6366f1] tracking-wide">
            {prediction.ticker}
          </span>
          <span className={cn('rounded-full px-2.5 py-1 text-xs font-semibold', getSignalClasses(prediction.category))}>
            {prediction.category}
          </span>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs text-[#475569]">Model Confidence</span>
          <span className="text-xs font-semibold text-[#94a3b8]">{confidencePct}%</span>
        </div>
        <ConfidenceBar
          value={confidencePct}
          color={getConfidenceBarColor(prediction.category)}
        />
      </div>

      {/* Expected return + range */}
      <div className="grid grid-cols-2 gap-3 pt-1">
        <div>
          <p className="text-xs text-[#475569] mb-0.5">Expected Return</p>
          <p className={cn(
            'text-sm font-bold',
            isPositiveReturn ? 'text-green-400' : 'text-red-400'
          )}>
            {isPositiveReturn ? '+' : ''}{expectedReturnPct}%
          </p>
        </div>
        <div>
          <p className="text-xs text-[#475569] mb-0.5">Predicted Range</p>
          <p className="text-sm font-medium text-[#94a3b8]">
            {parseFloat(lowerBoundPct) >= 0 ? '+' : ''}{lowerBoundPct}% →{' '}
            {parseFloat(upperBoundPct) >= 0 ? '+' : ''}{upperBoundPct}%
          </p>
        </div>
      </div>

      {/* Technical indicators mini-row */}
      {(prediction.rsi_14 != null || smaLabel || prediction.momentum_30d != null) && (
        <div className="flex items-center gap-2 flex-wrap pt-0.5">
          {prediction.rsi_14 != null && (
            <span className={cn(
              'text-[10px] px-1.5 py-0.5 rounded font-mono',
              prediction.rsi_14 > 60 ? 'bg-green-500/10 text-green-400' :
              prediction.rsi_14 < 40 ? 'bg-red-500/10 text-red-400' :
              'bg-[#1f2d40] text-[#94a3b8]'
            )}>
              RSI {prediction.rsi_14.toFixed(0)}
            </span>
          )}
          {smaLabel && (
            <span className={cn(
              'text-[10px] px-1.5 py-0.5 rounded font-medium',
              smaCross === 'golden_cross' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
            )}>
              {smaLabel}
            </span>
          )}
          {prediction.momentum_30d != null && (
            <span className={cn(
              'text-[10px] px-1.5 py-0.5 rounded font-mono',
              prediction.momentum_30d > 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
            )}>
              {prediction.momentum_30d > 0 ? '+' : ''}{prediction.momentum_30d.toFixed(1)}% 30d
            </span>
          )}
        </div>
      )}

      {/* AI reasoning — shown when LLM produced a reason */}
      {prediction.reason && (
        <p className="text-[11px] text-[#94a3b8] leading-relaxed border-t border-[#1f2d40] pt-2.5 line-clamp-2" title={prediction.reason}>
          {prediction.reason}
        </p>
      )}

      {/* Freshness timestamp */}
      {freshness && (
        <p className="text-[10px] text-[#475569] text-right -mt-1">
          Updated {freshness}
        </p>
      )}
    </GlassCard>
  )
}

// ── Main page component ────────────────────────────────────────────────────

export default function PredictionsPage() {
  const user = useAuthStore((s) => s.user)
  // Check for admin role — may be present as an extended field on the user object
  const isAdmin = !!(user && (user as unknown as { role?: string }).role === 'admin')

  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all')
  const [retrainStatus, setRetrainStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [retrainError, setRetrainError] = useState<string | null>(null)

  // ── Fetch watchlist to get tickers ─────────────────────────────────────

  const {
    data: watchlistItems = [],
    isLoading: watchlistLoading,
  } = useQuery({
    queryKey: queryKeys.watchlist.items(),
    queryFn: getWatchlist,
    staleTime: 60_000,
  })

  const watchlistTickers = watchlistItems.map((item) => item.ticker)

  // ── Fetch predictions for watchlist tickers ────────────────────────────

  const {
    data: predictions = [],
    isLoading: predictionsLoading,
    isError: predictionsError,
    error: predictionsErrorObj,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: queryKeys.market.predictions(watchlistTickers),
    queryFn: () => getPredictions(watchlistTickers),
    enabled: !watchlistLoading && watchlistTickers.length > 0,
    staleTime: 120_000,
  })

  const isLoading = watchlistLoading || (predictionsLoading && watchlistTickers.length > 0)

  // ── Apply category filter ──────────────────────────────────────────────

  const filteredPredictions = predictions.filter((p) => matchesFilter(p, categoryFilter))

  // ── Retrain model handler ──────────────────────────────────────────────

  const handleRetrain = async () => {
    setRetrainStatus('loading')
    setRetrainError(null)
    try {
      await apiClient.post('/market/predictions/train')
      setRetrainStatus('success')
    } catch {
      setRetrainStatus('error')
      setRetrainError('Failed to start model retraining. Please try again.')
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl space-y-6">

          {/* Page header */}
          <header className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#6366f1]/15">
                <Brain className="h-5 w-5 text-[#6366f1]" aria-hidden="true" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-[#f1f5f9]">AI Predictions</h1>
                <p className="text-sm text-[#475569]">
                  Ensemble model forecasts for your watchlist
                </p>
              </div>
            </div>

            {/* Admin retrain button */}
            {isAdmin && (
              <button
                type="button"
                onClick={() => void handleRetrain()}
                disabled={retrainStatus === 'loading'}
                aria-busy={retrainStatus === 'loading'}
                className={cn(
                  'flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all',
                  'bg-[#6366f1] text-white hover:bg-[#4f52d9] disabled:opacity-60 disabled:cursor-not-allowed'
                )}
              >
                {retrainStatus === 'loading' ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Retraining…
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" aria-hidden="true" />
                    Retrain Model
                  </>
                )}
              </button>
            )}
          </header>

          {/* Retrain feedback */}
          {retrainStatus === 'success' && (
            <div
              role="status"
              className="rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm text-green-400"
            >
              Model retraining started successfully. New predictions will be available shortly.
            </div>
          )}
          {retrainStatus === 'error' && retrainError && (
            <div
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400"
            >
              {retrainError}
            </div>
          )}

          {/* Live data note */}
          {!isLoading && predictions.length > 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-[#1f2d40] bg-[#111827]/60 px-4 py-2 text-xs text-[#475569]">
              <Brain className="h-3.5 w-3.5 shrink-0 text-[#6366f1]" />
              Predictions powered by RSI · MACD · SMA cross · 30-day momentum
              {predictions[0]?.computed_at && ` · refreshed daily at 7 AM ET`}
            </div>
          )}

          {/* Empty state: no watchlist items */}
          {!watchlistLoading && watchlistTickers.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-xl border border-[#1f2d40] bg-[#111827] px-8 py-16 text-center">
              <TrendingUp className="mb-4 h-16 w-16 text-[#475569]" aria-hidden="true" />
              <h2 className="text-base font-semibold text-[#94a3b8]">
                No predictions available
              </h2>
              <p className="mt-2 text-sm text-[#475569]">
                Add stocks to your watchlist to see predictions.
              </p>
            </div>
          )}

          {/* Error state */}
          {predictionsError && watchlistTickers.length > 0 && (
            <div
              role="alert"
              className="flex flex-col items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-8 py-10 text-center"
            >
              <p className="text-sm font-medium text-red-400">
                {(predictionsErrorObj as Error)?.message ?? 'Failed to load predictions.'}
              </p>
              <button
                type="button"
                onClick={() => void refetch()}
                disabled={isFetching}
                className="flex items-center gap-2 rounded-lg bg-red-500/20 px-4 py-2 text-sm font-semibold text-red-400 hover:bg-red-500/30 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} aria-hidden="true" />
                Retry
              </button>
            </div>
          )}

          {/* Content area — only show when watchlist is non-empty */}
          {watchlistTickers.length > 0 && !predictionsError && (
            <>
              {/* Category filter toolbar */}
              {!isLoading && predictions.length > 0 && (
                <nav aria-label="Prediction category filter" className="flex items-center gap-2 flex-wrap">
                  {(Object.keys(FILTER_LABELS) as CategoryFilter[]).map((filter) => (
                    <button
                      key={filter}
                      type="button"
                      onClick={() => setCategoryFilter(filter)}
                      aria-pressed={categoryFilter === filter}
                      className={cn(
                        'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                        categoryFilter === filter
                          ? 'bg-[#6366f1] text-white'
                          : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#1a2235]'
                      )}
                    >
                      {FILTER_LABELS[filter]}
                      {filter !== 'all' && (
                        <span className="ml-1.5 rounded-full bg-white/10 px-1.5 py-0.5 text-xs">
                          {predictions.filter((p) => matchesFilter(p, filter)).length}
                        </span>
                      )}
                    </button>
                  ))}
                </nav>
              )}

              {/* Loading skeleton */}
              {isLoading && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <PredictionSkeleton key={i} />
                  ))}
                </div>
              )}

              {/* Empty filter state */}
              {!isLoading && filteredPredictions.length === 0 && predictions.length > 0 && (
                <div className="flex flex-col items-center justify-center rounded-xl border border-[#1f2d40] bg-[#111827] px-8 py-12 text-center">
                  <Brain className="mb-3 h-12 w-12 text-[#475569]" aria-hidden="true" />
                  <p className="text-sm text-[#94a3b8]">
                    No {FILTER_LABELS[categoryFilter].toLowerCase()} signals in your watchlist.
                  </p>
                </div>
              )}

              {/* Prediction cards grid */}
              {!isLoading && filteredPredictions.length > 0 && (
                <section aria-label="Prediction cards">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                    {filteredPredictions.map((prediction) => (
                      <PredictionCard key={prediction.ticker} prediction={prediction} />
                    ))}
                  </div>
                  <p className="mt-3 text-xs text-[#475569]">
                    Showing {filteredPredictions.length} of {predictions.length} prediction{predictions.length !== 1 ? 's' : ''}
                  </p>
                </section>
              )}
            </>
          )}

        </div>
      </main>
    </PageTransition>
  )
}
