import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  FlaskConical, Play, Loader2,
  AlertTriangle, Info, ArrowUpRight, ArrowDownRight,
} from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import {
  getStrategies, runBacktest, DEFAULT_RISK,
  type RiskParams, type BacktestResult, type StrategyInfo,
} from '@/api/autotrade'
import { cn } from '@/lib/utils'
import { formatCurrency } from '@/lib/formatters'

const PERIODS = [
  { value: '3mo', label: '3 Months' },
  { value: '6mo', label: '6 Months' },
  { value: '1y', label: '1 Year' },
  { value: '2y', label: '2 Years' },
  { value: '5y', label: '5 Years' },
]

// ─── Metric card ──────────────────────────────────────────────────────────────
function Metric({ label, value, sub, tone }: {
  label: string; value: string; sub?: string
  tone?: 'pos' | 'neg' | 'neutral'
}) {
  const color = tone === 'pos' ? 'text-green-400' : tone === 'neg' ? 'text-red-400' : 'text-[#f1f5f9]'
  return (
    <div className="rounded-xl border border-[#1f2d40] bg-[#111827] px-4 py-3">
      <p className="text-[10px] font-medium text-[#475569] uppercase tracking-wide">{label}</p>
      <p className={cn('text-lg font-bold tabular-nums mt-0.5', color)}>{value}</p>
      {sub && <p className="text-[10px] text-[#475569] mt-0.5">{sub}</p>}
    </div>
  )
}

// ─── Equity curve (inline SVG sparkline-style) ─────────────────────────────────
function EquityCurve({ data, initial }: { data: { date: string; equity: number }[]; initial: number }) {
  if (data.length < 2) return null
  const w = 800, h = 200, pad = 4
  const equities = data.map((d) => d.equity)
  const min = Math.min(...equities, initial)
  const max = Math.max(...equities, initial)
  const range = max - min || 1
  const pts = data.map((d, i) => {
    const x = pad + (i / (data.length - 1)) * (w - 2 * pad)
    const y = h - pad - ((d.equity - min) / range) * (h - 2 * pad)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  // Baseline (initial capital)
  const baseY = h - pad - ((initial - min) / range) * (h - 2 * pad)
  const finalEquity = equities[equities.length - 1]
  const up = finalEquity >= initial
  const stroke = up ? '#00C851' : '#FF4444'

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-48" preserveAspectRatio="none">
      <line x1={pad} y1={baseY} x2={w - pad} y2={baseY}
        stroke="#475569" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
      <polyline points={pts} fill="none" stroke={stroke} strokeWidth="2"
        strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

export default function BacktestPage() {
  const [ticker, setTicker] = useState('AAPL')
  const [strategy, setStrategy] = useState('momentum')
  const [period, setPeriod] = useState('1y')
  const [initialCapital, setInitialCapital] = useState(100000)
  const [risk, setRisk] = useState<RiskParams>(DEFAULT_RISK)
  const [result, setResult] = useState<BacktestResult | null>(null)

  const { data: strategies } = useQuery({
    queryKey: ['autotrade', 'strategies'],
    queryFn: getStrategies,
    staleTime: Infinity,
  })

  const mutation = useMutation({
    mutationFn: runBacktest,
    onSuccess: (data) => setResult(data),
  })

  const handleRun = () => {
    const t = ticker.trim().toUpperCase()
    if (!/^[A-Z0-9]{1,10}$/.test(t)) return
    mutation.mutate({
      ticker: t, strategy, period, interval: '1d',
      initial_capital: initialCapital, risk,
    })
  }

  const errMsg = mutation.isError
    ? ((mutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
       ?? 'Backtest failed. Try a different ticker or period.')
    : null

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl space-y-6">

          {/* Header */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#6366f1]/20">
              <FlaskConical className="h-5 w-5 text-[#6366f1]" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#f1f5f9]">Strategy Backtester</h1>
              <p className="text-xs text-[#475569]">
                Test a strategy on historical data before risking anything. Paper only.
              </p>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="flex items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <p className="text-xs text-amber-200/80">
              Past performance does not predict future results. Backtests are optimistic —
              real trading involves slippage, gaps, and emotional decisions. Use this to
              compare strategies, not to project profits.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* ── Config panel ── */}
            <div className="lg:col-span-1 space-y-4">
              <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-4 space-y-4">
                <h2 className="text-sm font-semibold text-[#f1f5f9]">Configuration</h2>

                {/* Ticker */}
                <div>
                  <label className="text-xs text-[#475569] block mb-1">Ticker</label>
                  <input
                    type="text" value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10))}
                    className="w-full px-3 py-2 rounded-lg text-sm bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] focus:outline-none focus:border-[#6366f1]/50"
                  />
                </div>

                {/* Strategy */}
                <div>
                  <label className="text-xs text-[#475569] block mb-1">Strategy</label>
                  <select
                    value={strategy} onChange={(e) => setStrategy(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg text-sm bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] focus:outline-none focus:border-[#6366f1]/50"
                  >
                    {(strategies ?? []).map((s: StrategyInfo) => (
                      <option key={s.name} value={s.name}>{s.display_name}</option>
                    ))}
                  </select>
                </div>

                {/* Period */}
                <div>
                  <label className="text-xs text-[#475569] block mb-1">Period</label>
                  <select
                    value={period} onChange={(e) => setPeriod(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg text-sm bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] focus:outline-none focus:border-[#6366f1]/50"
                  >
                    {PERIODS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
                  </select>
                </div>

                {/* Initial capital */}
                <div>
                  <label className="text-xs text-[#475569] block mb-1">Initial Capital</label>
                  <input
                    type="number" value={initialCapital}
                    onChange={(e) => setInitialCapital(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg text-sm bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] focus:outline-none focus:border-[#6366f1]/50"
                  />
                </div>
              </div>

              {/* Risk params */}
              <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-4 space-y-3">
                <h2 className="text-sm font-semibold text-[#f1f5f9] flex items-center gap-1.5">
                  Risk Management
                  <span title="These controls limit losses — the most important part of any system.">
                    <Info className="h-3 w-3 text-[#475569]" />
                  </span>
                </h2>

                {[
                  { key: 'position_size_pct', label: 'Position Size', pct: true, min: 1, max: 100, step: 1 },
                  { key: 'stop_loss_pct', label: 'Stop Loss', pct: true, min: 0.5, max: 20, step: 0.5 },
                  { key: 'take_profit_pct', label: 'Take Profit', pct: true, min: 0.5, max: 50, step: 0.5 },
                  { key: 'daily_loss_limit_pct', label: 'Daily Loss Limit', pct: true, min: 1, max: 50, step: 1 },
                  { key: 'min_confidence', label: 'Min Confidence', pct: false, min: 0, max: 100, step: 5 },
                ].map(({ key, label, pct, min, max, step }) => {
                  const raw = risk[key as keyof RiskParams] as number
                  const display = pct ? Math.round(raw * 100) : raw
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#475569]">{label}</span>
                        <span className="text-[#94a3b8] font-semibold">{display}{pct || key === 'min_confidence' ? '%' : ''}</span>
                      </div>
                      <input
                        type="range" min={min} max={max} step={step}
                        value={display}
                        onChange={(e) => {
                          const v = Number(e.target.value)
                          setRisk((prev) => ({ ...prev, [key]: pct ? v / 100 : v }))
                        }}
                        className="w-full accent-[#6366f1]"
                      />
                    </div>
                  )
                })}
              </div>

              {/* Run button */}
              <button
                type="button" onClick={handleRun} disabled={mutation.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-bold bg-[#6366f1] hover:bg-[#818cf8] text-white transition-colors disabled:opacity-60"
              >
                {mutation.isPending
                  ? <><Loader2 className="h-4 w-4 animate-spin" />Running…</>
                  : <><Play className="h-4 w-4" />Run Backtest</>}
              </button>
            </div>

            {/* ── Results ── */}
            <div className="lg:col-span-2 space-y-4">
              {errMsg && (
                <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
                  <p className="text-sm text-red-400">{errMsg}</p>
                </div>
              )}

              {!result && !mutation.isPending && !errMsg && (
                <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-12 flex flex-col items-center gap-3 text-center">
                  <FlaskConical className="h-12 w-12 text-[#1f2d40]" />
                  <p className="text-sm text-[#475569]">
                    Configure a strategy and run a backtest to see performance metrics,
                    an equity curve, and the full trade log.
                  </p>
                </div>
              )}

              {result && (
                <>
                  {/* Metrics grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <Metric label="Total Return" tone={result.total_return_pct >= 0 ? 'pos' : 'neg'}
                      value={`${result.total_return_pct >= 0 ? '+' : ''}${result.total_return_pct.toFixed(2)}%`}
                      sub={formatCurrency(result.total_return)} />
                    <Metric label="Final Equity" value={formatCurrency(result.final_equity)}
                      sub={`from ${formatCurrency(result.initial_capital)}`} />
                    <Metric label="Win Rate"
                      tone={result.win_rate >= 50 ? 'pos' : 'neg'}
                      value={`${result.win_rate.toFixed(1)}%`}
                      sub={`${result.num_winning}W / ${result.num_losing}L`} />
                    <Metric label="Total Trades" value={String(result.num_trades)} />
                    <Metric label="Max Drawdown" tone="neg"
                      value={`-${result.max_drawdown_pct.toFixed(2)}%`} />
                    <Metric label="Sharpe Ratio"
                      tone={result.sharpe_ratio >= 1 ? 'pos' : result.sharpe_ratio < 0 ? 'neg' : 'neutral'}
                      value={result.sharpe_ratio.toFixed(2)} />
                    <Metric label="Profit Factor"
                      tone={result.profit_factor >= 1 ? 'pos' : 'neg'}
                      value={result.profit_factor.toFixed(2)} />
                    <Metric label="Avg Win / Loss"
                      value={`${formatCurrency(result.avg_win)}`}
                      sub={`loss ${formatCurrency(result.avg_loss)}`} />
                  </div>

                  {/* Equity curve */}
                  <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-semibold text-[#f1f5f9]">Equity Curve</h3>
                      <span className="text-xs text-[#475569]">
                        {result.start_date} → {result.end_date}
                      </span>
                    </div>
                    <EquityCurve data={result.equity_curve} initial={result.initial_capital} />
                  </div>

                  {/* Trade log */}
                  <div className="rounded-xl border border-[#1f2d40] bg-[#111827] overflow-hidden">
                    <div className="px-4 py-3 border-b border-[#1f2d40] flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-[#f1f5f9]">Trade Log</h3>
                      <span className="text-xs text-[#475569]">{result.trades.length} trades</span>
                    </div>
                    <div className="max-h-96 overflow-y-auto">
                      <table className="w-full text-xs">
                        <thead className="sticky top-0 bg-[#0d1424]">
                          <tr className="text-[#475569]">
                            <th className="text-left font-medium px-3 py-2">Entry</th>
                            <th className="text-left font-medium px-3 py-2">Exit</th>
                            <th className="text-right font-medium px-3 py-2">Qty</th>
                            <th className="text-right font-medium px-3 py-2">P&L</th>
                            <th className="text-right font-medium px-3 py-2">%</th>
                            <th className="text-right font-medium px-3 py-2">Reason</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1a2235]">
                          {result.trades.map((t, i) => {
                            const win = t.realized_pnl >= 0
                            return (
                              <tr key={i} className="hover:bg-[#0a0e1a]">
                                <td className="px-3 py-1.5 text-[#94a3b8]">
                                  {t.entry_time.slice(0, 10)} <span className="text-[#475569]">${t.entry_price.toFixed(2)}</span>
                                </td>
                                <td className="px-3 py-1.5 text-[#94a3b8]">
                                  {t.exit_time.slice(0, 10)} <span className="text-[#475569]">${t.exit_price.toFixed(2)}</span>
                                </td>
                                <td className="px-3 py-1.5 text-right text-[#94a3b8] tabular-nums">{t.quantity}</td>
                                <td className={cn('px-3 py-1.5 text-right font-semibold tabular-nums', win ? 'text-green-400' : 'text-red-400')}>
                                  {win ? <ArrowUpRight className="inline h-3 w-3" /> : <ArrowDownRight className="inline h-3 w-3" />}
                                  {formatCurrency(t.realized_pnl)}
                                </td>
                                <td className={cn('px-3 py-1.5 text-right font-semibold tabular-nums', win ? 'text-green-400' : 'text-red-400')}>
                                  {t.realized_pnl_pct >= 0 ? '+' : ''}{t.realized_pnl_pct.toFixed(1)}%
                                </td>
                                <td className="px-3 py-1.5 text-right">
                                  <span className={cn('text-[10px] px-1.5 py-0.5 rounded',
                                    t.exit_reason === 'take_profit' ? 'bg-green-500/15 text-green-400' :
                                    t.exit_reason === 'stop_loss' ? 'bg-red-500/15 text-red-400' :
                                    'bg-[#475569]/15 text-[#94a3b8]')}>
                                    {t.exit_reason.replace('_', ' ')}
                                  </span>
                                </td>
                              </tr>
                            )
                          })}
                          {result.trades.length === 0 && (
                            <tr><td colSpan={6} className="px-3 py-6 text-center text-[#475569]">
                              No trades generated. Try loosening risk params or a different strategy/period.
                            </td></tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </div>

          </div>
        </div>
      </main>
    </PageTransition>
  )
}
