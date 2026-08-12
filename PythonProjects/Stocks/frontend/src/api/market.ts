import apiClient from './client'

// --- Response types ---

export interface Quote {
  ticker: string
  price: number
  change: number
  change_pct: number
  volume: number
  day_high: number
  day_low: number
  company_name: string
  // Extended fields (Requirements: 11.4, 11.5)
  week_52_high?: number | null
  week_52_low?: number | null
  market_cap?: number | null
  pe_ratio?: number | null
  sector?: string | null
}

export interface OHLCV {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface ChartData {
  ticker: string
  period: string
  interval: string
  data: OHLCV[]
}

export interface Prediction {
  ticker: string
  prediction: number
  confidence: number
  direction: 'up' | 'down' | 'neutral' | 'bullish' | 'bearish'
  factors?: Record<string, number>
  // Technical signals (Requirements: 11.3)
  rsi_14?: number | null
  macd_signal?: 'bullish' | 'bearish' | 'neutral' | null
  sma_cross?: 'golden_cross' | 'death_cross' | 'neutral' | null
}

export interface TopMover {
  ticker: string
  name: string
  price_change_pct: number
  current_price: number
  volume: number
  avg_volume: number
  sector: string
  has_unusual_volume: boolean
}

export interface MoversResponse {
  gainers: TopMover[]
  losers: TopMover[]
}

export interface NewsArticle {
  id: string
  title: string
  source: string
  published_at: string        // ISO 8601
  sentiment_score: number     // [-1, 1]
  category: string
  is_breaking: boolean
  summary: string
  tickers: string[]
  url: string
}

export interface EnsemblePrediction {
  ticker: string
  category: 'Strong Buy' | 'Buy' | 'Hold' | 'Sell' | 'Strong Sell'
  confidence: number          // [0, 1]
  expected_return: number     // decimal, e.g. 0.035 = +3.5%
  lower_bound: number
  upper_bound: number
  is_low_confidence: boolean
  // Live prediction enrichment fields
  reason?: string | null
  rsi_14?: number | null
  macd_histogram?: number | null
  sma_cross?: 'golden_cross' | 'death_cross' | 'neutral' | null
  momentum_30d?: number | null
  computed_at?: string | null
}

export interface PennyStock {
  ticker: string
  price: number
  price_change_pct: number
  volume: number
  avg_volume: number
  volume_ratio: number
  momentum_score: number      // [0, 100]
  risk_level: 'low' | 'medium' | 'high' | 'extreme'
  sector: string
  catalyst: string
  suspicion_score: number     // [0, 1]
  recommendation: string
  insider_net: number
  insider_buys: number
  insider_sells: number
}

export interface MarketSnapshot {
  sp500_change_pct: number
  nasdaq_change_pct: number
  vix: number
}

export interface EarningsHistoryItem {
  quarter: string
  eps_estimate: number | null
  eps_actual: number | null
  surprise_pct: number | null
}

export interface EarningsData {
  ticker: string
  next_earnings_date: string | null
  next_earnings_time: string | null
  eps_estimate: number | null
  history: EarningsHistoryItem[]
}

// --- API functions ---

export async function getQuote(ticker: string): Promise<Quote> {
  const res = await apiClient.get<Quote>(`/market/quote/${ticker}`)
  return res.data
}

export async function getChart(
  ticker: string,
  period = '1mo',
  interval = '1d'
): Promise<ChartData> {
  const res = await apiClient.get<ChartData>(`/market/chart/${ticker}`, {
    params: { period, interval },
  })
  return res.data
}

export async function getPrediction(ticker: string): Promise<Prediction> {
  const res = await apiClient.get<Prediction>(`/market/predict/${ticker}`)
  return res.data
}

export async function getMovers(): Promise<MoversResponse> {
  const res = await apiClient.get<MoversResponse>('/market/movers')
  return res.data
}

export async function getNews(params?: {
  limit?: number
  offset?: number
  ticker?: string
  sentiment?: 'positive' | 'neutral' | 'negative'
  category?: string
}): Promise<NewsArticle[]> {
  const res = await apiClient.get<NewsArticle[]>('/market/news', { params })
  return res.data
}

export async function getTickerNews(ticker: string, limit = 3): Promise<NewsArticle[]> {
  const res = await apiClient.get<NewsArticle[]>(`/market/news/${ticker}`, {
    params: { limit },
  })
  return res.data
}

export async function getPredictions(tickers?: string[]): Promise<EnsemblePrediction[]> {
  const res = await apiClient.get<EnsemblePrediction[]>('/market/predictions', {
    params: tickers && tickers.length > 0 ? { tickers: tickers.join(',') } : undefined,
  })
  return res.data
}

export async function getPennyStocks(): Promise<PennyStock[]> {
  const res = await apiClient.get<PennyStock[]>('/market/penny-stocks')
  return res.data
}

export async function getSnapshot(): Promise<MarketSnapshot> {
  const res = await apiClient.get<MarketSnapshot>('/market/snapshot')
  return res.data
}

export async function getEarnings(ticker: string): Promise<EarningsData> {
  const res = await apiClient.get<EarningsData>(`/market/earnings/${ticker}`)
  return res.data
}

export interface InstitutionalHolder {
  holder: string
  shares: number | null
  pct_held: number | null
  value: number | null
  date_reported: string | null
  type: 'institution' | 'fund'
}

export interface InstitutionalData {
  ticker: string
  holders: InstitutionalHolder[]
}

export async function getInstitutional(ticker: string, limit = 10): Promise<InstitutionalData> {
  const res = await apiClient.get<InstitutionalData>(`/market/institutional/${ticker}`, {
    params: { limit },
  })
  return res.data
}

export async function getTopInstitutional(tickers: string[], limit = 10): Promise<InstitutionalData[]> {
  return Promise.all(tickers.map((t) => getInstitutional(t, limit)))
}
