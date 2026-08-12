import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useWebSocket } from '@/hooks/useWebSocket'
import {
  ArrowLeft, AlertCircle,
  Activity, Newspaper, ExternalLink, ShoppingCart, Trash2,
} from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import { CandlestickChart } from '@/components/charts/CandlestickChart'
import { OrderTicket } from '@/components/trading/OrderTicket'
import { getQuote, getPrediction, getTickerNews, getEarnings } from '@/api/market'
import { getSettings } from '@/api/settings'
import { queryKeys } from '@/api/queryKeys'
import { cn } from '@/lib/utils'
import { formatCurrency, formatCompact, formatDate } from '@/lib/formatters'
import type { OrderSide } from '@/api/trading'
import type { Quote, Prediction, NewsArticle } from '@/api/market'
import { AIResearchPanel } from '@/components/ai/AIResearchPanel'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function Sk({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded bg-[#1a2235]', className)} aria-hidden />
}

function PanelHeader({ label, icon }: { label: string; icon?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b border-[#1f2d40]">
      {icon}
      <span className="text-[10px] font-bold text-[#475569] uppercase tracking-widest">{label}</span>
    </div>
  )
}

function StatRow({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#1a2235] last:border-0">
      <span className="text-xs text-[#475569]">{label}</span>
      <span className={cn('text-xs font-semibold tabular-nums text-[#94a3b8]', valueClass)}>{value}</span>
    </div>
  )
}


// ─── Direction normalisation ──────────────────────────────────────────────────

function normDir(d?: string): 'bullish' | 'bearish' | 'neutral' {
  if (d === 'bullish' || d === 'up') return 'bullish'
  if (d === 'bearish' || d === 'down') return 'bearish'
  return 'neutral'
}

const DIR_BADGE: Record<string, { label: string; cls: string }> = {
  bullish: { label: 'BULLISH', cls: 'bg-green-500/20 text-green-400 border border-green-500/30' },
  bearish: { label: 'BEARISH', cls: 'bg-red-500/20 text-red-400 border border-red-500/30' },
  neutral: { label: 'NEUTRAL', cls: 'bg-[#475569]/20 text-[#94a3b8] border border-[#475569]/30' },
}

// ─── Sub-panels ───────────────────────────────────────────────────────────────

function TechnicalsPanel({ prediction, loading }: { prediction?: Prediction; loading: boolean }) {
  const rsi = prediction?.rsi_14
  const macd = prediction?.macd_signal ?? 'neutral'
  const cross = prediction?.sma_cross ?? 'neutral'

  const rsiColor = rsi == null ? 'text-[#94a3b8]' : rsi > 70 ? 'text-red-400' : rsi < 30 ? 'text-green-400' : 'text-[#94a3b8]'
  const rsiLabel = rsi == null ? '—' : rsi > 70 ? 'Overbought' : rsi < 30 ? 'Oversold' : 'Neutral'
  const macdColor = macd === 'bullish' ? 'text-green-400' : macd === 'bearish' ? 'text-red-400' : 'text-[#94a3b8]'
  const crossColor = cross === 'golden_cross' ? 'text-green-400' : cross === 'death_cross' ? 'text-red-400' : 'text-[#94a3b8]'
  const crossLabel = cross === 'golden_cross' ? 'Golden Cross' : cross === 'death_cross' ? 'Death Cross' : 'Neutral'

  return (
    <div className="rounded border border-[#1f2d40] bg-[#0d1424] overflow-hidden">
      <PanelHeader label="Technical" icon={<Activity className="h-3 w-3 text-[#475569]" />} />
      {loading ? (
        <div className="p-3 space-y-2">{[...Array(4)].map((_, i) => <Sk key={i} className="h-5 w-full" />)}</div>
      ) : (
        <>
          <StatRow label="RSI (14)" value={rsi != null ? `${rsi.toFixed(1)} — ${rsiLabel}` : '—'} valueClass={rsiColor} />
          <StatRow label="MACD Signal" value={macd.charAt(0).toUpperCase() + macd.slice(1)} valueClass={macdColor} />
          <StatRow label="SMA Cross" value={crossLabel} valueClass={crossColor} />
          <StatRow label="AI Confidence" value={prediction ? `${prediction.confidence.toFixed(1)}%` : '—'} />
        </>
      )}
    </div>
  )
}


function PredictionPanel({ prediction, loading }: { prediction?: Prediction; loading: boolean }) {
  const dir = normDir(prediction?.direction)
  const badge = DIR_BADGE[dir]
  const factors = prediction?.factors ? Object.entries(prediction.factors).sort(([, a], [, b]) => Math.abs(b) - Math.abs(a)).slice(0, 5) : []
  const maxAbs = factors[0] ? Math.abs(factors[0][1]) : 1

  return (
    <div className="rounded border border-[#1f2d40] bg-[#0d1424] overflow-hidden">
      <PanelHeader label="AI · Model Signal" />
      {loading ? (
        <div className="p-3 space-y-2">{[...Array(4)].map((_, i) => <Sk key={i} className="h-5 w-full" />)}</div>
      ) : prediction ? (
        <div className="p-3 space-y-3">
          <span className={cn('inline-block rounded px-2 py-0.5 text-xs font-bold tracking-widest', badge.cls)}>{badge.label}</span>
          {/* Confidence bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-[10px] text-[#475569]">
              <span>Confidence</span><span>{prediction.confidence.toFixed(1)}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-[#1a2235] overflow-hidden">
              <div className={cn('h-full rounded-full', dir === 'bullish' ? 'bg-green-400' : dir === 'bearish' ? 'bg-red-400' : 'bg-[#475569]')}
                style={{ width: `${Math.min(prediction.confidence, 100)}%` }} />
            </div>
          </div>
          {/* Key factors */}
          {factors.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-bold text-[#475569] uppercase tracking-widest">Key Factors</p>
              {factors.map(([name, val]) => {
                const pos = val >= 0
                const w = Math.round((Math.abs(val) / maxAbs) * 100)
                return (
                  <div key={name} className="flex items-center gap-2">
                    <span className="w-12 shrink-0 text-[10px] text-[#475569] truncate">{name}</span>
                    <div className="flex-1 h-1 rounded-full bg-[#1a2235] overflow-hidden">
                      <div className={cn('h-full rounded-full', pos ? 'bg-green-400' : 'bg-red-400')} style={{ width: `${w}%` }} />
                    </div>
                    <span className={cn('w-10 shrink-0 text-right text-[10px] tabular-nums', pos ? 'text-green-400' : 'text-red-400')}>
                      {pos ? '+' : ''}{val.toFixed(2)}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ) : (
        <div className="p-3 flex items-center gap-2 text-xs text-[#475569]">
          <AlertCircle className="h-4 w-4 shrink-0" />Prediction unavailable
        </div>
      )}
    </div>
  )
}


function NewsPanel({ news, loading }: { news?: NewsArticle[]; loading: boolean }) {
  // Aggregate sentiment across all articles
  const sentScores = news?.map((a) => a.sentiment_score) ?? []
  const avgSent = sentScores.length ? sentScores.reduce((s, v) => s + v, 0) / sentScores.length : null
  const bullishCount = sentScores.filter((s) => s > 0.15).length
  const bearishCount = sentScores.filter((s) => s < -0.15).length
  const neutralCount = sentScores.length - bullishCount - bearishCount

  function sentColor(score: number) {
    if (score > 0.15) return 'text-green-400'
    if (score < -0.15) return 'text-red-400'
    return 'text-[#475569]'
  }
  function sentBg(score: number) {
    if (score > 0.15) return 'bg-green-500'
    if (score < -0.15) return 'bg-red-500'
    return 'bg-[#475569]'
  }
  function sentLabel(score: number) {
    if (score > 0.5) return 'Bullish'
    if (score > 0.15) return 'Pos'
    if (score < -0.5) return 'Bearish'
    if (score < -0.15) return 'Neg'
    return 'Neutral'
  }

  return (
    <div className="rounded border border-[#1f2d40] bg-[#0d1424] overflow-hidden flex flex-col">
      <PanelHeader label="News Feed" icon={<Newspaper className="h-3 w-3 text-[#475569]" />} />

      {/* ── Sentiment summary bar ── */}
      {!loading && sentScores.length > 0 && (
        <div className="px-3 py-2 border-b border-[#1a2235] space-y-1.5">
          <div className="flex items-center justify-between text-[10px] text-[#475569]">
            <span>News Sentiment ({sentScores.length} articles)</span>
            {avgSent != null && (
              <span className={cn('font-bold', sentColor(avgSent))}>
                {avgSent > 0 ? '+' : ''}{avgSent.toFixed(2)} · {sentLabel(avgSent)}
              </span>
            )}
          </div>
          {/* Stacked bar: bullish / neutral / bearish */}
          <div className="flex h-1.5 rounded-full overflow-hidden gap-px bg-[#1a2235]">
            {bullishCount > 0 && (
              <div className="bg-green-500 rounded-l-full transition-all"
                style={{ width: `${(bullishCount / sentScores.length) * 100}%` }} />
            )}
            {neutralCount > 0 && (
              <div className="bg-[#334155] transition-all"
                style={{ width: `${(neutralCount / sentScores.length) * 100}%` }} />
            )}
            {bearishCount > 0 && (
              <div className="bg-red-500 rounded-r-full transition-all"
                style={{ width: `${(bearishCount / sentScores.length) * 100}%` }} />
            )}
          </div>
          <div className="flex items-center gap-3 text-[10px]">
            <span className="text-green-400">{bullishCount} Bullish</span>
            <span className="text-[#475569]">{neutralCount} Neutral</span>
            <span className="text-red-400">{bearishCount} Bearish</span>
          </div>
        </div>
      )}

      {/* ── Article list ── */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#1a2235]">
        {loading && [...Array(5)].map((_, i) => (
          <div key={i} className="p-3 space-y-1.5">
            <Sk className="h-3 w-full" />
            <Sk className="h-3 w-3/4" />
            <Sk className="h-2 w-1/2" />
          </div>
        ))}
        {!loading && (!news || news.length === 0) && (
          <p className="p-3 text-xs text-[#475569]">No news available.</p>
        )}
        {!loading && news?.map((a) => (
          <div key={a.id} className="p-3 space-y-1.5 hover:bg-[#111827] transition-colors group">
            {/* Title + link */}
            <div className="flex items-start justify-between gap-2">
              <p className="text-xs text-[#e2e8f0] leading-snug line-clamp-3 group-hover:text-white transition-colors">
                {a.is_breaking && (
                  <span className="mr-1.5 inline-block rounded px-1 py-px text-[9px] font-black bg-orange-500/20 text-orange-400 uppercase tracking-wide align-middle">
                    Breaking
                  </span>
                )}
                {a.title}
              </p>
              {a.url && (
                <a href={a.url} target="_blank" rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="shrink-0 text-[#334155] hover:text-[#6366f1] transition-colors mt-0.5">
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>

            {/* Sentiment score bar */}
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 rounded-full bg-[#1a2235] overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all', sentBg(a.sentiment_score))}
                  style={{ width: `${Math.min(Math.abs(a.sentiment_score) * 100, 100)}%` }}
                />
              </div>
              <span className={cn('text-[10px] font-semibold tabular-nums w-16 text-right shrink-0', sentColor(a.sentiment_score))}>
                {a.sentiment_score > 0 ? '+' : ''}{a.sentiment_score.toFixed(3)}
              </span>
            </div>

            {/* Meta */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] font-medium text-[#6366f1]">{a.source}</span>
              <span className="text-[10px] text-[#334155]">·</span>
              <span className="text-[10px] text-[#475569]">{formatDate(a.published_at)}</span>
              {a.category && a.category !== 'General' && (
                <>
                  <span className="text-[10px] text-[#334155]">·</span>
                  <span className="text-[10px] text-[#475569]">{a.category}</span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


function EarningsPanel({ earnings, loading }: { earnings?: import('@/api/market').EarningsData; loading: boolean }) {
  const hasNext = !!earnings?.next_earnings_date
  const hasHistory = (earnings?.history?.length ?? 0) > 0

  function surpriseColor(pct: number | null) {
    if (pct == null) return 'text-[#475569]'
    if (pct > 0) return 'text-green-400'
    if (pct < 0) return 'text-red-400'
    return 'text-[#94a3b8]'
  }

  return (
    <div className="rounded border border-[#1f2d40] bg-[#0d1424] overflow-hidden">
      <PanelHeader label="Earnings" icon={<span className="text-[10px]">📊</span>} />
      {loading ? (
        <div className="p-3 space-y-2">{[...Array(3)].map((_, i) => <Sk key={i} className="h-5 w-full" />)}</div>
      ) : (
        <div className="divide-y divide-[#1a2235]">
          {/* Next earnings */}
          <div className="px-3 py-2 space-y-0.5">
            <p className="text-[10px] text-[#475569] uppercase tracking-widest">Next Report</p>
            {hasNext ? (
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#f1f5f9]">{earnings!.next_earnings_date}</span>
                {earnings?.eps_estimate != null && (
                  <span className="text-[10px] text-[#475569]">
                    Est. EPS <span className="text-[#94a3b8] font-semibold">{earnings.eps_estimate.toFixed(2)}</span>
                  </span>
                )}
              </div>
            ) : (
              <p className="text-xs text-[#475569]">Date not available</p>
            )}
          </div>

          {/* History table */}
          {hasHistory && (
            <div className="px-3 py-2">
              <p className="text-[10px] text-[#475569] uppercase tracking-widest mb-2">Last {earnings!.history.length}Q History</p>
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="text-[#334155]">
                    <th className="text-left font-medium pb-1">Quarter</th>
                    <th className="text-right font-medium pb-1">Est</th>
                    <th className="text-right font-medium pb-1">Act</th>
                    <th className="text-right font-medium pb-1">Surp%</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1a2235]">
                  {earnings!.history.slice().reverse().map((row, i) => (
                    <tr key={i} className="hover:bg-[#111827] transition-colors">
                      <td className="py-1 text-[#475569]">{row.quarter}</td>
                      <td className="py-1 text-right text-[#94a3b8] tabular-nums">
                        {row.eps_estimate != null ? row.eps_estimate.toFixed(2) : '—'}
                      </td>
                      <td className="py-1 text-right text-[#94a3b8] tabular-nums">
                        {row.eps_actual != null ? row.eps_actual.toFixed(2) : '—'}
                      </td>
                      <td className={cn('py-1 text-right font-semibold tabular-nums', surpriseColor(row.surprise_pct))}>
                        {row.surprise_pct != null ? `${row.surprise_pct > 0 ? '+' : ''}${row.surprise_pct.toFixed(1)}%` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!hasNext && !hasHistory && (
            <p className="p-3 text-xs text-[#475569]">No earnings data available.</p>
          )}
        </div>
      )}
    </div>
  )
}

function QuoteStatsPanel({ quote, loading }: { quote?: Quote; loading: boolean }) {
  const wk52High = quote?.week_52_high
  const wk52Low = quote?.week_52_low
  const pct52 = wk52High && wk52Low && quote?.price
    ? ((quote.price - wk52Low) / (wk52High - wk52Low)) * 100
    : null

  return (
    <div className="rounded border border-[#1f2d40] bg-[#0d1424] overflow-hidden">
      <PanelHeader label="Key Stats" />
      {loading ? (
        <div className="p-3 space-y-2">{[...Array(6)].map((_, i) => <Sk key={i} className="h-5 w-full" />)}</div>
      ) : (
        <>
          <StatRow label="Market Cap" value={quote?.market_cap ? formatCompact(quote.market_cap) : '—'} />
          <StatRow label="P/E Ratio" value={quote?.pe_ratio != null ? quote.pe_ratio.toFixed(1) : '—'} />
          <StatRow label="Sector" value={quote?.sector ?? '—'} />
          <StatRow label="Volume" value={quote?.volume ? formatCompact(quote.volume).replace('$','') : '—'} />
          <StatRow label="52-Wk High" value={wk52High ? formatCurrency(wk52High) : '—'} valueClass="text-green-400" />
          <StatRow label="52-Wk Low" value={wk52Low ? formatCurrency(wk52Low) : '—'} valueClass="text-red-400" />
          {pct52 != null && (
            <div className="px-3 py-2 space-y-1">
              <div className="flex justify-between text-[10px] text-[#475569]">
                <span>52-Wk Range</span><span>{pct52.toFixed(0)}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-[#1a2235] overflow-hidden">
                <div className="h-full rounded-full bg-[#6366f1]" style={{ width: `${Math.min(pct52, 100)}%` }} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}


// ─── Main component ───────────────────────────────────────────────────────────

export default function StockDetailPage() {
  const { ticker = '' } = useParams<{ ticker: string }>()
  const navigate = useNavigate()

  const normalizedTicker = ticker.toUpperCase()
  const isInvalidTicker = !/^[A-Z0-9]{1,10}$/.test(normalizedTicker) || normalizedTicker === 'SEARCH'

  const [orderTicketOpen, setOrderTicketOpen] = useState(false)
  const [orderSide, setOrderSide] = useState<OrderSide>('buy')
  const [priceFlash, setPriceFlash] = useState<'up' | 'down' | null>(null)
  const prevPriceRef = useRef<number | null>(null)
  // Period-aware % change — updated by CandlestickChart whenever data loads
  const [periodPct, setPeriodPct] = useState<{ range: string; pct: number } | null>(null)

  // Feature flags — controls whether WebSocket streaming is active
  const { data: appSettings } = useQuery({
    queryKey: queryKeys.settings.config(),
    queryFn: getSettings,
    staleTime: 300_000,
  })
  const streamingEnabled = appSettings?.feature_flags.real_time_streaming ?? false

  const { subscribe, unsubscribe } = useWebSocket({
    tickers: [normalizedTicker],
    onPriceUpdate: (prices) => {
      const np = prices[normalizedTicker]
      if (np == null) return
      if (prevPriceRef.current !== null) {
        setPriceFlash(np >= prevPriceRef.current ? 'up' : 'down')
        setTimeout(() => setPriceFlash(null), 600)
      }
      prevPriceRef.current = np
    },
    enabled: streamingEnabled,
  })

  useEffect(() => {
    subscribe([normalizedTicker])
    return () => unsubscribe([normalizedTicker])
  }, [normalizedTicker, subscribe, unsubscribe])

  useEffect(() => {
    if (isInvalidTicker) navigate('/stock/search', { replace: true })
  }, [isInvalidTicker, navigate])

  const enabled = normalizedTicker.length > 0 && !isInvalidTicker

  const { data: quote, isLoading: quoteLoading, isError: quoteError } = useQuery({
    queryKey: queryKeys.market.quote(normalizedTicker),
    queryFn: () => getQuote(normalizedTicker),
    enabled, refetchInterval: 30_000, staleTime: 15_000,
  })

  const { data: prediction, isLoading: predLoading } = useQuery({
    queryKey: queryKeys.market.prediction(normalizedTicker),
    queryFn: () => getPrediction(normalizedTicker),
    enabled, staleTime: 60_000,
  })

  const { data: news, isLoading: newsLoading } = useQuery({
    queryKey: queryKeys.market.tickerNews(normalizedTicker),
    queryFn: () => getTickerNews(normalizedTicker, 20),
    enabled, staleTime: 300_000,  // 5 min — matches backend cache
  })

  const { data: earnings, isLoading: earningsLoading } = useQuery({
    queryKey: queryKeys.market.earnings(normalizedTicker),
    queryFn: () => getEarnings(normalizedTicker),
    enabled, staleTime: 14_400_000,  // 4h — matches backend cache
  })

  const positive = (quote?.change ?? 0) >= 0
  const dir = normDir(prediction?.direction)
  const badge = DIR_BADGE[dir]


  return (
    <PageTransition>
      <div className="min-h-full bg-[#080c14] text-[#f1f5f9] flex flex-col">

        {/* ── Top header bar ──────────────────────────────────────────── */}
        <div className="border-b border-[#1f2d40] bg-[#0a0e1a] px-4 py-2.5 flex items-center gap-4 flex-wrap">
          <button type="button" onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-xs text-[#475569] hover:text-[#94a3b8] transition-colors shrink-0">
            <ArrowLeft className="h-3.5 w-3.5" />Back
          </button>

          {/* Ticker + company */}
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-lg font-black text-white tracking-wide shrink-0">{normalizedTicker}</span>
            {quoteLoading
              ? <Sk className="h-4 w-40" />
              : <span className="text-sm text-[#475569] truncate">{quote?.company_name}</span>
            }
          </div>

          {/* Price block */}
          {quoteLoading ? <Sk className="h-7 w-28" /> : quoteError ? (
            <span className="text-xs text-red-400 flex items-center gap-1"><AlertCircle className="h-3 w-3" />Quote unavailable</span>
          ) : quote && (
            <div className="flex items-baseline gap-2 shrink-0">
              <span className={cn('text-2xl font-bold tabular-nums transition-colors duration-300',
                priceFlash === 'up' ? 'text-green-400' : priceFlash === 'down' ? 'text-red-400' : 'text-white')}>
                {formatCurrency(quote.price)}
              </span>
              {/* Show period % when chart has loaded, otherwise fall back to intraday */}
              {periodPct ? (
                <span className={cn('text-sm font-semibold tabular-nums', periodPct.pct >= 0 ? 'text-green-400' : 'text-red-400')}>
                  {periodPct.pct >= 0 ? '+' : ''}{periodPct.pct.toFixed(2)}%
                  <span className="ml-1 text-[10px] text-[#475569] font-normal">{periodPct.range}</span>
                </span>
              ) : (
                <span className={cn('text-sm font-semibold tabular-nums', positive ? 'text-green-400' : 'text-red-400')}>
                  {positive ? '+' : ''}{formatCurrency(quote.change)} ({positive ? '+' : ''}{quote.change_pct.toFixed(2)}%)
                  <span className="ml-1 text-[10px] text-[#475569] font-normal">1D</span>
                </span>
              )}
              <span className="flex items-center gap-1 text-[10px] text-[#475569]">
                <span className={cn(
                  'h-1.5 w-1.5 rounded-full inline-block',
                  streamingEnabled ? 'bg-green-400 animate-pulse' : 'bg-[#475569]',
                )} />
                {streamingEnabled ? 'Live' : 'Polling'}
              </span>
            </div>
          )}

          {/* Signal badge */}
          {prediction && (
            <span className={cn('shrink-0 rounded px-2 py-0.5 text-[10px] font-black tracking-widest', badge.cls)}>
              {badge.label} · MODEL SIGNAL
            </span>
          )}

          {/* Stat pills */}
          {quote && (
            <div className="flex items-center gap-4 ml-auto flex-wrap text-xs">
              {quote.market_cap && <span className="text-[#475569]">Mkt Cap <span className="text-[#94a3b8] font-semibold">{formatCompact(quote.market_cap)}</span></span>}
              {quote.sector && <span className="text-[#475569]">Sector <span className="text-[#94a3b8] font-semibold">{quote.sector}</span></span>}
              {quote.week_52_high && <span className="text-[#475569]">52W H <span className="text-green-400 font-semibold">{formatCurrency(quote.week_52_high)}</span></span>}
              {quote.week_52_low && <span className="text-[#475569]">52W L <span className="text-red-400 font-semibold">{formatCurrency(quote.week_52_low)}</span></span>}
            </div>
          )}

          {/* Buy / Sell */}
          <div className="flex gap-2 shrink-0 ml-2">
            <button type="button" onClick={() => { setOrderSide('buy'); setOrderTicketOpen(true) }}
              className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-bold bg-green-600 hover:bg-green-500 text-white transition-colors">
              <ShoppingCart className="h-3 w-3" />Buy
            </button>
            <button type="button" onClick={() => { setOrderSide('sell'); setOrderTicketOpen(true) }}
              className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-bold bg-red-600 hover:bg-red-500 text-white transition-colors">
              <Trash2 className="h-3 w-3" />Sell
            </button>
          </div>
        </div>


        {/* ── 3-column terminal body ───────────────────────────────────── */}
        <div className="flex flex-1 overflow-hidden min-h-0">

          {/* LEFT sidebar — stats + technicals + prediction */}
          <div className="w-56 shrink-0 border-r border-[#1f2d40] overflow-y-auto flex flex-col gap-3 p-2 bg-[#0a0e1a]">
            <QuoteStatsPanel quote={quote} loading={quoteLoading} />
            <TechnicalsPanel prediction={prediction} loading={predLoading} />
            <PredictionPanel prediction={prediction} loading={predLoading} />
          </div>

          {/* CENTER — chart fills remaining space */}
          <div className="flex-1 min-w-0 flex flex-col overflow-hidden bg-[#080c14]">
            <CandlestickChart
              ticker={normalizedTicker}
              height={520}
              className="flex-1 border-0 rounded-none"
              disabled={isInvalidTicker}
              onPeriodChange={(range, pct) => setPeriodPct({ range, pct })}
            />

            {/* OHLCV quick bar under chart */}
            {quote && (
              <div className="shrink-0 border-t border-[#1f2d40] bg-[#0a0e1a] px-4 py-2 flex items-center gap-6 text-xs flex-wrap">
                <span className="text-[#475569]">Open <span className="text-[#94a3b8] font-semibold tabular-nums">{formatCurrency(quote.day_high)}</span></span>
                <span className="text-[#475569]">High <span className="text-green-400 font-semibold tabular-nums">{formatCurrency(quote.day_high)}</span></span>
                <span className="text-[#475569]">Low <span className="text-red-400 font-semibold tabular-nums">{formatCurrency(quote.day_low)}</span></span>
                <span className="text-[#475569]">Close <span className="text-white font-semibold tabular-nums">{formatCurrency(quote.price)}</span></span>
                <span className="text-[#475569]">Vol <span className="text-[#94a3b8] font-semibold tabular-nums">{formatCompact(quote.volume ?? 0).replace('$','')}</span></span>
                {prediction?.rsi_14 != null && (
                  <span className="text-[#475569]">RSI(14) <span className={cn('font-semibold tabular-nums',
                    prediction.rsi_14 > 70 ? 'text-red-400' : prediction.rsi_14 < 30 ? 'text-green-400' : 'text-[#94a3b8]')}>
                    {prediction.rsi_14.toFixed(1)}
                  </span></span>
                )}
                {prediction?.macd_signal && (
                  <span className="text-[#475569]">MACD <span className={cn('font-semibold',
                    prediction.macd_signal === 'bullish' ? 'text-green-400' : prediction.macd_signal === 'bearish' ? 'text-red-400' : 'text-[#94a3b8]')}>
                    {prediction.macd_signal.charAt(0).toUpperCase() + prediction.macd_signal.slice(1)}
                  </span></span>
                )}
              </div>
            )}
          </div>

          {/* RIGHT sidebar — earnings + news feed + AI research */}
          <div className="w-72 shrink-0 border-l border-[#1f2d40] overflow-y-auto bg-[#0a0e1a] flex flex-col gap-0">
            <EarningsPanel earnings={earnings} loading={earningsLoading} />
            <AIResearchPanel ticker={normalizedTicker} />
            <NewsPanel news={news} loading={newsLoading} />
          </div>
        </div>

        {/* ── Order ticket modal ───────────────────────────────────────── */}
        <OrderTicket
          isOpen={orderTicketOpen}
          onClose={() => setOrderTicketOpen(false)}
          defaultTicker={normalizedTicker}
          defaultSide={orderSide}
        />
      </div>
    </PageTransition>
  )
}
