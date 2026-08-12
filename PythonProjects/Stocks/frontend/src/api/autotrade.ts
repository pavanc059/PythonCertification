import apiClient from './client'

export interface RiskParams {
  position_size_pct: number
  stop_loss_pct: number
  take_profit_pct: number
  daily_loss_limit_pct: number
  max_positions: number
  max_trades_per_day: number
  min_confidence: number
}

export interface BacktestRequest {
  ticker: string
  strategy: string
  period: string
  interval: string
  initial_capital: number
  risk: RiskParams
}

export interface TradeRecord {
  ticker: string
  entry_time: string
  entry_price: number
  exit_time: string
  exit_price: number
  quantity: number
  realized_pnl: number
  realized_pnl_pct: number
  exit_reason: string
}

export interface EquityPoint {
  date: string
  equity: number
}

export interface BacktestResult {
  ticker: string
  strategy: string
  start_date: string
  end_date: string
  initial_capital: number
  final_equity: number
  total_return: number
  total_return_pct: number
  num_trades: number
  num_winning: number
  num_losing: number
  win_rate: number
  avg_win: number
  avg_loss: number
  profit_factor: number
  max_drawdown_pct: number
  sharpe_ratio: number
  trades: TradeRecord[]
  equity_curve: EquityPoint[]
}

export interface StrategyInfo {
  name: string
  display_name: string
  min_bars: number
}

export async function getStrategies(): Promise<StrategyInfo[]> {
  const res = await apiClient.get<{ strategies: StrategyInfo[] }>('/autotrade/strategies')
  return res.data.strategies
}

export async function runBacktest(req: BacktestRequest): Promise<BacktestResult> {
  const res = await apiClient.post<BacktestResult>('/autotrade/backtest', req)
  return res.data
}

export const DEFAULT_RISK: RiskParams = {
  position_size_pct: 0.10,
  stop_loss_pct: 0.02,
  take_profit_pct: 0.04,
  daily_loss_limit_pct: 0.03,
  max_positions: 5,
  max_trades_per_day: 10,
  min_confidence: 55,
}

// ------------------------------------------------------------------
// Bot CRUD
// ------------------------------------------------------------------

export interface CreateBotRequest {
  name: string
  ticker: string
  strategy: string
  risk: RiskParams
  enabled: boolean
}

export interface UpdateBotRequest {
  name?: string
  ticker?: string
  strategy?: string
  risk?: RiskParams
  enabled?: boolean
}

export interface Bot {
  id: string
  name: string
  ticker: string
  strategy: string
  enabled: boolean
  risk: RiskParams
  last_run_at: string | null
  last_signal: string | null
  last_error: string | null
  total_trades: number
  winning_trades: number
  total_pnl: number
  created_at: string
  updated_at: string
}

export interface BotLog {
  id: string
  timestamp: string
  ticker: string
  price: number | null
  signal_type: string
  signal_confidence: number | null
  signal_reason: string | null
  action_taken: string
  order_id: string | null
  details: string | null
}

export async function createBot(req: CreateBotRequest): Promise<Bot> {
  const res = await apiClient.post<Bot>('/autotrade/bots', req)
  return res.data
}

export async function listBots(): Promise<Bot[]> {
  const res = await apiClient.get<Bot[]>('/autotrade/bots')
  return res.data
}

export async function getBot(id: string): Promise<Bot> {
  const res = await apiClient.get<Bot>(`/autotrade/bots/${id}`)
  return res.data
}

export async function updateBot(id: string, req: UpdateBotRequest): Promise<Bot> {
  const res = await apiClient.patch<Bot>(`/autotrade/bots/${id}`, req)
  return res.data
}

export async function deleteBot(id: string): Promise<void> {
  await apiClient.delete(`/autotrade/bots/${id}`)
}

export async function getBotLogs(id: string, limit = 100): Promise<BotLog[]> {
  const res = await apiClient.get<BotLog[]>(`/autotrade/bots/${id}/logs?limit=${limit}`)
  return res.data
}
