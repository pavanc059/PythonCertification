import apiClient from './client'

// --- Request types ---

export interface AddWatchlistRequest {
  ticker: string
  alert_price?: number
  list_name?: string
}

// --- Response types ---

export interface WatchlistItem {
  id: string
  ticker: string
  company_name?: string
  alert_price?: number
  list_name: string
  added_at: string
}

// --- API functions ---

export async function getWatchlist(): Promise<WatchlistItem[]> {
  const res = await apiClient.get<WatchlistItem[]>('/watchlist')
  return res.data
}

export async function addToWatchlist(data: AddWatchlistRequest): Promise<WatchlistItem> {
  const res = await apiClient.post<WatchlistItem>('/watchlist/add', data)
  return res.data
}

export async function removeFromWatchlist(ticker: string): Promise<void> {
  await apiClient.delete(`/watchlist/${ticker}`)
}

export async function getWatchlistNames(): Promise<string[]> {
  const res = await apiClient.get<string[]>('/watchlist/lists')
  return res.data
}

export async function createWatchlistList(name: string): Promise<{ name: string }> {
  const res = await apiClient.post<{ name: string }>('/watchlist/lists', { name })
  return res.data
}
