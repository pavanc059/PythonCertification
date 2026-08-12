import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Plus, X, Loader2, TrendingUp, Trash2, LineChart, AlertCircle, ChevronRight } from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import { GlassCard } from '@/components/common/GlassCard'
import { ConfidenceBar } from '@/components/common/ConfidenceBar'
import { SkeletonPulse } from '@/components/common/SkeletonPulse'
import {
  getWatchlist,
  addToWatchlist,
  removeFromWatchlist,
} from '@/api/watchlist'
import type { WatchlistItem } from '@/api/watchlist'
import { getQuote, getPredictions } from '@/api/market'
import type { Quote, EnsemblePrediction } from '@/api/market'
import { queryKeys } from '@/api/queryKeys'
import { cn } from '@/lib/utils'
import { formatCurrency, formatCompact } from '@/lib/formatters'

// ── Animation variants ────────────────────────────────────────────────────────
const listItemVariants = {
  initial: { opacity: 0, x: -12 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 12 },
}
const listItemTransition = { duration: 0.18 }

/** Auto-refresh prices every 30 seconds */
const PRICE_REFETCH_INTERVAL = 30_000

/** Validate 1–10 uppercase alphanumeric characters */
const TICKER_REGEX = /^[A-Z0-9]{1,10}$/

// ── RemoveButton with 2-second confirmation tooltip ──────────────────────────
interface RemoveButtonProps {
  ticker: string
  onConfirm: () => void
  disabled?: boolean
}

function RemoveButton({ ticker, onConfirm, disabled }: RemoveButtonProps) {
  const [confirming, setConfirming] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Auto-dismiss confirmation after 2 seconds
  useEffect(() => {
    if (confirming) {
      timerRef.current = setTimeout(() => setConfirming(false), 2000)
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [confirming])

  const handleFirstClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (disabled) return
    setConfirming(true)
  }

  const handleConfirmClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (timerRef.current) clearTimeout(timerRef.current)
    setConfirming(false)
    onConfirm()
  }

  const handleCancelClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (timerRef.current) clearTimeout(timerRef.current)
    setConfirming(false)
  }

  if (confirming) {
    return (
      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
        <span className="text-xs text-[#94a3b8] whitespace-nowrap">Remove?</span>
        <button
          type="button"
          aria-label={`Confirm remove ${ticker}`}
          onClick={handleConfirmClick}
          className="px-2 py-1 text-xs rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
        >
          Yes
        </button>
        <button
          type="button"
          aria-label="Cancel remove"
          onClick={handleCancelClick}
          className="p-1 text-[#475569] hover:text-[#94a3b8] transition-colors"
        >
          <X className="h-3 w-3" aria-hidden="true" />
        </button>
      </div>
    )
  }

  return (
    <button
      type="button"
      aria-label={`Remove ${ticker} from watchlist`}
      onClick={handleFirstClick}
      disabled={disabled}
      className={cn(
        'p-1.5 rounded-md text-[#475569] hover:text-red-400 hover:bg-red-500/10',
        'transition-colors opacity-0 group-hover:opacity-100',
        disabled && 'cursor-not-allowed opacity-30'
      )}
    >
      <Trash2 className="h-4 w-4" aria-hidden="true" />
    </button>
  )
}

// ── WatchlistRow ──────────────────────────────────────────────────────────────
interface WatchlistRowProps {
  item: WatchlistItem
  quote: Quote | undefined
  quoteError: boolean
  prediction: EnsemblePrediction | undefined
  onRemove: (ticker: string) => void
  onNavigate: (ticker: string) => void
  isRemoving: boolean
}

function WatchlistRow({
  item,
  quote,
  quoteError,
  prediction,
  onRemove,
  onNavigate,
  isRemoving,
}: WatchlistRowProps) {
  const ticker = item.ticker

  const price = quoteError ? '--' : quote ? formatCurrency(quote.price) : null
  const changePct = quoteError
    ? '--'
    : quote
      ? `${quote.change_pct >= 0 ? '+' : ''}${quote.change_pct.toFixed(2)}%`
      : null
  const volume = quoteError ? '--' : quote ? formatCompact(quote.volume).replace('$', '') : null

  const isPositive = !quoteError && quote ? quote.change_pct >= 0 : null
  const confidenceValue = prediction ? Math.round(prediction.confidence * 100) : 0

  return (
    <motion.div
      layout
      variants={listItemVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={listItemTransition}
    >
      <GlassCard
        noHover
        className="group px-4 py-3"
      >
        <div className="flex items-center gap-3">
          {/* Ticker + company name */}
          <button
            type="button"
            onClick={() => onNavigate(ticker)}
            className="flex min-w-0 flex-1 items-center gap-3 text-left"
            aria-label={`View ${ticker} details`}
          >
            <div className="flex min-w-[4rem] flex-col">
              <span className="text-sm font-bold text-[#f1f5f9]">{ticker}</span>
              {quote?.company_name && (
                <span className="truncate text-xs text-[#475569] max-w-[8rem]">
                  {quote.company_name}
                </span>
              )}
            </div>

            {/* Price */}
            <div className="hidden sm:flex min-w-[4.5rem] flex-col items-end">
              {price === null ? (
                <SkeletonPulse className="h-4 w-14" />
              ) : (
                <span className="text-sm font-semibold text-[#f1f5f9]">{price}</span>
              )}
            </div>

            {/* Change % */}
            <div className="hidden sm:flex min-w-[4rem] flex-col items-end">
              {changePct === null ? (
                <SkeletonPulse className="h-4 w-12" />
              ) : (
                <span
                  className={cn(
                    'text-xs font-medium px-1.5 py-0.5 rounded',
                    changePct === '--'
                      ? 'text-[#475569]'
                      : isPositive
                        ? 'text-green-400 bg-green-500/10'
                        : 'text-red-400 bg-red-500/10'
                  )}
                >
                  {changePct}
                </span>
              )}
            </div>

            {/* Volume */}
            <div className="hidden md:flex min-w-[4rem] flex-col">
              {volume === null ? (
                <SkeletonPulse className="h-4 w-12" />
              ) : (
                <span className="text-xs text-[#475569]">
                  Vol: <span className="text-[#94a3b8]">{volume}</span>
                </span>
              )}
            </div>

            {/* ConfidenceBar */}
            <div className="hidden lg:flex min-w-[7rem] flex-col gap-1">
              {prediction ? (
                <>
                  <span className="text-xs text-[#475569]">
                    AI:{' '}
                    <span className="text-[#94a3b8]">{prediction.category}</span>
                  </span>
                  <ConfidenceBar
                    value={confidenceValue}
                    color="#6366f1"
                    className="w-full"
                  />
                </>
              ) : (
                <span className="text-xs text-[#475569]">—</span>
              )}
            </div>

            <ChevronRight className="h-4 w-4 text-[#475569] flex-shrink-0 ml-auto" aria-hidden="true" />
          </button>

          {/* Remove button */}
          <RemoveButton
            ticker={ticker}
            onConfirm={() => onRemove(ticker)}
            disabled={isRemoving}
          />
        </div>

        {/* Mobile: price + change row */}
        <div className="mt-2 flex items-center gap-3 sm:hidden">
          {price === null ? (
            <SkeletonPulse className="h-4 w-14" />
          ) : (
            <span className="text-sm font-semibold text-[#f1f5f9]">{price}</span>
          )}
          {changePct === null ? (
            <SkeletonPulse className="h-4 w-12" />
          ) : (
            <span
              className={cn(
                'text-xs font-medium px-1.5 py-0.5 rounded',
                changePct === '--'
                  ? 'text-[#475569]'
                  : isPositive
                    ? 'text-green-400 bg-green-500/10'
                    : 'text-red-400 bg-red-500/10'
              )}
            >
              {changePct}
            </span>
          )}
        </div>

        {/* Mobile: ConfidenceBar */}
        {prediction && (
          <div className="mt-2 flex flex-col gap-1 lg:hidden">
            <span className="text-xs text-[#475569]">
              AI confidence:{' '}
              <span className="text-[#94a3b8]">{prediction.category}</span>
            </span>
            <ConfidenceBar value={confidenceValue} color="#6366f1" />
          </div>
        )}
      </GlassCard>
    </motion.div>
  )
}

// ── AddTickerRow ──────────────────────────────────────────────────────────────
interface AddTickerRowProps {
  onAdd: (ticker: string) => void
  isPending: boolean
}

function AddTickerRow({ onAdd, isPending }: AddTickerRowProps) {
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '')
    setValue(raw)
    if (error) setError(null)
  }

  const handleSubmit = () => {
    const ticker = value.trim()
    if (!ticker) return
    if (!TICKER_REGEX.test(ticker)) {
      setError('Invalid ticker symbol.')
      return
    }
    onAdd(ticker)
    setValue('')
    setError(null)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={isPending}
          placeholder="Add ticker (e.g. AAPL)"
          maxLength={10}
          aria-label="Add ticker to watchlist"
          aria-describedby={error ? 'add-ticker-error' : undefined}
          aria-invalid={error ? 'true' : 'false'}
          className={cn(
            'flex-1 px-3 py-2 text-sm rounded-md',
            'bg-[#0a0e1a] border text-[#f1f5f9] placeholder:text-[#475569]',
            'focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50',
            'disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
            error ? 'border-red-500/70' : 'border-[#1f2d40]'
          )}
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isPending || !value.trim()}
          aria-label="Submit add ticker"
          className={cn(
            'flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md',
            'bg-[#6366f1] text-white hover:bg-[#4f52d9]',
            'disabled:opacity-50 disabled:cursor-not-allowed transition-colors'
          )}
        >
          {isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Plus className="h-4 w-4" aria-hidden="true" />
          )}
          Add
        </button>
      </div>

      {error && (
        <p
          id="add-ticker-error"
          role="alert"
          className="flex items-center gap-1 text-xs text-red-400"
        >
          <AlertCircle className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  )
}

// ── WatchlistPage ─────────────────────────────────────────────────────────────

export default function WatchlistPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [addError, setAddError] = useState<string | null>(null)
  const addInputRef = useRef<HTMLDivElement>(null)

  // ── Queries ───────────────────────────────────────────────────────────────

  const {
    data: items = [],
    isLoading: itemsLoading,
  } = useQuery({
    queryKey: queryKeys.watchlist.items(),
    queryFn: getWatchlist,
    refetchInterval: PRICE_REFETCH_INTERVAL,
  })

  const tickers = Array.from(new Set(items.map((i) => i.ticker)))

  // Per-ticker quote queries
  const quoteResults = useQueries({
    queries: tickers.map((ticker) => ({
      queryKey: queryKeys.market.quote(ticker),
      queryFn: () => getQuote(ticker),
      refetchInterval: PRICE_REFETCH_INTERVAL,
      staleTime: 15_000,
      retry: 1,
    })),
  })

  const quoteMap = Object.fromEntries(
    tickers.map((ticker, i) => [ticker, quoteResults[i]?.data])
  )
  const quoteErrorMap = Object.fromEntries(
    tickers.map((ticker, i) => [ticker, !!quoteResults[i]?.isError])
  )

  // Predictions for all watchlist tickers
  const { data: predictions = [] } = useQuery({
    queryKey: queryKeys.market.predictions(tickers),
    queryFn: () => getPredictions(tickers),
    enabled: tickers.length > 0,
    staleTime: 120_000,
  })

  const predictionMap = Object.fromEntries(
    predictions.map((p) => [p.ticker, p])
  )

  // ── Mutations ─────────────────────────────────────────────────────────────

  const addMutation = useMutation({
    mutationFn: (ticker: string) => addToWatchlist({ ticker, list_name: 'Default' }),
    onSuccess: () => {
      setAddError(null)
      void queryClient.invalidateQueries({ queryKey: queryKeys.watchlist.items() })
    },
    onError: (err: unknown) => {
      // 404 means ticker not found
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        setAddError('Invalid ticker symbol.')
      } else {
        setAddError('Failed to add ticker. Please try again.')
      }
    },
  })

  const removeMutation = useMutation({
    mutationFn: (ticker: string) => removeFromWatchlist(ticker),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.watchlist.items() })
    },
  })

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleAdd = (ticker: string) => {
    setAddError(null)
    addMutation.mutate(ticker)
  }

  const handleRemove = (ticker: string) => {
    removeMutation.mutate(ticker)
  }

  const handleNavigate = (ticker: string) => {
    navigate(`/stock/${ticker}`)
  }

  const focusAddInput = () => {
    const input = addInputRef.current?.querySelector('input')
    input?.focus()
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl space-y-6">

          {/* ── Page Header ───────────────────────────────────────────── */}
          <header className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-3">
                <TrendingUp className="h-6 w-6 text-[#6366f1]" aria-hidden="true" />
                <h1 className="text-2xl font-bold text-[#f1f5f9]">Watchlist</h1>
                {!itemsLoading && (
                  <span className="rounded-full bg-[#6366f1]/15 px-2.5 py-0.5 text-xs font-semibold text-[#6366f1]">
                    {items.length} {items.length === 1 ? 'stock' : 'stocks'}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-[#475569]">
                Track stocks with live quotes and AI predictions
              </p>
            </div>
          </header>

          {/* ── Add ticker input ─────────────────────────────────────── */}
          <div ref={addInputRef}>
            <AddTickerRow
              onAdd={handleAdd}
              isPending={addMutation.isPending}
            />
            {/* Mutation-level error (e.g. 404 invalid ticker) */}
            {addError && !addMutation.isPending && (
              <p role="alert" className="mt-1 flex items-center gap-1 text-xs text-red-400">
                <AlertCircle className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                {addError}
              </p>
            )}
          </div>

          {/* ── Loading skeleton ─────────────────────────────────────── */}
          {itemsLoading && (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonPulse key={i} className="h-16 w-full" />
              ))}
            </div>
          )}

          {/* ── Empty state ──────────────────────────────────────────── */}
          {!itemsLoading && items.length === 0 && (
            <GlassCard noHover className="flex flex-col items-center justify-center px-8 py-16 text-center">
              <LineChart
                className="mb-4 h-16 w-16 text-[#475569]"
                aria-hidden="true"
              />
              <h2 className="text-base font-semibold text-[#94a3b8]">
                Your watchlist is empty
              </h2>
              <p className="mt-2 text-sm text-[#475569]">
                Search for a ticker above and add it to start tracking quotes and AI predictions.
              </p>
              <button
                type="button"
                onClick={focusAddInput}
                className="mt-6 inline-flex items-center gap-2 rounded-lg bg-[#6366f1] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#4f52d9] focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50"
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                Add Your First Stock
              </button>
            </GlassCard>
          )}

          {/* ── Column headers ────────────────────────────────────────── */}
          {!itemsLoading && items.length > 0 && (
            <div className="hidden sm:flex items-center gap-3 px-4 text-xs text-[#475569] font-medium">
              <span className="min-w-[4rem]">Ticker</span>
              <span className="min-w-[4.5rem] text-right">Price</span>
              <span className="min-w-[4rem] text-right">Change</span>
              <span className="hidden md:block min-w-[4rem]">Volume</span>
              <span className="hidden lg:block min-w-[7rem]">AI Prediction</span>
            </div>
          )}

          {/* ── Watchlist rows ────────────────────────────────────────── */}
          {!itemsLoading && items.length > 0 && (
            <AnimatePresence mode="sync">
              <div className="space-y-2">
                {items.map((item) => (
                  <WatchlistRow
                    key={item.id || item.ticker}
                    item={item}
                    quote={quoteMap[item.ticker]}
                    quoteError={quoteErrorMap[item.ticker] ?? false}
                    prediction={predictionMap[item.ticker]}
                    onRemove={handleRemove}
                    onNavigate={handleNavigate}
                    isRemoving={removeMutation.isPending}
                  />
                ))}
              </div>
            </AnimatePresence>
          )}

        </div>
      </main>
    </PageTransition>
  )
}
