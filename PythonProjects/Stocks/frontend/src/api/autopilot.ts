import apiClient from './client'

export type MarketType = 'penny' | 'regular'

export interface AutoPilotConfig {
  id: string
  market_type: MarketType
  enabled: boolean
  capital: number
  daily_profit_target: number
  daily_loss_limit: number
  max_concurrent_positions: number
  max_position_size_pct: number
  take_profit_pct: number
  stop_loss_pct: number
  min_price: number
  max_price: number
  min_change_pct: number
  min_volume_ratio: number
  max_candidates: number
  use_llm: boolean
  llm_min_confidence: number
  force_flat_minutes_before_close: number
  data_provider: string | null
  trading_day: string | null
  realized_pnl_today: number
  trades_today: number
  target_hit: boolean
  halted: boolean
  status: string
  last_run_at: string | null
  last_error: string | null
  created_at: string
  updated_at: string
}

export type AutoPilotConfigUpdate = Partial<
  Pick<
    AutoPilotConfig,
    | 'enabled' | 'capital' | 'daily_profit_target' | 'daily_loss_limit'
    | 'max_concurrent_positions' | 'max_position_size_pct' | 'take_profit_pct'
    | 'stop_loss_pct' | 'min_price' | 'max_price' | 'min_change_pct'
    | 'min_volume_ratio' | 'max_candidates' | 'use_llm' | 'llm_min_confidence'
    | 'force_flat_minutes_before_close' | 'data_provider'
  >
>

export interface AutoPilotStatus {
  market_type: MarketType
  enabled: boolean
  status: string
  capital: number
  daily_profit_target: number
  realized_pnl_today: number
  progress_pct: number
  target_hit: boolean
  halted: boolean
  trades_today: number
  open_positions: number
  last_run_at: string | null
}

export interface AutoPilotTrade {
  id: string
  market_type: MarketType
  ticker: string
  trading_day: string
  entry_time: string
  entry_price: number
  quantity: number
  stop_price: number
  take_profit_price: number
  momentum_score: number | null
  llm_confidence: number | null
  entry_reason: string | null
  status: string
  exit_time: string | null
  exit_price: number | null
  exit_reason: string | null
  realized_pnl: number | null
  realized_pnl_pct: number | null
}

export interface AutoPilotReport {
  id: string
  market_type: MarketType
  trading_day: string
  capital: number
  daily_profit_target: number
  realized_pnl: number
  target_met: boolean
  return_pct: number
  num_trades: number
  num_winning: number
  num_losing: number
  win_rate: number
  best_trade_pnl: number | null
  worst_trade_pnl: number | null
  summary: string | null
}

export interface ProvidersInfo {
  providers: string[]
  active: string
}

export async function getProviders(): Promise<ProvidersInfo> {
  const res = await apiClient.get<ProvidersInfo>('/autopilot/providers')
  return res.data
}

export async function getConfig(market: MarketType): Promise<AutoPilotConfig> {
  const res = await apiClient.get<AutoPilotConfig>(`/autopilot/${market}/config`)
  return res.data
}

export async function updateConfig(market: MarketType, body: AutoPilotConfigUpdate): Promise<AutoPilotConfig> {
  const res = await apiClient.put<AutoPilotConfig>(`/autopilot/${market}/config`, body)
  return res.data
}

export async function setEnabled(market: MarketType, enabled: boolean): Promise<AutoPilotConfig> {
  const res = await apiClient.post<AutoPilotConfig>(`/autopilot/${market}/enable?enabled=${enabled}`)
  return res.data
}

export async function flatten(market: MarketType): Promise<AutoPilotStatus> {
  const res = await apiClient.post<AutoPilotStatus>(`/autopilot/${market}/flatten`)
  return res.data
}

export async function getStatus(market: MarketType): Promise<AutoPilotStatus> {
  const res = await apiClient.get<AutoPilotStatus>(`/autopilot/${market}/status`)
  return res.data
}

export async function getTrades(market: MarketType, limit = 100): Promise<AutoPilotTrade[]> {
  const res = await apiClient.get<AutoPilotTrade[]>(`/autopilot/${market}/trades?limit=${limit}`)
  return res.data
}

export async function getReports(market: MarketType, limit = 60): Promise<AutoPilotReport[]> {
  const res = await apiClient.get<AutoPilotReport[]>(`/autopilot/${market}/reports?limit=${limit}`)
  return res.data
}
