import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Bot, Plus, Trash2, Power, PowerOff, Activity, TrendingUp, TrendingDown,
  AlertTriangle, Loader2, X, Edit2, Info,
} from 'lucide-react'
import { Gauge } from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import {
  listBots, createBot, updateBot, deleteBot, getBotLogs, getStrategies,
  DEFAULT_RISK, type Bot as BotType, type BotLog, type StrategyInfo, type RiskParams,
} from '@/api/autotrade'
import { AutoPilotPanel } from './autopilot/AutoPilotPanel'
import type { MarketType } from '@/api/autopilot'
import { cn } from '@/lib/utils'
import { formatCurrency } from '@/lib/formatters'

type Mode = 'bots' | 'autopilot'

/** Segmented control to switch between the per-ticker Bots and AutoPilot. */
function ModeSwitch({ mode, setMode }: { mode: Mode; setMode: (m: Mode) => void }) {
  return (
    <div className="inline-flex rounded-xl bg-[#111827] border border-[#1f2d40] p-1">
      <button
        type="button" onClick={() => setMode('bots')}
        className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors',
          mode === 'bots' ? 'bg-[#6366f1] text-white' : 'text-[#94a3b8] hover:text-[#f1f5f9]')}
      >
        <Bot className="h-3.5 w-3.5" />Bots
      </button>
      <button
        type="button" onClick={() => setMode('autopilot')}
        className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors',
          mode === 'autopilot' ? 'bg-[#6366f1] text-white' : 'text-[#94a3b8] hover:text-[#f1f5f9]')}
      >
        <Gauge className="h-3.5 w-3.5" />AutoPilot
      </button>
    </div>
  )
}

/** Top-level page: switches between Bots and AutoPilot modes. */
export default function AutoTradePage() {
  const [mode, setMode] = useState<Mode>('bots')
  return mode === 'bots'
    ? <BotsView mode={mode} setMode={setMode} />
    : <AutoPilotView mode={mode} setMode={setMode} />
}

/** AutoPilot mode: Penny | Regular sub-sections. */
function AutoPilotView({ mode, setMode }: { mode: Mode; setMode: (m: Mode) => void }) {
  const [market, setMarket] = useState<MarketType>('regular')
  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#6366f1]/20">
                <Gauge className="h-5 w-5 text-[#6366f1]" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-[#f1f5f9]">AutoPilot</h1>
                <p className="text-xs text-[#475569]">
                  Automated day-trading toward a daily profit target • Paper only
                </p>
              </div>
            </div>
            <ModeSwitch mode={mode} setMode={setMode} />
          </div>

          {/* Reality-check banner */}
          <div className="flex items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-200/80 space-y-1">
              <p className="font-semibold">Paper trading only — the daily target is a goal, not a guarantee.</p>
              <p>
                AutoPilot scans for momentum, filters with an LLM, and opens paper positions toward your
                daily target. It stops trading once the target is hit and halts if the loss limit is reached.
                All positions are force-closed before market close (no overnight risk).
              </p>
            </div>
          </div>

          {/* Penny | Regular sub-tabs */}
          <div className="inline-flex rounded-xl bg-[#111827] border border-[#1f2d40] p-1">
            {(['regular', 'penny'] as MarketType[]).map((m) => (
              <button
                key={m} type="button" onClick={() => setMarket(m)}
                className={cn('px-4 py-1.5 rounded-lg text-xs font-bold capitalize transition-colors',
                  market === m ? 'bg-[#6366f1] text-white' : 'text-[#94a3b8] hover:text-[#f1f5f9]')}
              >
                {m} stocks
              </button>
            ))}
          </div>

          <AutoPilotPanel key={market} market={market} />
        </div>
      </main>
    </PageTransition>
  )
}

function BotsView({ mode, setMode }: { mode: Mode; setMode: (m: Mode) => void }) {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [editBot, setEditBot] = useState<BotType | null>(null)
  const [viewLogs, setViewLogs] = useState<string | null>(null)
  const [showStrategyInfo, setShowStrategyInfo] = useState(false)

  const { data: bots, isLoading } = useQuery({
    queryKey: ['autotrade', 'bots'],
    queryFn: listBots,
    refetchInterval: 30_000,  // refresh every 30s to show live stats
  })

  const { data: strategies } = useQuery({
    queryKey: ['autotrade', 'strategies'],
    queryFn: getStrategies,
    staleTime: Infinity,
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      updateBot(id, { enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['autotrade', 'bots'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteBot,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['autotrade', 'bots'] }),
  })

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl space-y-6">

          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#6366f1]/20">
                <Bot className="h-5 w-5 text-[#6366f1]" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-[#f1f5f9] flex items-center gap-2">
                  Auto-Trade Bots
                  <button
                    type="button"
                    onClick={() => setShowStrategyInfo(true)}
                    className="inline-flex items-center justify-center h-5 w-5 rounded-full text-[#475569] hover:text-[#6366f1] hover:bg-[#6366f1]/10 transition-colors"
                    aria-label="Strategy information"
                    title="How strategies work"
                  >
                    <Info className="h-4 w-4" />
                  </button>
                </h1>
                <p className="text-xs text-[#475569]">
                  Paper trading only • Runs every 5 min during market hours
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <ModeSwitch mode={mode} setMode={setMode} />
              <button
                type="button" onClick={() => setShowCreate(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold bg-[#6366f1] hover:bg-[#818cf8] text-white transition-colors"
              >
                <Plus className="h-4 w-4" />Create Bot
              </button>
            </div>
          </div>

          {/* Warning banner */}
          <div className="flex items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-200/80 space-y-1">
              <p className="font-semibold">Paper trading only — no real money at risk.</p>
              <p>
                Bots run automatically during market hours (9:30 AM – 4:00 PM ET, Mon–Fri).
                Signals are evaluated every 5 minutes. Each bot places paper orders through
                the risk manager — same stop-loss / take-profit rules as backtesting.
              </p>
            </div>
          </div>

          {/* Bot list */}
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-[#6366f1]" />
            </div>
          ) : !bots || bots.length === 0 ? (
            <div className="rounded-xl border border-[#1f2d40] bg-[#111827] p-12 flex flex-col items-center gap-3 text-center">
              <Bot className="h-12 w-12 text-[#1f2d40]" />
              <p className="text-sm text-[#475569]">
                No bots yet. Create your first bot to start auto-trading on paper.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {bots.map((bot) => (
                <BotCard
                  key={bot.id}
                  bot={bot}
                  strategies={strategies}
                  onToggle={(enabled) => toggleMutation.mutate({ id: bot.id, enabled })}
                  onEdit={() => setEditBot(bot)}
                  onDelete={() => {
                    if (confirm(`Delete bot "${bot.name}"? This cannot be undone.`))
                      deleteMutation.mutate(bot.id)
                  }}
                  onViewLogs={() => setViewLogs(bot.id)}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Modals */}
      {showStrategyInfo && (
        <StrategyInfoModal onClose={() => setShowStrategyInfo(false)} />
      )}
      {showCreate && (
        <BotModal
          strategies={strategies ?? []}
          onClose={() => setShowCreate(false)}
          onSuccess={() => {
            setShowCreate(false)
            queryClient.invalidateQueries({ queryKey: ['autotrade', 'bots'] })
          }}
        />
      )}
      {editBot && (
        <BotModal
          bot={editBot}
          strategies={strategies ?? []}
          onClose={() => setEditBot(null)}
          onSuccess={() => {
            setEditBot(null)
            queryClient.invalidateQueries({ queryKey: ['autotrade', 'bots'] })
          }}
        />
      )}
      {viewLogs && (
        <LogsModal
          botId={viewLogs}
          onClose={() => setViewLogs(null)}
        />
      )}
    </PageTransition>
  )
}

// ─── Bot Card ─────────────────────────────────────────────────────────────────
function BotCard({ bot, strategies, onToggle, onEdit, onDelete, onViewLogs }: {
  bot: BotType
  strategies?: StrategyInfo[]
  onToggle: (enabled: boolean) => void
  onEdit: () => void
  onDelete: () => void
  onViewLogs: () => void
}) {
  const winRate = bot.total_trades > 0 ? (bot.winning_trades / bot.total_trades) * 100 : 0
  const pnlPos = bot.total_pnl >= 0
  const lastRun = bot.last_run_at ? new Date(bot.last_run_at) : null
  const minutesAgo = lastRun ? Math.floor((Date.now() - lastRun.getTime()) / 60000) : null

  return (
    <div className={cn(
      'rounded-xl border bg-[#111827] p-4 transition-colors',
      bot.enabled ? 'border-[#6366f1]/30' : 'border-[#1f2d40]'
    )}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-bold text-[#f1f5f9] truncate">{bot.name}</h3>
            {bot.enabled ? (
              <span className="flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-green-500/15 text-green-400 border border-green-500/30">
                <Activity className="h-3 w-3" />ACTIVE
              </span>
            ) : (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#475569]/15 text-[#94a3b8]">
                PAUSED
              </span>
            )}
          </div>
          <p className="text-xs text-[#475569]">
            {bot.ticker} · {strategies?.find((s: StrategyInfo) => s.name === bot.strategy)?.display_name ?? bot.strategy}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button" onClick={() => onToggle(!bot.enabled)}
            className="p-1.5 rounded-lg hover:bg-[#1f2d40] transition-colors"
            title={bot.enabled ? 'Pause bot' : 'Resume bot'}
          >
            {bot.enabled
              ? <PowerOff className="h-4 w-4 text-[#94a3b8]" />
              : <Power className="h-4 w-4 text-[#94a3b8]" />}
          </button>
          <button
            type="button" onClick={onEdit}
            className="p-1.5 rounded-lg hover:bg-[#1f2d40] transition-colors"
            title="Edit bot"
          >
            <Edit2 className="h-4 w-4 text-[#94a3b8]" />
          </button>
          <button
            type="button" onClick={onDelete}
            className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
            title="Delete bot"
          >
            <Trash2 className="h-4 w-4 text-red-400" />
          </button>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="rounded-lg bg-[#0a0e1a] px-2 py-1.5">
          <p className="text-[9px] text-[#475569] uppercase tracking-wide">Trades</p>
          <p className="text-sm font-bold text-[#f1f5f9] tabular-nums">{bot.total_trades}</p>
        </div>
        <div className="rounded-lg bg-[#0a0e1a] px-2 py-1.5">
          <p className="text-[9px] text-[#475569] uppercase tracking-wide">Win Rate</p>
          <p className={cn('text-sm font-bold tabular-nums', winRate >= 50 ? 'text-green-400' : 'text-red-400')}>
            {bot.total_trades > 0 ? `${winRate.toFixed(0)}%` : '—'}
          </p>
        </div>
        <div className="rounded-lg bg-[#0a0e1a] px-2 py-1.5">
          <p className="text-[9px] text-[#475569] uppercase tracking-wide">Total P&L</p>
          <p className={cn('text-sm font-bold tabular-nums flex items-center gap-0.5', pnlPos ? 'text-green-400' : 'text-red-400')}>
            {pnlPos ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {formatCurrency(bot.total_pnl)}
          </p>
        </div>
      </div>

      {/* Status footer */}
      <div className="flex items-center justify-between pt-2 border-t border-[#1f2d40]">
        <div className="min-w-0 flex-1">
          {bot.last_run_at ? (
            <div className="flex items-center gap-1.5">
              <div className={cn('h-1.5 w-1.5 rounded-full', bot.enabled ? 'bg-green-400 animate-pulse' : 'bg-[#475569]')} />
              <span className="text-[10px] text-[#475569]">
                Last run: {minutesAgo !== null ? (minutesAgo === 0 ? 'just now' : `${minutesAgo}m ago`) : 'unknown'}
              </span>
              {bot.last_signal && (
                <span className={cn('text-[10px] font-bold px-1 py-0.5 rounded',
                  bot.last_signal === 'BUY' ? 'bg-green-500/15 text-green-400' :
                  bot.last_signal === 'SELL' ? 'bg-red-500/15 text-red-400' :
                  'bg-[#475569]/15 text-[#94a3b8]')}>
                  {bot.last_signal}
                </span>
              )}
            </div>
          ) : (
            <span className="text-[10px] text-[#475569]">Never run</span>
          )}
          {bot.last_error && (
            <p className="text-[10px] text-red-400 truncate mt-0.5" title={bot.last_error}>
              Error: {bot.last_error}
            </p>
          )}
        </div>
        <button
          type="button" onClick={onViewLogs}
          className="text-[10px] text-[#6366f1] hover:text-[#818cf8] font-semibold transition-colors"
        >
          View Logs
        </button>
      </div>
    </div>
  )
}

// ─── Bot Modal (Create/Edit) ──────────────────────────────────────────────────
function BotModal({ bot, strategies, onClose, onSuccess }: {
  bot?: BotType
  strategies: StrategyInfo[]
  onClose: () => void
  onSuccess: () => void
}) {
  const isEdit = !!bot
  const [name, setName] = useState(bot?.name ?? '')
  const [ticker, setTicker] = useState(bot?.ticker ?? '')
  const [strategy, setStrategy] = useState(bot?.strategy ?? 'momentum')
  const [enabled, setEnabled] = useState(bot?.enabled ?? true)
  const [risk, setRisk] = useState<RiskParams>(bot?.risk ?? DEFAULT_RISK)

  const mutation = useMutation({
    mutationFn: async () => {
      if (isEdit) {
        return updateBot(bot.id, { name, ticker, strategy, enabled, risk })
      } else {
        return createBot({ name, ticker, strategy, enabled, risk })
      }
    },
    onSuccess,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !ticker.trim()) return
    mutation.mutate()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-[#111827] rounded-xl border border-[#1f2d40] w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-[#1f2d40]">
            <h2 className="text-lg font-bold text-[#f1f5f9]">
              {isEdit ? 'Edit Bot' : 'Create Bot'}
            </h2>
            <button
              type="button" onClick={onClose}
              className="p-1 rounded-lg hover:bg-[#1f2d40] transition-colors"
            >
              <X className="h-5 w-5 text-[#94a3b8]" />
            </button>
          </div>

          {/* Body */}
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-[#475569] block mb-1">Bot Name</label>
                <input
                  type="text" value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="My Momentum Bot"
                  className="w-full px-3 py-2 rounded-lg text-sm bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] focus:outline-none focus:border-[#6366f1]/50"
                />
              </div>
              <div>
                <label className="text-xs text-[#475569] block mb-1">Ticker</label>
                <input
                  type="text" value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10))}
                  placeholder="AAPL"
                  className="w-full px-3 py-2 rounded-lg text-sm bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] focus:outline-none focus:border-[#6366f1]/50"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-[#475569] block mb-1">Strategy</label>
              <select
                value={strategy} onChange={(e) => setStrategy(e.target.value)}
                className="w-full px-3 py-2 rounded-lg text-sm bg-[#0a0e1a] border border-[#1f2d40] text-[#f1f5f9] focus:outline-none focus:border-[#6366f1]/50"
              >
                {strategies.map((s) => (
                  <option key={s.name} value={s.name}>{s.display_name}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox" id="enabled" checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-[#1f2d40] bg-[#0a0e1a] text-[#6366f1] focus:ring-[#6366f1]/50"
              />
              <label htmlFor="enabled" className="text-sm text-[#f1f5f9] cursor-pointer">
                Enable bot (will run every 5 min during market hours)
              </label>
            </div>

            {/* Risk params */}
            <div className="rounded-lg border border-[#1f2d40] bg-[#0a0e1a] p-3 space-y-2.5">
              <h3 className="text-xs font-semibold text-[#f1f5f9] mb-2">Risk Management</h3>
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
                    <div className="flex justify-between text-[10px] mb-1">
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
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 p-4 border-t border-[#1f2d40]">
            <button
              type="button" onClick={onClose}
              className="px-4 py-2 rounded-xl text-sm font-bold text-[#94a3b8] hover:bg-[#1f2d40] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit" disabled={mutation.isPending || !name.trim() || !ticker.trim()}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold bg-[#6366f1] hover:bg-[#818cf8] text-white transition-colors disabled:opacity-60"
            >
              {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {isEdit ? 'Update Bot' : 'Create Bot'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Logs Modal ───────────────────────────────────────────────────────────────
function LogsModal({ botId, onClose }: { botId: string; onClose: () => void }) {
  const { data: logs, isLoading } = useQuery({
    queryKey: ['autotrade', 'bots', botId, 'logs'],
    queryFn: () => getBotLogs(botId, 100),
    refetchInterval: 10_000,  // refresh every 10s for live updates
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-[#111827] rounded-xl border border-[#1f2d40] w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#1f2d40]">
          <h2 className="text-lg font-bold text-[#f1f5f9]">Execution Logs</h2>
          <button
            type="button" onClick={onClose}
            className="p-1 rounded-lg hover:bg-[#1f2d40] transition-colors"
          >
            <X className="h-5 w-5 text-[#94a3b8]" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-[#6366f1]" />
            </div>
          ) : !logs || logs.length === 0 ? (
            <div className="text-center py-12 text-sm text-[#475569]">
              No logs yet. The bot will log every execution here.
            </div>
          ) : (
            <div className="space-y-2">
              {logs.map((log: BotLog) => {
                const time = new Date(log.timestamp).toLocaleString()
                const actionColor =
                  log.action_taken === 'order_placed' ? 'text-green-400' :
                  log.action_taken === 'risk_blocked' ? 'text-amber-400' :
                  log.action_taken === 'error' ? 'text-red-400' :
                  'text-[#94a3b8]'
                return (
                  <div key={log.id} className="rounded-lg bg-[#0a0e1a] border border-[#1f2d40] p-3">
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-[#475569] tabular-nums">{time}</span>
                        <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded',
                          log.signal_type === 'BUY' ? 'bg-green-500/15 text-green-400' :
                          log.signal_type === 'SELL' ? 'bg-red-500/15 text-red-400' :
                          'bg-[#475569]/15 text-[#94a3b8]')}>
                          {log.signal_type}
                        </span>
                        {log.signal_confidence !== null && (
                          <span className="text-[10px] text-[#475569]">
                            {log.signal_confidence.toFixed(0)}% conf
                          </span>
                        )}
                      </div>
                      {log.price !== null && (
                        <span className="text-xs text-[#94a3b8] tabular-nums">${log.price.toFixed(2)}</span>
                      )}
                    </div>
                    {log.signal_reason && (
                      <p className="text-xs text-[#94a3b8] mb-1">{log.signal_reason}</p>
                    )}
                    <div className="flex items-center justify-between">
                      <span className={cn('text-xs font-semibold', actionColor)}>
                        {log.action_taken.replace('_', ' ').toUpperCase()}
                      </span>
                      {log.order_id && (
                        <span className="text-[10px] text-[#475569]">Order: {log.order_id.slice(0, 8)}</span>
                      )}
                    </div>
                    {log.details && (
                      <p className="text-[10px] text-[#475569] mt-1">{log.details}</p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Strategy Info Modal ──────────────────────────────────────────────────────

const STRATEGY_DETAILS = [
  {
    name: 'Momentum (RSI + MACD)',
    slug: 'momentum',
    colour: 'text-[#6366f1] bg-[#6366f1]/10 border-[#6366f1]/30',
    tagline: 'Follow the trend — buy strength, sell weakness.',
    description:
      'Uses RSI and MACD to detect when a stock is gaining bullish momentum. '
      + 'It waits for both indicators to agree before entering, then exits when the momentum fades.',
    buy: 'RSI ≥ 55 AND MACD histogram is positive (bullish crossover).',
    sell: 'RSI ≥ 70 (overbought) OR MACD histogram turns negative.',
    minBars: 35,
    bestFor: 'Trending markets, breakouts, strong earnings movers.',
    risk: 'Can whipsaw in sideways/choppy markets.',
    indicators: [
      { name: 'RSI(14)', note: 'Momentum oscillator 0–100. Above 55 = bullish.' },
      { name: 'MACD(12,26,9)', note: 'Trend-following. Positive histogram = bullish pressure.' },
    ],
  },
  {
    name: 'Mean Reversion (Bollinger Bands)',
    slug: 'mean_reversion',
    colour: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
    tagline: 'Buy dips — prices return to the mean.',
    description:
      'Looks for stocks that have temporarily dropped below their normal price range (lower Bollinger Band). '
      + 'The theory is that extreme moves revert — so it buys the dip and sells when price recovers.',
    buy: 'Price falls below the lower Bollinger Band (2σ below 20-day SMA) while RSI is oversold.',
    sell: 'Price reverts to or above the middle Bollinger Band (20-day SMA).',
    minBars: 25,
    bestFor: 'Range-bound markets, sideways consolidation, high-liquidity large-caps.',
    risk: 'A true downtrend can keep breaking lower — "catching a falling knife."',
    indicators: [
      { name: 'Bollinger Bands(20, 2σ)', note: 'Upper/Middle/Lower bands around price. Lower band = oversold zone.' },
      { name: 'RSI(14)', note: 'Used as confirmation — only enter if RSI also suggests oversold.' },
    ],
  },
  {
    name: 'MA Crossover (SMA 20/50)',
    slug: 'ma_crossover',
    colour: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    tagline: 'Classic trend-following via moving average crossovers.',
    description:
      'Watches for a short-term moving average to cross above or below a longer-term one. '
      + 'A golden cross signals the start of an uptrend; a death cross signals a downtrend.',
    buy: 'SMA-20 crosses above SMA-50 (Golden Cross) — uptrend confirmed.',
    sell: 'SMA-20 crosses below SMA-50 (Death Cross) — downtrend confirmed.',
    minBars: 50,
    bestFor: 'Identifying new trends early. Works well on daily charts for medium-term moves.',
    risk: 'Lags the market — signals come after the move has already started. Generates false signals in ranging markets.',
    indicators: [
      { name: 'SMA(20)', note: 'Short-term average. Reacts faster to price changes.' },
      { name: 'SMA(50)', note: 'Longer-term trend. More stable, slower to react.' },
    ],
  },
]

function StrategyInfoModal({ onClose }: { onClose: () => void }) {
  const [active, setActive] = useState(0)
  const s = STRATEGY_DETAILS[active]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#0d1321] rounded-2xl border border-[#1f2d40] w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f2d40]">
          <div className="flex items-center gap-2">
            <Info className="h-4.5 w-4.5 text-[#6366f1]" />
            <h2 className="text-base font-bold text-[#f1f5f9]">How Strategies Work</h2>
          </div>
          <button
            type="button" onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[#1f2d40] text-[#475569] hover:text-[#f1f5f9] transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Strategy tabs */}
        <div className="flex border-b border-[#1f2d40] px-5 gap-1 pt-2">
          {STRATEGY_DETAILS.map((strat, i) => (
            <button
              key={strat.slug}
              type="button"
              onClick={() => setActive(i)}
              className={cn(
                'px-3 py-2 text-xs font-bold rounded-t-lg border-b-2 transition-colors whitespace-nowrap',
                active === i
                  ? 'border-[#6366f1] text-[#f1f5f9]'
                  : 'border-transparent text-[#475569] hover:text-[#94a3b8]',
              )}
            >
              {strat.name.split(' (')[0]}
            </button>
          ))}
        </div>

        {/* Strategy content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">

          {/* Name + tagline */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={cn('text-xs font-bold px-2 py-0.5 rounded-full border', s.colour)}>
                {s.name}
              </span>
              <span className="text-[10px] text-[#475569]">min {s.minBars} bars of data</span>
            </div>
            <p className="text-sm font-semibold text-[#f1f5f9]">{s.tagline}</p>
            <p className="text-xs text-[#94a3b8] mt-1 leading-relaxed">{s.description}</p>
          </div>

          {/* Signal rules */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="rounded-xl bg-green-500/5 border border-green-500/20 p-3">
              <p className="text-[10px] font-bold text-green-400 uppercase tracking-wide mb-1.5">
                ↑ BUY Signal
              </p>
              <p className="text-xs text-[#e2e8f0] leading-relaxed">{s.buy}</p>
            </div>
            <div className="rounded-xl bg-red-500/5 border border-red-500/20 p-3">
              <p className="text-[10px] font-bold text-red-400 uppercase tracking-wide mb-1.5">
                ↓ SELL Signal
              </p>
              <p className="text-xs text-[#e2e8f0] leading-relaxed">{s.sell}</p>
            </div>
          </div>

          {/* Indicators used */}
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[#475569] mb-2">
              Indicators
            </p>
            <div className="space-y-2">
              {s.indicators.map((ind) => (
                <div key={ind.name} className="flex items-start gap-2">
                  <span className="text-[10px] font-bold text-[#6366f1] bg-[#6366f1]/10 px-1.5 py-0.5 rounded shrink-0 mt-0.5">
                    {ind.name}
                  </span>
                  <p className="text-xs text-[#94a3b8]">{ind.note}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Best for / Risk */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="rounded-xl bg-[#111827] border border-[#1f2d40] p-3">
              <p className="text-[10px] font-bold text-[#475569] uppercase tracking-wide mb-1">Best For</p>
              <p className="text-xs text-[#94a3b8] leading-relaxed">{s.bestFor}</p>
            </div>
            <div className="rounded-xl bg-amber-500/5 border border-amber-500/20 p-3">
              <p className="text-[10px] font-bold text-amber-400 uppercase tracking-wide mb-1">⚠ Risk</p>
              <p className="text-xs text-[#94a3b8] leading-relaxed">{s.risk}</p>
            </div>
          </div>

          {/* How the bot executes */}
          <div className="rounded-xl bg-[#111827] border border-[#1f2d40] p-3 space-y-2">
            <p className="text-[10px] font-bold text-[#475569] uppercase tracking-wide">
              Execution Flow (every 5 min during market hours)
            </p>
            {[
              'Fetch 60 days of daily OHLCV bars from yfinance',
              'Evaluate strategy → BUY / SELL / HOLD signal',
              'If BUY and no open position: run through risk gates (confidence, position limits, daily loss limit, cash)',
              'If approved: place market buy order, size = equity × position_size_pct',
              'If SELL and have position: close the position, record P&L',
              'Log every execution to the audit trail (View Logs button)',
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-[10px] font-bold text-[#6366f1] tabular-nums shrink-0 mt-0.5 w-4">
                  {i + 1}.
                </span>
                <p className="text-xs text-[#94a3b8]">{step}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer note */}
        <div className="px-5 py-3 border-t border-[#1f2d40]">
          <p className="text-[10px] text-[#334155] text-center">
            All trading is paper only — no real money at risk. All signals are evaluated on daily bars.
          </p>
        </div>
      </div>
    </div>
  )
}
