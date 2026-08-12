import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Power, PowerOff, Loader2, Target, TrendingUp, TrendingDown,
  Sparkles, XCircle, Settings2, Activity,
} from 'lucide-react'
import {
  getConfig, updateConfig, setEnabled, flatten, getStatus, getTrades, getReports,
  type MarketType, type AutoPilotConfig, type AutoPilotConfigUpdate,
} from '@/api/autopilot'
import { cn } from '@/lib/utils'
import { formatCurrency } from '@/lib/formatters'

/**
 * One AutoPilot section (penny OR regular). Shows the live daily progress,
 * config editor, open positions, and daily report history.
 */
export function AutoPilotPanel({ market }: { market: MarketType }) {
  const qc = useQueryClient()
  const [showConfig, setShowConfig] = useState(false)

  const { data: config } = useQuery({
    queryKey: ['autopilot', market, 'config'],
    queryFn: () => getConfig(market),
  })

  const { data: status } = useQuery({
    queryKey: ['autopilot', market, 'status'],
    queryFn: () => getStatus(market),
    refetchInterval: 15_000,
  })

  const { data: trades } = useQuery({
    queryKey: ['autopilot', market, 'trades'],
    queryFn: () => getTrades(market, 50),
    refetchInterval: 15_000,
  })

  const { data: reports } = useQuery({
    queryKey: ['autopilot', market, 'reports'],
    queryFn: () => getReports(market, 30),
    refetchInterval: 60_000,
  })

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['autopilot', market] })
  }

  const toggleMutation = useMutation({
    mutationFn: (enabled: boolean) => setEnabled(market, enabled),
    onSuccess: invalidate,
  })

  const flattenMutation = useMutation({
    mutationFn: () => flatten(market),
    onSuccess: invalidate,
  })

  if (!config || !status) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-[#6366f1]" />
      </div>
    )
  }

  const openTrades = (trades ?? []).filter((t) => t.status === 'open')
  const closedTrades = (trades ?? []).filter((t) => t.status === 'closed')
  const pnl = status.realized_pnl_today
  const pnlPos = pnl >= 0
  const progress = Math.min(Math.max(status.progress_pct, 0), 100)

  const statusStyles: Record<string, string> = {
    idle: 'bg-[#475569]/15 text-[#94a3b8]',
    scanning: 'bg-blue-500/15 text-blue-400',
    trading: 'bg-[#6366f1]/15 text-[#818cf8]',
    target_hit: 'bg-green-500/15 text-green-400',
    halted: 'bg-red-500/15 text-red-400',
    closed: 'bg-amber-500/15 text-amber-400',
  }

  return (
    <div className="space-y-4">
      {/* Master control + status */}
      <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-[#f1f5f9] capitalize">{market} AutoPilot</h3>
              <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded uppercase',
                statusStyles[status.status] ?? statusStyles.idle)}>
                {status.status.replace('_', ' ')}
              </span>
              {config.use_llm && (
                <span className="flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-300">
                  <Sparkles className="h-3 w-3" />LLM
                </span>
              )}
            </div>
            <p className="text-xs text-[#475569] mt-0.5">
              {status.enabled ? 'Running during market hours' : 'Paused'} · provider {config.data_provider ?? 'default'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowConfig((v) => !v)}
              className="p-2 rounded-lg hover:bg-[#1f2d40] transition-colors"
              title="Configure"
            >
              <Settings2 className="h-4 w-4 text-[#94a3b8]" />
            </button>
            <button
              type="button"
              onClick={() => toggleMutation.mutate(!status.enabled)}
              disabled={toggleMutation.isPending}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-bold transition-colors',
                status.enabled
                  ? 'bg-red-500/15 text-red-400 hover:bg-red-500/25'
                  : 'bg-green-500/15 text-green-400 hover:bg-green-500/25'
              )}
            >
              {toggleMutation.isPending
                ? <Loader2 className="h-4 w-4 animate-spin" />
                : status.enabled ? <PowerOff className="h-4 w-4" /> : <Power className="h-4 w-4" />}
              {status.enabled ? 'Stop' : 'Start'}
            </button>
          </div>
        </div>

        {/* Progress toward daily target */}
        <div className="rounded-lg bg-[#0a0e1a] p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5 text-xs text-[#94a3b8]">
              <Target className="h-3.5 w-3.5" />
              Today's target
            </div>
            <div className={cn('text-sm font-bold tabular-nums flex items-center gap-1', pnlPos ? 'text-green-400' : 'text-red-400')}>
              {pnlPos ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
              {formatCurrency(pnl)} / {formatCurrency(status.daily_profit_target)}
            </div>
          </div>
          <div className="h-2.5 rounded-full bg-[#1f2d40] overflow-hidden">
            <div
              className={cn('h-full rounded-full transition-all',
                status.halted ? 'bg-red-500' : status.target_hit ? 'bg-green-500' : 'bg-[#6366f1]')}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-2 text-[10px] text-[#475569]">
            <span>Capital {formatCurrency(status.capital)}</span>
            <span>{status.open_positions} open · {status.trades_today} trades today</span>
          </div>
          {status.target_hit && (
            <p className="mt-2 text-[10px] text-green-400 font-semibold">
              Target hit — trading locked for the day to protect gains.
            </p>
          )}
          {status.halted && (
            <p className="mt-2 text-[10px] text-red-400 font-semibold">
              Daily loss limit hit — halted and flattened for the day.
            </p>
          )}
        </div>

        {openTrades.length > 0 && (
          <button
            type="button"
            onClick={() => flattenMutation.mutate()}
            disabled={flattenMutation.isPending}
            className="mt-3 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 transition-colors"
          >
            {flattenMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <XCircle className="h-3.5 w-3.5" />}
            Close all {openTrades.length} positions now
          </button>
        )}

        {config.last_error && (
          <p className="mt-2 text-[10px] text-red-400 truncate" title={config.last_error}>
            Last error: {config.last_error}
          </p>
        )}
      </div>

      {showConfig && (
        <ConfigEditor
          market={market}
          config={config}
          onSaved={() => { setShowConfig(false); invalidate() }}
        />
      )}

      {/* Open positions */}
      <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-4">
        <h4 className="text-xs font-bold text-[#f1f5f9] mb-3 flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5 text-[#6366f1]" />Open Positions
        </h4>
        {openTrades.length === 0 ? (
          <p className="text-xs text-[#475569] py-2">No open positions.</p>
        ) : (
          <div className="space-y-2">
            {openTrades.map((t) => (
              <div key={t.id} className="rounded-lg bg-[#0a0e1a] p-2.5 flex items-center justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[#f1f5f9]">{t.ticker}</span>
                    <span className="text-[10px] text-[#475569]">x{t.quantity} @ ${t.entry_price.toFixed(2)}</span>
                    {t.llm_confidence != null && (
                      <span className="text-[10px] text-purple-300">LLM {t.llm_confidence.toFixed(0)}%</span>
                    )}
                  </div>
                  <p className="text-[10px] text-[#475569] truncate max-w-md" title={t.entry_reason ?? ''}>{t.entry_reason}</p>
                </div>
                <div className="text-right text-[10px] text-[#94a3b8] shrink-0">
                  <div>TP ${t.take_profit_price.toFixed(2)}</div>
                  <div>SL ${t.stop_price.toFixed(2)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Today's closed trades */}
      {closedTrades.length > 0 && (
        <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-4">
          <h4 className="text-xs font-bold text-[#f1f5f9] mb-3">Recent Closed Trades</h4>
          <div className="space-y-1.5">
            {closedTrades.slice(0, 15).map((t) => {
              const win = (t.realized_pnl ?? 0) >= 0
              return (
                <div key={t.id} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-[#f1f5f9]">{t.ticker}</span>
                    <span className="text-[10px] text-[#475569]">{t.exit_reason}</span>
                  </div>
                  <span className={cn('font-bold tabular-nums', win ? 'text-green-400' : 'text-red-400')}>
                    {win ? '+' : ''}{formatCurrency(t.realized_pnl ?? 0)}
                    <span className="text-[10px] ml-1 opacity-70">({t.realized_pnl_pct?.toFixed(1)}%)</span>
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Daily report history */}
      <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-4">
        <h4 className="text-xs font-bold text-[#f1f5f9] mb-3">Daily Reports</h4>
        {!reports || reports.length === 0 ? (
          <p className="text-xs text-[#475569] py-2">No reports yet. One is generated after each trading day.</p>
        ) : (
          <div className="space-y-2">
            {reports.map((r) => {
              const win = r.realized_pnl >= 0
              return (
                <div key={r.id} className="rounded-lg bg-[#0a0e1a] p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-[#f1f5f9]">{r.trading_day}</span>
                    <div className="flex items-center gap-2">
                      {r.target_met && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-green-500/15 text-green-400">TARGET MET</span>
                      )}
                      <span className={cn('text-sm font-bold tabular-nums', win ? 'text-green-400' : 'text-red-400')}>
                        {win ? '+' : ''}{formatCurrency(r.realized_pnl)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-[#475569]">
                    <span>{r.num_trades} trades</span>
                    <span>{r.win_rate.toFixed(0)}% win</span>
                    <span>{r.return_pct.toFixed(2)}% return</span>
                  </div>
                  {r.summary && <p className="text-[10px] text-[#94a3b8] mt-1.5">{r.summary}</p>}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Config editor ──────────────────────────────────────────────────────────
function ConfigEditor({ market, config, onSaved }: {
  market: MarketType
  config: AutoPilotConfig
  onSaved: () => void
}) {
  const [form, setForm] = useState<AutoPilotConfigUpdate>({
    capital: config.capital,
    daily_profit_target: config.daily_profit_target,
    daily_loss_limit: config.daily_loss_limit,
    max_concurrent_positions: config.max_concurrent_positions,
    max_position_size_pct: config.max_position_size_pct,
    take_profit_pct: config.take_profit_pct,
    stop_loss_pct: config.stop_loss_pct,
    min_price: config.min_price,
    max_price: config.max_price,
    min_change_pct: config.min_change_pct,
    min_volume_ratio: config.min_volume_ratio,
    max_candidates: config.max_candidates,
    use_llm: config.use_llm,
    llm_min_confidence: config.llm_min_confidence,
  })

  const mutation = useMutation({
    mutationFn: () => updateConfig(market, form),
    onSuccess: onSaved,
  })

  const num = (k: keyof AutoPilotConfigUpdate) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: Number(e.target.value) }))

  const field = (label: string, k: keyof AutoPilotConfigUpdate, step = 1, suffix?: string) => (
    <div>
      <label className="text-[10px] text-[#475569] block mb-1">{label}{suffix ? ` (${suffix})` : ''}</label>
      <input
        type="number" step={step} value={form[k] as number}
        onChange={num(k)}
        className="w-full px-2 py-1.5 rounded-lg text-xs bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] focus:outline-none focus:border-[#6366f1]/50"
      />
    </div>
  )

  return (
    <div className="rounded-xl border border-[#6366f1]/30 bg-[#111827] p-4 space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {field('Capital', 'capital', 100, '$')}
        {field('Daily target', 'daily_profit_target', 10, '$')}
        {field('Daily loss limit', 'daily_loss_limit', 10, '$')}
        {field('Max positions', 'max_concurrent_positions', 1)}
        {field('Max pos size', 'max_position_size_pct', 0.01, 'frac')}
        {field('Take profit', 'take_profit_pct', 0.005, 'frac')}
        {field('Stop loss', 'stop_loss_pct', 0.005, 'frac')}
        {field('Min price', 'min_price', 0.5, '$')}
        {field('Max price', 'max_price', 1, '$')}
        {field('Min change', 'min_change_pct', 0.5, '%')}
        {field('Min volume ratio', 'min_volume_ratio', 0.1, 'x')}
        {field('Max candidates', 'max_candidates', 1)}
      </div>

      <div className="flex items-center gap-4 pt-2 border-t border-[#1f2d40]">
        <label className="flex items-center gap-2 text-xs text-[#f1f5f9] cursor-pointer">
          <input
            type="checkbox" checked={!!form.use_llm}
            onChange={(e) => setForm((f) => ({ ...f, use_llm: e.target.checked }))}
            className="h-4 w-4 rounded border-[#1f2d40] bg-[#0a0e1a] text-[#6366f1]"
          />
          Use LLM prediction gate
        </label>
        {form.use_llm && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[#475569]">Min confidence</span>
            <input
              type="number" step={5} value={form.llm_min_confidence as number}
              onChange={num('llm_min_confidence')}
              className="w-16 px-2 py-1 rounded-lg text-xs bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] focus:outline-none focus:border-[#6366f1]/50"
            />
          </div>
        )}
      </div>

      <div className="flex justify-end">
        <button
          type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold bg-[#6366f1] hover:bg-[#818cf8] text-white transition-colors disabled:opacity-60"
        >
          {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          Save config
        </button>
      </div>
    </div>
  )
}
