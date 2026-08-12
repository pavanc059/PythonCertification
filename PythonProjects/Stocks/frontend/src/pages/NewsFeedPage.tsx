import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, Newspaper, Zap } from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import {
  GlassCard,
  SentimentBadge,
  SkeletonPulse,
  AccordionRow,
} from '@/components/common'
import { getNews } from '@/api/market'
import type { NewsArticle } from '@/api/market'
import { queryKeys } from '@/api/queryKeys'
import { cn } from '@/lib/utils'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 20
const SCROLL_THRESHOLD_PX = 200
const BREAKING_MAX = 5

type SentimentFilter = 'all' | 'positive' | 'neutral' | 'negative'
type CategoryFilter = 'all' | 'Earnings' | 'Economic' | 'M&A' | 'Regulatory'

const SENTIMENT_OPTIONS: { label: string; value: SentimentFilter }[] = [
  { label: 'All', value: 'all' },
  { label: 'Positive', value: 'positive' },
  { label: 'Neutral', value: 'neutral' },
  { label: 'Negative', value: 'negative' },
]

const CATEGORY_OPTIONS: { label: string; value: CategoryFilter }[] = [
  { label: 'All', value: 'all' },
  { label: 'Earnings', value: 'Earnings' },
  { label: 'Economic', value: 'Economic' },
  { label: 'M&A', value: 'M&A' },
  { label: 'Regulatory', value: 'Regulatory' },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Format an ISO 8601 timestamp as a relative time string */
function formatRelativeTime(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then

  if (isNaN(then)) return isoString

  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 60) return `${diffSec}s ago`

  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`

  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`

  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 30) return `${diffDay}d ago`

  return new Date(isoString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/** Validate a ticker: 1–5 uppercase alpha characters */
function isValidTicker(value: string): boolean {
  return /^[A-Z]{1,5}$/.test(value)
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface TickerChipProps {
  ticker: string
  onClick: (ticker: string) => void
}

function TickerChip({ ticker, onClick }: TickerChipProps) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        onClick(ticker)
      }}
      className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-bold text-[#6366f1] bg-[#6366f1]/10 border border-[#6366f1]/20 hover:bg-[#6366f1]/25 transition-colors"
    >
      {ticker}
    </button>
  )
}

interface NewsCardProps {
  article: NewsArticle
  onTickerClick: (ticker: string) => void
  /** When true, shows a red "BREAKING" badge in the header */
  isBreaking?: boolean
}

function NewsCard({ article, onTickerClick, isBreaking }: NewsCardProps) {
  const accordionHeader = (
    <div className="flex flex-col gap-1 w-full pr-2">
      {/* Title row */}
      <div className="flex items-start gap-2">
        {isBreaking && (
          <span className="mt-0.5 flex-shrink-0 inline-flex items-center rounded-full bg-red-500/20 border border-red-500/40 px-2 py-0.5 text-xs font-bold text-red-400 uppercase tracking-wide">
            Breaking
          </span>
        )}
        <span className="text-sm font-semibold text-[#f1f5f9] leading-snug line-clamp-2">
          {article.title}
        </span>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <SentimentBadge score={article.sentiment_score} />

        <span className="text-xs text-[#475569]">{article.source}</span>

        <span className="text-xs text-[#475569]">
          {formatRelativeTime(article.published_at)}
        </span>

        {article.category && (
          <span className="inline-flex items-center rounded-full bg-[#1a2235] border border-[#1f2d40] px-2 py-0.5 text-xs text-[#94a3b8]">
            {article.category}
          </span>
        )}
      </div>

      {/* Ticker chips */}
      {article.tickers.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {article.tickers.map((ticker) => (
            <TickerChip key={ticker} ticker={ticker} onClick={onTickerClick} />
          ))}
        </div>
      )}
    </div>
  )

  return (
    <GlassCard noHover className="overflow-hidden">
      <AccordionRow header={accordionHeader}>
        <div className="px-4 pb-4 pt-1">
          <p className="text-sm text-[#94a3b8] leading-relaxed">{article.summary}</p>
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-block text-xs text-[#6366f1] hover:text-[#818cf8] transition-colors"
            >
              Read full article →
            </a>
          )}
        </div>
      </AccordionRow>
    </GlassCard>
  )
}

interface BreakingNewsSectionProps {
  articles: NewsArticle[]
  onTickerClick: (ticker: string) => void
}

function BreakingNewsSection({ articles, onTickerClick }: BreakingNewsSectionProps) {
  if (articles.length === 0) return null

  return (
    <section aria-labelledby="breaking-news-heading" className="space-y-3">
      <div className="flex items-center gap-2">
        <Zap className="h-4 w-4 text-red-400" aria-hidden="true" />
        <h2
          id="breaking-news-heading"
          className="text-sm font-bold text-red-400 uppercase tracking-wider"
        >
          Breaking News
        </h2>
      </div>
      <div className="space-y-2">
        {articles.map((article) => (
          <NewsCard
            key={article.id}
            article={article}
            onTickerClick={onTickerClick}
            isBreaking
          />
        ))}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------

function NewsFeedSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading news">
      {Array.from({ length: 5 }).map((_, i) => (
        <GlassCard key={i} noHover className="p-4 space-y-2">
          <SkeletonPulse className="h-4 w-3/4" />
          <SkeletonPulse className="h-3 w-1/2" />
          <SkeletonPulse className="h-3 w-1/3" />
        </GlassCard>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function NewsFeedPage() {
  const navigate = useNavigate()

  // ── Filter state ───────────────────────────────────────────────────────
  const [tickerInput, setTickerInput] = useState('')
  const [tickerFilter, setTickerFilter] = useState<string | undefined>(undefined)
  const [tickerError, setTickerError] = useState<string | null>(null)
  const [sentimentFilter, setSentimentFilter] = useState<SentimentFilter>('all')
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all')

  // ── Pagination state ───────────────────────────────────────────────────
  const [offset, setOffset] = useState(0)
  // Accumulated articles across pages (for "load more" / infinite scroll)
  const [articles, setArticles] = useState<NewsArticle[]>([])

  // ── Scroll sentinel ref ────────────────────────────────────────────────
  const sentinelRef = useRef<HTMLDivElement>(null)
  const hasMoreRef = useRef(true)

  // ── Build query params ─────────────────────────────────────────────────
  const queryParams = {
    limit: PAGE_SIZE,
    offset,
    ...(tickerFilter ? { ticker: tickerFilter } : {}),
    ...(sentimentFilter !== 'all' ? { sentiment: sentimentFilter as 'positive' | 'neutral' | 'negative' } : {}),
    ...(categoryFilter !== 'all' ? { category: categoryFilter } : {}),
  }

  // ── Data fetch ─────────────────────────────────────────────────────────
  const {
    data,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.market.news(queryParams),
    queryFn: () => getNews(queryParams),
    staleTime: 60_000,
  })

  // Append new data to accumulated articles list
  useEffect(() => {
    if (data) {
      if (offset === 0) {
        // Fresh filter/search: replace the list
        setArticles(data)
      } else {
        // Subsequent page: append
        setArticles((prev) => {
          const existingIds = new Set(prev.map((a) => a.id))
          const newItems = data.filter((a) => !existingIds.has(a.id))
          return [...prev, ...newItems]
        })
      }
      // No more pages if the server returned fewer articles than requested
      hasMoreRef.current = data.length === PAGE_SIZE
    }
  }, [data, offset])

  // ── Helpers to apply filters (always resets offset) ────────────────────
  const applyTickerFilter = useCallback((value: string | undefined) => {
    setTickerFilter(value)
    setOffset(0)
    setArticles([])
  }, [])

  const applySentimentFilter = useCallback((value: SentimentFilter) => {
    setSentimentFilter(value)
    setOffset(0)
    setArticles([])
  }, [])

  const applyCategoryFilter = useCallback((value: CategoryFilter) => {
    setCategoryFilter(value)
    setOffset(0)
    setArticles([])
  }, [])

  // ── Ticker input handlers ───────────────────────────────────────────────
  const handleTickerInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 5)
    setTickerInput(raw)
    setTickerError(null)
    // Clear filter if input emptied
    if (raw === '') {
      applyTickerFilter(undefined)
    }
  }

  const handleTickerSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (tickerInput === '') {
      applyTickerFilter(undefined)
      return
    }
    if (!isValidTicker(tickerInput)) {
      setTickerError('Enter 1–5 uppercase letters.')
      return
    }
    applyTickerFilter(tickerInput)
  }

  const handleTickerClear = () => {
    setTickerInput('')
    setTickerError(null)
    applyTickerFilter(undefined)
  }

  // ── Navigation ─────────────────────────────────────────────────────────
  const handleTickerClick = useCallback(
    (ticker: string) => {
      navigate(`/stock/${ticker}`)
    },
    [navigate]
  )

  // ── Load next page ──────────────────────────────────────────────────────
  const loadMore = useCallback(() => {
    if (!isFetching && hasMoreRef.current) {
      setOffset((prev) => prev + PAGE_SIZE)
    }
  }, [isFetching])

  // ── Infinite scroll via IntersectionObserver ───────────────────────────
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMoreRef.current && !isFetching) {
          loadMore()
        }
      },
      { rootMargin: `${SCROLL_THRESHOLD_PX}px` }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [isFetching, loadMore])

  // ── Derived data ───────────────────────────────────────────────────────
  const breakingArticles = articles
    .filter((a) => a.is_breaking)
    .sort((a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime())
    .slice(0, BREAKING_MAX)

  // All articles (breaking ones are still shown in the main feed too)
  const allArticles = articles

  const isEmpty = !isLoading && !isFetching && allArticles.length === 0 && !isError

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl space-y-6">

          {/* Page header */}
          <header>
            <div className="flex items-center gap-3">
              <Newspaper className="h-6 w-6 text-[#6366f1]" aria-hidden="true" />
              <h1 className="text-2xl font-bold text-[#f1f5f9]">News Feed</h1>
            </div>
            <p className="mt-1 text-sm text-[#475569]">
              Latest market news, filtered and ranked by sentiment
            </p>
          </header>

          {/* Filter toolbar */}
          <section aria-label="News filters" className="space-y-3">
            {/* Ticker input */}
            <form onSubmit={handleTickerSubmit} className="flex items-start gap-2">
              <div className="flex-1 max-w-xs">
                <div className="relative">
                  <input
                    type="text"
                    value={tickerInput}
                    onChange={handleTickerInputChange}
                    placeholder="Filter by ticker (e.g. AAPL)"
                    aria-label="Filter by ticker symbol"
                    aria-describedby={tickerError ? 'ticker-error' : undefined}
                    aria-invalid={tickerError ? 'true' : 'false'}
                    maxLength={5}
                    className={cn(
                      'w-full rounded-lg bg-[#111827] border px-3 py-2 text-sm text-[#f1f5f9] placeholder:text-[#475569]',
                      'focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50',
                      tickerError ? 'border-red-500/60' : 'border-[#1f2d40]'
                    )}
                  />
                </div>
                {tickerError && (
                  <p
                    id="ticker-error"
                    role="alert"
                    className="mt-1 text-xs text-red-400"
                  >
                    {tickerError}
                  </p>
                )}
              </div>
              <button
                type="submit"
                className="rounded-lg bg-[#6366f1] px-3 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
              >
                Filter
              </button>
              {tickerFilter && (
                <button
                  type="button"
                  onClick={handleTickerClear}
                  className="rounded-lg border border-[#1f2d40] bg-[#111827] px-3 py-2 text-sm text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
                >
                  Clear
                </button>
              )}
            </form>

            {/* Sentiment filter */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-[#475569] font-medium">Sentiment:</span>
              {SENTIMENT_OPTIONS.map(({ label, value }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => applySentimentFilter(value)}
                  aria-pressed={sentimentFilter === value}
                  className={cn(
                    'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                    sentimentFilter === value
                      ? 'bg-[#6366f1] text-white'
                      : 'border border-[#1f2d40] text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#1a2235]'
                  )}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Category filter */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-[#475569] font-medium">Category:</span>
              {CATEGORY_OPTIONS.map(({ label, value }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => applyCategoryFilter(value)}
                  aria-pressed={categoryFilter === value}
                  className={cn(
                    'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                    categoryFilter === value
                      ? 'bg-[#6366f1] text-white'
                      : 'border border-[#1f2d40] text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#1a2235]'
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </section>

          {/* Error state */}
          {isError && (
            <section aria-live="assertive" className="space-y-3">
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-4 text-sm text-red-400">
                {error instanceof Error
                  ? error.message
                  : 'Failed to load news. Please try again.'}
              </div>
              <button
                type="button"
                onClick={() => refetch()}
                className="inline-flex items-center gap-2 rounded-lg border border-[#1f2d40] bg-[#111827] px-4 py-2 text-sm font-medium text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                Retry
              </button>
            </section>
          )}

          {/* Initial loading skeleton */}
          {isLoading && offset === 0 && <NewsFeedSkeleton />}

          {/* Content */}
          {!isLoading && !isError && (
            <div className="space-y-6">
              {/* Breaking News pinned section */}
              <BreakingNewsSection
                articles={breakingArticles}
                onTickerClick={handleTickerClick}
              />

              {/* All articles */}
              {allArticles.length > 0 && (
                <section aria-labelledby="all-news-heading" className="space-y-3">
                  {breakingArticles.length > 0 && (
                    <h2
                      id="all-news-heading"
                      className="text-sm font-semibold text-[#94a3b8] uppercase tracking-wider"
                    >
                      All News
                    </h2>
                  )}
                  <div className="space-y-2">
                    {allArticles.map((article) => (
                      <NewsCard
                        key={article.id}
                        article={article}
                        onTickerClick={handleTickerClick}
                        isBreaking={article.is_breaking}
                      />
                    ))}
                  </div>
                </section>
              )}

              {/* Empty state */}
              {isEmpty && (
                <div
                  role="status"
                  className="flex flex-col items-center justify-center rounded-xl border border-[#1f2d40] bg-[#111827] px-8 py-16 text-center"
                >
                  <Newspaper
                    className="mb-4 h-12 w-12 text-[#475569]"
                    aria-hidden="true"
                  />
                  <p className="text-sm font-semibold text-[#94a3b8]">
                    No news matching your filters.
                  </p>
                  <p className="mt-1 text-xs text-[#475569]">
                    Try adjusting the ticker, sentiment, or category filter.
                  </p>
                </div>
              )}

              {/* Loading more indicator */}
              {isFetching && offset > 0 && (
                <div className="space-y-2" aria-busy="true" aria-label="Loading more news">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <GlassCard key={i} noHover className="p-4 space-y-2">
                      <SkeletonPulse className="h-4 w-3/4" />
                      <SkeletonPulse className="h-3 w-1/2" />
                    </GlassCard>
                  ))}
                </div>
              )}

              {/* Scroll sentinel + manual "Load more" fallback */}
              {!isFetching && hasMoreRef.current && allArticles.length > 0 && (
                <div ref={sentinelRef} className="flex justify-center pt-2">
                  <button
                    type="button"
                    onClick={loadMore}
                    className="rounded-lg border border-[#1f2d40] bg-[#111827] px-5 py-2.5 text-sm font-medium text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#1a2235] transition-colors"
                  >
                    Load more
                  </button>
                </div>
              )}

              {/* End of feed indicator */}
              {!hasMoreRef.current && allArticles.length > 0 && (
                <p className="text-center text-xs text-[#475569] py-4">
                  You've reached the end of the news feed.
                </p>
              )}
            </div>
          )}

        </div>
      </main>
    </PageTransition>
  )
}
