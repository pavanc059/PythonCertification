import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Loader2, TrendingUp, TrendingDown } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getQuote, getPrediction, getTickerNews } from '@/api/market'
import type { Quote, Prediction, NewsArticle } from '@/api/market'
import { SentimentBadge } from '@/components/common'
import { queryKeys } from '@/api/queryKeys'
import { cn } from '@/lib/utils'

export interface StockSearchResult {
  quote: Quote
  prediction: Prediction
  news: NewsArticle[]
}

interface StockSearchBoxProps {
  onResult?: (data: StockSearchResult) => void
  className?: string
}

const TICKER_RE = /^[A-Z0-9]{1,10}$/

export function StockSearchBox({ className }: StockSearchBoxProps) {
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [submittedTicker, setSubmittedTicker] = useState<string | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Normalize to uppercase as user types
  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10)
    setInput(val)
    setValidationError(null)
    if (submittedTicker && val !== submittedTicker) setSubmittedTicker(null)
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!TICKER_RE.test(input)) {
      setValidationError('Enter 1–10 uppercase alphanumeric characters.')
      return
    }
    setSubmittedTicker(input)
  }

  const {
    data: quote,
    isLoading: quoteLoading,
    isError: quoteError,
    error: quoteRawError,
  } = useQuery({
    queryKey: queryKeys.market.quote(submittedTicker ?? ''),
    queryFn: () => getQuote(submittedTicker!),
    enabled: !!submittedTicker,
    retry: false,
  })

  const { data: prediction } = useQuery({
    queryKey: queryKeys.market.prediction(submittedTicker ?? ''),
    queryFn: () => getPrediction(submittedTicker!),
    enabled: !!submittedTicker && !!quote,
    retry: false,
  })

  const { data: tickerNews } = useQuery({
    queryKey: queryKeys.market.tickerNews(submittedTicker ?? ''),
    queryFn: () => getTickerNews(submittedTicker!, 2),
    enabled: !!submittedTicker && !!quote,
    retry: false,
  })

  // Navigate to stock detail on card click
  function handleNavigate() {
    if (submittedTicker) navigate(`/stock/${submittedTicker}`)
  }

  // Determine error message
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const is404 = quoteError && (quoteRawError as any)?.response?.status === 404
  const errorMessage = quoteError
    ? is404
      ? 'Symbol not found.'
      : 'Unable to load data — please try again.'
    : null

  const loading = quoteLoading

  return (
    <div className={cn('w-full', className)}>
      <form onSubmit={handleSubmit} role="search" className="flex gap-2">
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none"
            aria-hidden="true"
          />
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={handleChange}
            placeholder="Search ticker (e.g. AAPL)"
            aria-label="Stock ticker search"
            className={cn(
              'w-full pl-9 pr-4 py-2 rounded-lg text-sm',
              'bg-[#111827] border border-[#1f2d40] text-slate-200 placeholder-slate-500',
              'focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50 focus:border-[#6366f1]/50',
              'transition-colors'
            )}
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className={cn(
            'flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium',
            'bg-[#6366f1] text-white hover:bg-[#818cf8] transition-colors',
            'disabled:opacity-60 disabled:cursor-not-allowed'
          )}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
          Search
        </button>
      </form>

      {/* Validation error */}
      {validationError && (
        <p className="mt-1.5 text-xs text-red-400">{validationError}</p>
      )}

      {/* API error */}
      {errorMessage && (
        <p className="mt-1.5 text-xs text-red-400" role="alert">{errorMessage}</p>
      )}

      {/* Result card */}
      {quote && !quoteError && (
        <div
          role="button"
          tabIndex={0}
          onClick={handleNavigate}
          onKeyDown={(e) => e.key === 'Enter' && handleNavigate()}
          className={cn(
            'mt-3 p-3 rounded-xl border border-[#1f2d40] bg-[#111827]/80',
            'cursor-pointer hover:border-[#6366f1]/40 hover:bg-[#1a2235] transition-all'
          )}
          aria-label={`View details for ${quote.ticker}`}
        >
          {/* Header row */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <div>
              <span className="font-bold text-white text-sm">{quote.ticker}</span>
              {quote.company_name && (
                <span className="ml-1.5 text-xs text-slate-400 truncate">{quote.company_name}</span>
              )}
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-sm font-medium text-white">${quote.price.toFixed(2)}</p>
              <p className={cn(
                'text-xs font-medium',
                quote.change_pct >= 0 ? 'text-green-400' : 'text-red-400'
              )}>
                {quote.change_pct >= 0
                  ? <TrendingUp className="inline h-3 w-3 mr-0.5" />
                  : <TrendingDown className="inline h-3 w-3 mr-0.5" />
                }
                {quote.change_pct >= 0 ? '+' : ''}{quote.change_pct.toFixed(2)}%
              </p>
            </div>
          </div>

          {/* Volume */}
          <p className="text-xs text-slate-500 mb-2">
            Vol: {quote.volume >= 1_000_000
              ? `${(quote.volume / 1_000_000).toFixed(1)}M`
              : quote.volume >= 1_000
                ? `${(quote.volume / 1_000).toFixed(1)}K`
                : quote.volume}
          </p>

          {/* Prediction signal */}
          {prediction && (
            <div className="mb-2 flex items-center gap-2">
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
                ({Math.round(prediction.confidence * 100)}% confidence)
              </span>
            </div>
          )}

          {/* News snippets (up to 2) */}
          {tickerNews && tickerNews.length > 0 && (
            <div className="space-y-1.5 border-t border-[#1f2d40] pt-2">
              {tickerNews.slice(0, 2).map((article) => (
                <div key={article.id} className="flex items-start gap-2">
                  <SentimentBadge score={article.sentiment_score} className="mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-slate-300 line-clamp-2">{article.title}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
