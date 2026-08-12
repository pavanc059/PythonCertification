/**
 * AIResearchPage — full-page AI stock research assistant.
 * Accessible at /ai-research
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Brain, Search, Loader2,
  ExternalLink, ChevronRight, AlertCircle, Sparkles,
} from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import { getInsiders, getGurus, streamAnalysis, streamBuyersAnalysis } from '@/api/ai'
import { cn } from '@/lib/utils'

const TICKER_RE = /^[A-Z0-9]{1,10}$/

// ─── Simple markdown renderer ─────────────────────────────────────────────────
function Md({ text }: { text: string }) {
  return (
    <div className="space-y-1 leading-relaxed">
      {text.split('\n').map((line, i) => {
        if (line.startsWith('## '))
          return <p key={i} className="text-sm font-bold text-[#f1f5f9] mt-4 mb-1 border-b border-[#1f2d40] pb-1">{line.slice(3)}</p>
        if (line.startsWith('### '))
          return <p key={i} className="text-sm font-semibold text-[#6366f1] mt-3 mb-0.5">{line.slice(4)}</p>
        if (line.startsWith('- ') || line.startsWith('• ')) {
          const parts = line.slice(2).split(/(\*\*[^*]+\*\*)/)
          return (
            <p key={i} className="text-sm text-[#94a3b8] pl-4 flex gap-2">
              <span className="text-[#475569] shrink-0">•</span>
              <span>{parts.map((p, j) => p.startsWith('**')
                ? <span key={j} className="font-semibold text-[#f1f5f9]">{p.slice(2,-2)}</span>
                : p)}</span>
            </p>
          )
        }
        const numMatch = line.match(/^(\d+)\.\s+(.+)/)
        if (numMatch) {
          const parts = numMatch[2].split(/(\*\*[^*]+\*\*)/)
          return (
            <p key={i} className="text-sm text-[#94a3b8] pl-4 flex gap-2">
              <span className="text-[#6366f1] font-bold shrink-0">{numMatch[1]}.</span>
              <span>{parts.map((p, j) => p.startsWith('**')
                ? <span key={j} className="font-semibold text-[#f1f5f9]">{p.slice(2,-2)}</span>
                : p)}</span>
            </p>
          )
        }
        if (!line.trim()) return <div key={i} className="h-2" />
        const parts = line.split(/(\*\*[^*]+\*\*)/)
        return (
          <p key={i} className="text-sm text-[#94a3b8]">
            {parts.map((p, j) => p.startsWith('**')
              ? <span key={j} className="font-semibold text-[#f1f5f9]">{p.slice(2,-2)}</span>
              : p)}
          </p>
        )
      })}
    </div>
  )
}

export default function AIResearchPage() {
  const navigate = useNavigate()
  const [ticker, setTicker] = useState('')
  const [submittedTicker, setSubmittedTicker] = useState('')
  const [question, setQuestion] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamedText, setStreamedText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [tickerError, setTickerError] = useState('')
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (streaming) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamedText, streaming])

  const { data: insiders, isLoading: insidersLoading } = useQuery({
    queryKey: ['ai', 'insiders', submittedTicker],
    queryFn: () => getInsiders(submittedTicker),
    enabled: !!submittedTicker,
    staleTime: 300_000,
    retry: false,
  })

  const { data: gurus, isLoading: gurusLoading } = useQuery({
    queryKey: ['ai', 'gurus', submittedTicker],
    queryFn: () => getGurus(submittedTicker),
    enabled: !!submittedTicker,
    staleTime: 3_600_000,
    retry: false,
  })

  const handleTickerSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const t = ticker.trim().toUpperCase()
    if (!TICKER_RE.test(t)) { setTickerError('Enter a valid ticker (1–10 chars)'); return }
    setTickerError('')
    setSubmittedTicker(t)
    setStreamedText('')
    setError(null)
  }

  const handleAnalyze = useCallback(() => {
    if (!submittedTicker) return
    if (streaming) { abortRef.current?.abort(); setStreaming(false); return }
    setStreamedText('')
    setError(null)
    setStreaming(true)
    const q = question.trim() || 'Who are the biggest buyers? What are insiders and institutions doing?'
    abortRef.current = streamAnalysis(
      submittedTicker, q,
      (chunk) => setStreamedText((p) => p + chunk),
      () => setStreaming(false),
      (err) => { setError(err); setStreaming(false) },
    )
  }, [submittedTicker, question, streaming])

  const QUICK_QUESTIONS = [
    'Who are the biggest individual buyers right now?',
    'What are hedge funds and institutions doing with this stock?',
    'Are insiders buying or selling? What does it signal?',
    'What is the current news sentiment and what risks should I know?',
    'Summarise the bull vs bear case based on current data.',
  ]

  // Handler for the dedicated "Who's Buying?" deep search
  const handleWhosBuying = useCallback(() => {
    if (!submittedTicker) return
    if (streaming) { abortRef.current?.abort(); setStreaming(false); return }
    setStreamedText('')
    setError(null)
    setStreaming(true)
    setQuestion("Who are the top individual buyers right now? (deep search)")
    abortRef.current = streamBuyersAnalysis(
      submittedTicker,
      (chunk) => setStreamedText((p) => p + chunk),
      () => setStreaming(false),
      (err) => { setError(err); setStreaming(false) },
    )
  }, [submittedTicker, streaming])

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl space-y-6">

          {/* Header */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#6366f1]/20">
              <Brain className="h-5 w-5 text-[#6366f1]" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#f1f5f9]">AI Stock Research</h1>
              <p className="text-xs text-[#475569]">
                RAG pipeline · Insider filings · Institutional 13F · Tavily web search · GPT-4o
              </p>
            </div>
          </div>

          {/* Ticker input */}
          <form onSubmit={handleTickerSubmit} className="flex gap-2">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#475569] pointer-events-none" />
              <input
                type="text"
                value={ticker}
                onChange={(e) => {
                  setTicker(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10))
                  setTickerError('')
                }}
                placeholder="Ticker (e.g. AAPL)"
                className={cn(
                  'w-full pl-9 pr-3 py-2.5 rounded-xl text-sm bg-[#111827] text-[#f1f5f9] placeholder-[#475569]',
                  'border focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50 transition-colors',
                  tickerError ? 'border-red-500/50' : 'border-[#1f2d40]',
                )}
              />
            </div>
            <button type="submit"
              className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-[#111827] border border-[#1f2d40] text-[#94a3b8] hover:text-[#f1f5f9] hover:border-[#6366f1]/50 transition-colors">
              Load Data
            </button>
            {submittedTicker && (
              <button type="button" onClick={() => navigate(`/stock/${submittedTicker}`)}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold border border-[#6366f1]/30 text-[#6366f1] hover:bg-[#6366f1]/10 transition-colors">
                Chart <ChevronRight className="h-4 w-4" />
              </button>
            )}
          </form>
          {tickerError && <p className="-mt-4 text-xs text-red-400">{tickerError}</p>}

          {submittedTicker && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

              {/* ── Left column: structured data ── */}
              <div className="lg:col-span-1 space-y-4">

                {/* Insider transactions */}
                <div className="rounded-xl border border-[#1f2d40] bg-[#111827] overflow-hidden">
                  <div className="px-4 py-3 border-b border-[#1f2d40] flex items-center justify-between">
                    <span className="text-sm font-semibold text-[#f1f5f9]">Insider Transactions</span>
                    {insiders?.summary && (
                      <span className={cn('text-xs font-bold px-2 py-0.5 rounded',
                        insiders.summary.signal === 'bullish' ? 'bg-green-500/15 text-green-400' :
                        insiders.summary.signal === 'bearish' ? 'bg-red-500/15 text-red-400' :
                        'bg-[#475569]/15 text-[#94a3b8]')}>
                        {insiders.summary.signal.toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div className="p-4">
                    {insidersLoading ? (
                      <div className="space-y-2">{[...Array(4)].map((_, i) => <div key={i} className="h-8 animate-pulse rounded bg-[#1a2235]" />)}</div>
                    ) : insiders && insiders.transactions.length > 0 ? (
                      <>
                        <div className="flex gap-4 mb-3 text-xs">
                          <span className="text-green-400 font-bold">↑ {insiders.summary.total_buys} buys</span>
                          <span className="text-red-400 font-bold">↓ {insiders.summary.total_sells} sells</span>
                          <span className="text-[#475569]">Net: <span className={insiders.summary.net_shares >= 0 ? 'text-green-400' : 'text-red-400'}>
                            {insiders.summary.net_shares >= 0 ? '+' : ''}{insiders.summary.net_shares.toLocaleString()} sh
                          </span></span>
                        </div>
                        <div className="space-y-1.5">
                          {insiders.transactions.slice(0, 8).map((t, i) => (
                            <div key={i} className="flex items-center justify-between text-xs">
                              <div className="flex items-center gap-2 min-w-0">
                                <span className={cn('shrink-0 font-bold w-8', t.action === 'BUY' ? 'text-green-400' : 'text-red-400')}>
                                  {t.action === 'BUY' ? '▲' : '▼'} {t.action}
                                </span>
                                <span className="text-[#94a3b8] truncate">{t.name}</span>
                              </div>
                              <div className="shrink-0 text-right ml-2">
                                <p className="text-[#f1f5f9] tabular-nums">{t.shares.toLocaleString()} sh</p>
                                <p className="text-[#475569] text-[10px]">{t.date}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : (
                      <p className="text-sm text-[#475569]">No insider transactions found in the last 6 months.</p>
                    )}
                  </div>
                </div>

                {/* Institutional / gurus */}
                <div className="rounded-xl border border-[#1f2d40] bg-[#111827] overflow-hidden">
                  <div className="px-4 py-3 border-b border-[#1f2d40]">
                    <span className="text-sm font-semibold text-[#f1f5f9]">Institutional Holdings</span>
                  </div>
                  <div className="p-4 space-y-3">
                    {gurusLoading ? (
                      <div className="space-y-2">{[...Array(4)].map((_, i) => <div key={i} className="h-6 animate-pulse rounded bg-[#1a2235]" />)}</div>
                    ) : (
                      <>
                        {(gurus?.institutional_holders ?? []).slice(0, 5).map((h, i) => (
                          <div key={i} className="flex items-center justify-between text-xs">
                            <span className="text-[#94a3b8] truncate flex-1 mr-2">{h.holder}</span>
                            <div className="shrink-0 text-right">
                              <span className="text-[#6366f1] font-bold">{h.pct.toFixed(2)}%</span>
                            </div>
                          </div>
                        ))}
                        {(gurus?.guru_13f ?? []).length > 0 && (
                          <div className="pt-2 border-t border-[#1a2235]">
                            <p className="text-xs font-semibold text-[#475569] uppercase tracking-wide mb-1.5">Guru 13F Presence</p>
                            {gurus!.guru_13f.map((g, i) => (
                              <div key={i} className="flex items-center justify-between text-xs mb-1">
                                <span className="text-green-400 truncate">{g.guru}</span>
                                <a href={g.filing_url} target="_blank" rel="noopener noreferrer"
                                  className="text-[#475569] hover:text-[#6366f1] transition-colors shrink-0 ml-1">
                                  <ExternalLink className="h-3 w-3" />
                                </a>
                              </div>
                            ))}
                          </div>
                        )}
                        {(gurus?.institutional_holders ?? []).length === 0 && (gurus?.guru_13f ?? []).length === 0 && (
                          <p className="text-sm text-[#475569]">No holder data available.</p>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* ── Right column: AI chat ── */}
              <div className="lg:col-span-2 space-y-4">

                <div className="rounded-xl border border-[#6366f1]/30 bg-[#111827] overflow-hidden">
                  <div className="px-4 py-3 border-b border-[#1f2d40] flex items-center gap-2 bg-[#6366f1]/5">
                    <Sparkles className="h-4 w-4 text-[#6366f1]" />
                    <span className="text-sm font-semibold text-[#f1f5f9]">AI Analysis — {submittedTicker}</span>
                    <span className="ml-auto text-[10px] text-[#475569]">GPT-4o · Tavily · Finnhub · SEC 13F</span>
                  </div>

                  {/* Who's Buying — dedicated deep search */}
                  {submittedTicker && (
                    <div className="px-4 py-2 border-b border-[#1f2d40] bg-[#6366f1]/5">
                      <button
                        type="button"
                        onClick={handleWhosBuying}
                        disabled={streaming}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-bold bg-[#6366f1] hover:bg-[#818cf8] text-white transition-colors disabled:opacity-50"
                      >
                        {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : '🔍'}
                        Who's Buying {submittedTicker} Right Now?
                        <span className="text-xs font-normal opacity-75 ml-1">6 web searches + filings</span>
                      </button>
                    </div>
                  )}

                  {/* Question input */}
                  <div className="p-4 border-b border-[#1f2d40] space-y-3">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                        placeholder="Ask about insiders, institutions, news sentiment..."
                        className="flex-1 px-3 py-2 rounded-lg text-sm bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] placeholder-[#475569] focus:outline-none focus:border-[#6366f1]/50 transition-colors"
                      />
                      <button type="button" onClick={handleAnalyze}
                        className={cn(
                          'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors',
                          streaming
                            ? 'bg-red-600 hover:bg-red-500 text-white'
                            : 'bg-[#6366f1] hover:bg-[#818cf8] text-white'
                        )}>
                        {streaming ? (
                          <><Loader2 className="h-4 w-4 animate-spin" />Stop</>
                        ) : (
                          <><Brain className="h-4 w-4" />Analyze</>
                        )}
                      </button>
                    </div>

                    {/* Quick questions */}
                    <div className="flex flex-wrap gap-1.5">
                      {QUICK_QUESTIONS.map((q) => (
                        <button key={q} type="button"
                          onClick={() => { setQuestion(q) }}
                          className="rounded-full border border-[#1f2d40] bg-[#0a0e1a] px-2.5 py-1 text-[11px] text-[#475569] hover:text-[#94a3b8] hover:border-[#6366f1]/40 transition-colors">
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Response area */}
                  <div className="p-4 min-h-48 max-h-[600px] overflow-y-auto">
                    {!streamedText && !streaming && !error && (
                      <div className="flex flex-col items-center justify-center h-40 text-center gap-3">
                        <Brain className="h-10 w-10 text-[#1f2d40]" />
                        <p className="text-sm text-[#475569]">
                          Ask a question above to get an AI-powered analysis of {submittedTicker} using live data from insider filings, institutional holdings, news sentiment, and web search.
                        </p>
                      </div>
                    )}
                    {error && (
                      <div className="flex items-center gap-2 text-sm text-red-400 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        {error}
                      </div>
                    )}
                    {streamedText && <Md text={streamedText} />}
                    {streaming && (
                      <span className="inline-block h-4 w-0.5 bg-[#6366f1] animate-pulse ml-0.5 align-middle mt-1" />
                    )}
                    <div ref={bottomRef} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!submittedTicker && (
            <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-10 flex flex-col items-center gap-4 text-center">
              <Brain className="h-12 w-12 text-[#1f2d40]" />
              <div>
                <p className="text-base font-semibold text-[#94a3b8]">Enter a ticker to start researching</p>
                <p className="text-sm text-[#475569] mt-1">
                  The AI will pull insider Form 4 filings, institutional 13F holdings, news sentiment, and live web search results — then synthesise everything into a clear analysis.
                </p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center">
                {['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN'].map((t) => (
                  <button key={t} type="button"
                    onClick={() => { setTicker(t); setSubmittedTicker(t) }}
                    className="rounded-full border border-[#1f2d40] bg-[#0a0e1a] px-3 py-1.5 text-sm font-bold text-[#6366f1] hover:border-[#6366f1]/50 transition-colors">
                    {t}
                  </button>
                ))}
              </div>
            </div>
          )}

        </div>
      </main>
    </PageTransition>
  )
}
