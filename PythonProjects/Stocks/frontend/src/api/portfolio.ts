import apiClient from './client'

// --- Response types ---

export interface Benchmark {
  ticker: string
  return_pct: number
}

export interface PortfolioSummary {
  account_id: string
  cash: number
  portfolio_value: number
  total_value: number
  buying_power: number
  initial_cash: number
  total_return: number
  total_return_pct: number
  realized_pnl: number
  unrealized_pnl: number
  day_pnl: number
  win_rate: number
  num_trades: number
  num_winning_trades: number
  num_losing_trades: number
  avg_win: number
  avg_loss: number
  benchmark?: Benchmark
}

export interface Position {
  ticker: string
  quantity: number
  avg_entry_price: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  cost_basis: number
  day_change_pct?: number
}

export interface ClosedTradeRecord {
  ticker: string
  side: string
  quantity: number
  entry_price: number
  exit_price: number
  realized_pnl: number
  opened_at: string
  closed_at: string
}

export interface EquitySnapshot {
  timestamp: string
  equity: number
}

export interface PortfolioHistory {
  closed_trades: ClosedTradeRecord[]
  equity_snapshots: EquitySnapshot[]
  total_realized_pnl: number
}

// --- API functions ---

export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  const res = await apiClient.get<PortfolioSummary>('/portfolio/summary')
  return res.data
}

export async function getPositions(): Promise<Position[]> {
  const res = await apiClient.get<Position[]>('/portfolio/positions')
  return res.data
}

export async function getPortfolioHistory(): Promise<PortfolioHistory> {
  const res = await apiClient.get<PortfolioHistory>('/portfolio/history')
  return res.data
}
