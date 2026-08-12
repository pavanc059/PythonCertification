import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  Loader2,
  TrendingUp,
  TrendingDown,
  Clock,
  X,
  Flame,
  ChevronRight,
  AlertCircle,
} from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import { getQuote, getPrediction, getMovers } from '@/api/market'
import type { Quote, Prediction } from '@/api/market'
import { queryKeys } from '@/api/queryKeys'
import { cn } from '@/lib/utils'
import { formatCurrency, formatCompact } from '@/lib/formatters'

// ── Constants ─────────────────────────────────────────────────────────────────

const TICKER_RE = /^[A-Z0-9]{1,10}$/
const HISTORY_KEY = 'stockiq_search_history'
const MAX_HISTORY = 8

// ── localStorage helpers ──────────────────────────────────────────────────────

function loadHistory(): string[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]')
  } catch {
    return []
  }
}

function saveHistory(tickers: string[]): void {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(tickers.slice(0, MAX_HISTORY)))
  } catch { /* ignore */ }
}

function addToHistory(ticker: string): string[] {
  const current = loadHistory().filter((t) => t !== ticker)
  const updated = [ticker, ...current].slice(0, MAX_HISTORY)
  saveHistory(updated)
  return updated
}

// ── Trending tickers (fallback if movers not available) ───────────────────────

const FALLBACK_TRENDING = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL', 'META', 'AMD']

// ── Sub-components ────────────────────────────────────────────────────────────

interface QuoteCardProps {
  ticker: string
  quote: Quote
  prediction: Prediction | undefined
  onClick: () => void
}

function QuoteCard({ ticker, quote, prediction, onClick }: QuoteCardProps) {
  const positive = quote.change_pct >= 0
  const directionKey =
    prediction?.direction === 'bullish' || prediction?.direction === 'up' ? 'up' :
    prediction?.direction === 'bearish' || prediction?.direction === 'down' ? 'down' : 'neutral'

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      className={cn(
        'group w-full rounded-xl border border-[#1f2d40] bg-[#111827]',
        'p-4 cursor-pointer transition-all duration-150',
        'hover:border-[#6366f1]/40 hover:bg-[#1a2235]',
        'focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50',
      )}
      aria-label={`View ${ticker} detail page`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="rounded bg-[#6366f1]/20 px-2 py-0.5 text-xs font-bold text-[#6366f1] tracking-wide">
              {quote.ticker}
            </span>
            {prediction && (
              <span className={cn(
                'text-xs font-medium',
                directionKey === 'up' ? 'text-green-400' :
                directionKey === 'down' ? 'text-red-400' : 'text-[#94a3b8]'
              )}>
                {directionKey === 'up' ? '▲ Bullish' : directionKey === 'down' ? '▼ Bearish' : '— Neutral'}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-[#94a3b8] truncate">{quote.company_name}</p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-lg font-bold text-[#f1f5f9] tabular-nums">
            {formatCurrency(quote.price)}
          </p>
          <p className={cn('text-sm font-semibold tabular-nums', positive ? 'text-green-400' : 'text-red-400')}>
            {positive ? '+' : ''}{quote.change_pct.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* Stats row */}
      <div className="mt-3 grid grid-cols-4 gap-2 border-t border-[#1f2d40] pt-3">
        {[
          { label: 'High', value: formatCurrency(quote.day_high) },
          { label: 'Low', value: formatCurrency(quote.day_low) },
          { label: 'Volume', value: formatCompact(quote.volume ?? 0).replace('$', '') },
          { label: 'Mkt Cap', value: quote.market_cap ? formatCompact(quote.market_cap) : '—' },
        ].map(({ label, value }) => (
          <div key={label} className="flex flex-col gap-0.5">
            <span className="text-[10px] font-medium text-[#475569] uppercase tracking-wide">{label}</span>
            <span className="text-xs font-medium text-[#94a3b8] tabular-nums">{value}</span>
          </div>
        ))}
      </div>

      {/* CTA */}
      <div className="mt-3 flex items-center justify-end gap-1 text-xs text-[#6366f1] group-hover:text-[#818cf8] transition-colors">
        View full history
        <ChevronRight className="h-3.5 w-3.5" />
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function StockSearchPage() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)

  const [input, setInput] = useState('')
  const [submittedTicker, setSubmittedTicker] = useState<string | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [history, setHistory] = useState<string[]>(loadHistory)

  // Auto-focus search input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // ── Movers for trending section ──────────────────────────────────────────
  const { data: movers } = useQuery({
    queryKey: queryKeys.market.movers(),
    queryFn: getMovers,
    staleTime: 60_000,
  })

  const trendingTickers = movers?.gainers.length
    ? movers.gainers.slice(0, 8).map((g) => g.ticker)
    : FALLBACK_TRENDING

  // ── Quote + prediction for searched ticker ───────────────────────────────
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

  // ── Handlers ────────────────────────────────────────────────────────────

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10)
    setInput(val)
    setValidationError(null)
    if (submittedTicker && val !== submittedTicker) setSubmittedTicker(null)
  }

  const search = useCallback((ticker: string) => {
    if (!TICKER_RE.test(ticker)) {
      setValidationError('Enter 1–10 uppercase alphanumeric characters.')
      return
    }
    setValidationError(null)
    setInput(ticker)
    setSubmittedTicker(ticker)
    setHistory(addToHistory(ticker))
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    search(input)
  }

  const handleQuoteClick = () => {
    if (submittedTicker) navigate(`/stock/${submittedTicker}`)
  }

  const removeFromHistory = (ticker: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const updated = history.filter((t) => t !== ticker)
    setHistory(updated)
    saveHistory(updated)
  }

  const clearHistory = () => {
    setHistory([])
    saveHistory([])
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const is404 = quoteError && (quoteRawError as any)?.response?.status === 404
  const errorMessage = quoteError
    ? is404 ? `"${submittedTicker}" not found. Check the symbol and try again.`
    : 'Unable to load data — please try again.'
    : null

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl space-y-8">

          {/* ── Header ──────────────────────────────────────────────────── */}
          <div>
            <h1 className="text-2xl font-bold text-[#f1f5f9]">Stock Search</h1>
            <p className="mt-1 text-sm text-[#475569]">
              Search a ticker to view a live quote, price history, and AI signal.
            </p>
          </div>

          {/* ── Search bar ──────────────────────────────────────────────── */}
          <form onSubmit={handleSubmit} role="search" className="flex gap-2">
            <div className="relative flex-1">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#475569] pointer-events-none"
                aria-hidden="true"
              />
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={handleChange}
                placeholder="Enter ticker symbol (e.g. AAPL, MSFT, TSLA)"
                aria-label="Stock ticker search"
                autoCapitalize="characters"
                autoCorrect="off"
                spellCheck={false}
                className={cn(
                  'w-full pl-10 pr-4 py-3 rounded-xl text-sm',
                  'bg-[#111827] border text-[#f1f5f9] placeholder-[#475569]',
                  'focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50 transition-colors',
                  validationError ? 'border-red-500/50' : 'border-[#1f2d40] focus:border-[#6366f1]/50',
                )}
              />
            </div>
            <button
              type="submit"
              disabled={quoteLoading}
              className={cn(
                'flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold',
                'bg-[#6366f1] text-white hover:bg-[#818cf8] transition-colors',
                'disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50',
              )}
            >
              {quoteLoading
                ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                : <Search className="h-4 w-4" aria-hidden="true" />
              }
              Search
            </button>
          </form>

          {validationError && (
            <p className="-mt-6 text-xs text-red-400" role="alert">{validationError}</p>
          )}

          {/* ── Quote result ─────────────────────────────────────────────── */}
          {quoteLoading && (
            <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-6 flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-[#6366f1]" />
              <span className="text-sm text-[#475569]">Fetching {submittedTicker}…</span>
            </div>
          )}

          {errorMessage && !quoteLoading && (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
              <p className="text-sm text-red-400">{errorMessage}</p>
            </div>
          )}

          {quote && !quoteError && !quoteLoading && (
            <QuoteCard
              ticker={submittedTicker!}
              quote={quote}
              prediction={prediction}
              onClick={handleQuoteClick}
            />
          )}

          {/* ── Recent searches ──────────────────────────────────────────── */}
          {history.length > 0 && (
            <section aria-label="Recent searches">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-[#475569]" aria-hidden="true" />
                  <h2 className="text-sm font-semibold text-[#94a3b8] uppercase tracking-wide">
                    Recent
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={clearHistory}
                  className="text-xs text-[#475569] hover:text-[#94a3b8] transition-colors"
                >
                  Clear all
                </button>
              </div>

              <div className="flex flex-wrap gap-2">
                {history.map((ticker) => (
                  <div
                    key={ticker}
                    className="flex items-center gap-1 rounded-lg border border-[#1f2d40] bg-[#111827] pl-3 pr-1.5 py-1.5"
                  >
                    <button
                      type="button"
                      onClick={() => search(ticker)}
                      className="text-sm font-medium text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
                    >
                      {ticker}
                    </button>
                    <button
                      type="button"
                      aria-label={`Remove ${ticker} from history`}
                      onClick={(e) => removeFromHistory(ticker, e)}
                      className="ml-1 p-0.5 rounded text-[#475569] hover:text-red-400 transition-colors"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Trending stocks ──────────────────────────────────────────── */}
          <section aria-label="Trending stocks">
            <div className="flex items-center gap-2 mb-3">
              <Flame className="h-4 w-4 text-orange-400" aria-hidden="true" />
              <h2 className="text-sm font-semibold text-[#94a3b8] uppercase tracking-wide">
                Trending
              </h2>
              {movers?.gainers.length ? (
                <span className="text-xs text-[#475569]">Top gainers today</span>
              ) : (
                <span className="text-xs text-[#475569]">Popular stocks</span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {trendingTickers.map((ticker) => {
                const mover = movers?.gainers.find((g) => g.ticker === ticker)
                const positive = (mover?.price_change_pct ?? 0) >= 0
                return (
                  <button
                    key={ticker}
                    type="button"
                    onClick={() => search(ticker)}
                    className={cn(
                      'flex items-center justify-between gap-2 rounded-xl border border-[#1f2d40]',
                      'bg-[#111827] px-3 py-2.5 text-left transition-all duration-150',
                      'hover:border-[#6366f1]/40 hover:bg-[#1a2235]',
                      'focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50',
                    )}
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-[#f1f5f9] truncate">{ticker}</p>
                      {mover && (
                        <p className="text-xs text-[#475569] tabular-nums truncate">
                          {formatCurrency(mover.current_price)}
                        </p>
                      )}
                    </div>
                    {mover ? (
                      <span className={cn(
                        'shrink-0 text-xs font-semibold tabular-nums',
                        positive ? 'text-green-400' : 'text-red-400',
                      )}>
                        {positive
                          ? <TrendingUp className="inline h-3 w-3 mr-0.5" />
                          : <TrendingDown className="inline h-3 w-3 mr-0.5" />
                        }
                        {positive ? '+' : ''}{mover.price_change_pct.toFixed(1)}%
                      </span>
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-[#475569]" />
                    )}
                  </button>
                )
              })}
            </div>
          </section>

        </div>
      </main>
    </PageTransition>
  )
}
