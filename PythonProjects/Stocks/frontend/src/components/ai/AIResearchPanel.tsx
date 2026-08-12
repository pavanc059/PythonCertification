/**
 * AIResearchPanel — terminal sidebar panel for StockDetailPage.
 *
 * Shows:
 * - Insider transaction summary (buys vs sells, net signal)
 * - Guru / institutional presence
 * - Ask AI button → streams GPT-4o analysis inline
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Brain, TrendingUp, TrendingDown, Minus, Loader2, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getInsiders, getGurus, streamAnalysis, streamBuyersAnalysis } from '@/api/ai'
import type { InsiderTransaction } from '@/api/ai'

// ─── Markdown renderer (simple — bold + newlines only) ───────────────────────
function SimpleMarkdown({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <div className="space-y-0.5">
      {lines.map((line, i) => {
        // Headers: ## or ###
        if (line.startsWith('### ')) {
          return <p key={i} className="text-[11px] font-bold text-[#6366f1] mt-2 mb-0.5">{line.slice(4)}</p>
        }
        if (line.startsWith('## ')) {
          return <p key={i} className="text-xs font-bold text-[#f1f5f9] mt-2 mb-0.5">{line.slice(3)}</p>
        }
        if (line.startsWith('**') && line.endsWith('**')) {
          return <p key={i} className="text-[11px] font-bold text-[#e2e8f0]">{line.slice(2, -2)}</p>
        }
        // Bullet points
        if (line.startsWith('- ') || line.startsWith('• ')) {
          const content = line.slice(2)
          // Inline bold: **word**
          const parts = content.split(/(\*\*[^*]+\*\*)/)
          return (
            <p key={i} className="text-[11px] text-[#94a3b8] pl-2 before:content-['•'] before:mr-1.5 before:text-[#475569]">
              {parts.map((p, j) =>
                p.startsWith('**') ? (
                  <span key={j} className="font-semibold text-[#f1f5f9]">{p.slice(2, -2)}</span>
                ) : p
              )}
            </p>
          )
        }
        // Numbered list
        const numMatch = line.match(/^(\d+)\.\s+(.+)/)
        if (numMatch) {
          const parts = numMatch[2].split(/(\*\*[^*]+\*\*)/)
          return (
            <p key={i} className="text-[11px] text-[#94a3b8] pl-2">
              <span className="text-[#6366f1] font-bold mr-1">{numMatch[1]}.</span>
              {parts.map((p, j) =>
                p.startsWith('**') ? (
                  <span key={j} className="font-semibold text-[#f1f5f9]">{p.slice(2, -2)}</span>
                ) : p
              )}
            </p>
          )
        }
        if (!line.trim()) return <div key={i} className="h-1" />
        // Plain text with inline bold
        const parts = line.split(/(\*\*[^*]+\*\*)/)
        return (
          <p key={i} className="text-[11px] text-[#94a3b8] leading-relaxed">
            {parts.map((p, j) =>
              p.startsWith('**') ? (
                <span key={j} className="font-semibold text-[#f1f5f9]">{p.slice(2, -2)}</span>
              ) : p
            )}
          </p>
        )
      })}
    </div>
  )
}

// ─── Panel header ─────────────────────────────────────────────────────────────
function PanelHeader({ label, icon }: { label: string; icon?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b border-[#1f2d40]">
      {icon}
      <span className="text-[10px] font-bold text-[#475569] uppercase tracking-widest">{label}</span>
    </div>
  )
}

// ─── Signal badge ─────────────────────────────────────────────────────────────
function SignalBadge({ signal }: { signal: 'bullish' | 'bearish' | 'neutral' | undefined }) {
  if (!signal) return null
  const cfg = {
    bullish: { cls: 'bg-green-500/15 text-green-400 border-green-500/30', Icon: TrendingUp, label: 'Net Buying' },
    bearish: { cls: 'bg-red-500/15 text-red-400 border-red-500/30', Icon: TrendingDown, label: 'Net Selling' },
    neutral: { cls: 'bg-[#475569]/15 text-[#94a3b8] border-[#475569]/30', Icon: Minus, label: 'Neutral' },
  }[signal]
  return (
    <span className={cn('inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-bold', cfg.cls)}>
      <cfg.Icon className="h-2.5 w-2.5" />
      {cfg.label}
    </span>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────
interface AIResearchPanelProps {
  ticker: string
}

export function AIResearchPanel({ ticker }: AIResearchPanelProps) {
  const [question, setQuestion] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamedText, setStreamedText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [showAnalysis, setShowAnalysis] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: insiders, isLoading: insidersLoading } = useQuery({
    queryKey: ['ai', 'insiders', ticker],
    queryFn: () => getInsiders(ticker),
    staleTime: 300_000,
    retry: false,
  })

  const { data: gurus, isLoading: gurusLoading } = useQuery({
    queryKey: ['ai', 'gurus', ticker],
    queryFn: () => getGurus(ticker),
    staleTime: 3_600_000,
    retry: false,
  })

  // Auto-scroll to bottom during streaming
  useEffect(() => {
    if (streaming) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamedText, streaming])

  const handleAsk = useCallback(() => {
    if (streaming) {
      abortRef.current?.abort()
      setStreaming(false)
      return
    }
    setStreamedText('')
    setError(null)
    setShowAnalysis(true)
    setStreaming(true)

    const q = question.trim() || 'Who are the biggest buyers? What are insiders and institutions doing?'
    abortRef.current = streamAnalysis(
      ticker, q,
      (chunk) => setStreamedText((prev) => prev + chunk),
      () => setStreaming(false),
      (err) => { setError(err); setStreaming(false) },
    )
  }, [ticker, question, streaming])

  return (    <div className="rounded border border-[#1f2d40] bg-[#0d1424] overflow-hidden flex flex-col">
      <PanelHeader label="AI Research" icon={<Brain className="h-3 w-3 text-[#6366f1]" />} />

      {/* ── Insider summary ── */}
      <div className="border-b border-[#1a2235]">
        <div className="px-3 py-2 flex items-center justify-between">
          <span className="text-[10px] font-bold text-[#475569] uppercase tracking-widest">Insider Transactions</span>
          <SignalBadge signal={insiders?.summary.signal} />
        </div>

        {insidersLoading ? (
          <div className="px-3 pb-2 space-y-1">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-4 animate-pulse rounded bg-[#1a2235]" />
            ))}
          </div>
        ) : insiders && insiders.transactions.length > 0 ? (
          <div className="px-3 pb-2 space-y-1">
            <div className="flex gap-4 text-[10px] mb-1.5">
              <span className="text-green-400 font-bold">{insiders.summary.total_buys} Buys</span>
              <span className="text-red-400 font-bold">{insiders.summary.total_sells} Sells</span>
              <span className="text-[#475569]">
                Net: <span className={insiders.summary.net_shares >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {insiders.summary.net_shares >= 0 ? '+' : ''}{insiders.summary.net_shares.toLocaleString()} sh
                </span>
              </span>
            </div>
            {insiders.transactions.slice(0, 5).map((t: InsiderTransaction, i: number) => (
              <div key={i} className="flex items-center justify-between text-[10px]">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className={cn('shrink-0 font-bold', t.action === 'BUY' ? 'text-green-400' : 'text-red-400')}>
                    {t.action}
                  </span>
                  <span className="text-[#475569] truncate">{t.name.split(' ').slice(0, 2).join(' ')}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[#94a3b8] tabular-nums">{t.shares.toLocaleString()}</span>
                  <span className="text-[#475569] text-[9px]">{t.date}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="px-3 pb-2 text-[10px] text-[#475569]">No insider transactions in last 90 days.</p>
        )}
      </div>

      {/* ── Institutional / gurus ── */}
      <div className="border-b border-[#1a2235]">
        <div className="px-3 py-2">
          <span className="text-[10px] font-bold text-[#475569] uppercase tracking-widest">Top Holders</span>
        </div>
        {gurusLoading ? (
          <div className="px-3 pb-2 space-y-1">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-4 animate-pulse rounded bg-[#1a2235]" />
            ))}
          </div>
        ) : (
          <div className="px-3 pb-2 space-y-1">
            {(gurus?.institutional_holders ?? []).slice(0, 3).map((h, i) => (
              <div key={i} className="flex items-center justify-between text-[10px]">
                <span className="text-[#94a3b8] truncate flex-1 mr-2">{h.holder}</span>
                <span className="text-[#6366f1] font-bold shrink-0">{h.pct.toFixed(1)}%</span>
              </div>
            ))}
            {gurus?.guru_13f && gurus.guru_13f.length > 0 && (
              <div className="mt-1.5 pt-1.5 border-t border-[#1a2235]">
                <p className="text-[9px] text-[#475569] uppercase tracking-widest mb-1">Guru 13F Presence</p>
                {gurus.guru_13f.slice(0, 2).map((g, i) => (
                  <p key={i} className="text-[10px] text-green-400 truncate">✓ {g.guru}</p>
                ))}
              </div>
            )}
            {(gurus?.institutional_holders ?? []).length === 0 && (
              <p className="text-[10px] text-[#475569]">No holder data available.</p>
            )}
          </div>
        )}
      </div>

      {/* ── Ask AI ── */}
      <div className="p-3 space-y-2">
        <p className="text-[10px] font-bold text-[#475569] uppercase tracking-widest">Ask AI (RAG + Web Search)</p>
        <div className="flex gap-1.5">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            placeholder="e.g. Who is buying? What's the outlook?"
            className="flex-1 min-w-0 rounded bg-[#111827] border border-[#1f2d40] px-2 py-1 text-[11px] text-[#f1f5f9] placeholder-[#475569] focus:outline-none focus:border-[#6366f1]/50"
          />
          <button
            type="button"
            onClick={handleAsk}
            className={cn(
              'shrink-0 flex items-center gap-1 px-2 py-1 rounded text-[11px] font-bold transition-colors',
              streaming
                ? 'bg-red-600/20 text-red-400 border border-red-600/30 hover:bg-red-600/30'
                : 'bg-[#6366f1]/20 text-[#6366f1] border border-[#6366f1]/30 hover:bg-[#6366f1]/30'
            )}
          >
            {streaming ? (
              <><Loader2 className="h-3 w-3 animate-spin" />Stop</>
            ) : (
              <><Brain className="h-3 w-3" />Ask</>
            )}
          </button>
        </div>

        {/* Quick question chips */}
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => {
              setQuestion('Who are the top individual buyers right now?')
              setStreamedText('')
              setError(null)
              setShowAnalysis(true)
              setStreaming(true)
              abortRef.current = streamBuyersAnalysis(
                ticker,
                (chunk) => setStreamedText((prev) => prev + chunk),
                () => setStreaming(false),
                (err) => { setError(err); setStreaming(false) },
              )
            }}
            className="w-full rounded bg-[#6366f1]/10 border border-[#6366f1]/30 px-2 py-1 text-[10px] font-bold text-[#6366f1] hover:bg-[#6366f1]/20 transition-colors flex items-center justify-center gap-1"
          >
            🔍 Who's Buying? (News + Filings + Web Search)
          </button>
          {[
            'Who is buying?',
            'Insider sentiment?',
            'Institutional outlook?',
            'Key risks?',
          ].map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => { setQuestion(q); }}
              className="rounded bg-[#111827] border border-[#1f2d40] px-2 py-0.5 text-[10px] text-[#475569] hover:text-[#94a3b8] hover:border-[#2d3f58] transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* ── Streaming response ── */}
      {showAnalysis && (
        <div className="border-t border-[#1f2d40] px-3 py-2 max-h-96 overflow-y-auto">
          {error && (
            <div className="flex items-center gap-2 text-[11px] text-red-400">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {error}
            </div>
          )}
          {streamedText && <SimpleMarkdown text={streamedText} />}
          {streaming && (
            <span className="inline-block h-3 w-0.5 bg-[#6366f1] animate-pulse ml-0.5 align-middle" />
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
