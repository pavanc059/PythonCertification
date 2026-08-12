import apiClient from './client'

export interface InsiderTransaction {
  name: string
  title: string
  shares: number
  change: number
  price: number
  action: 'BUY' | 'SELL'
  date: string
  filing_date: string
}

export interface InsiderSummary {
  total_buys: number
  total_sells: number
  net_shares: number
  signal: 'bullish' | 'bearish' | 'neutral'
}

export interface InsiderData {
  ticker: string
  transactions: InsiderTransaction[]
  summary: InsiderSummary
}

export interface HolderItem {
  holder: string
  pct: number
  value: number
}

export interface GuruHolding {
  guru: string
  ticker: string
  quarter: string
  source: string
  filing_url: string
}

export interface GuruData {
  ticker: string
  company: string
  institutional_holders: HolderItem[]
  fund_holders: HolderItem[]
  guru_13f: GuruHolding[]
}

export async function getInsiders(ticker: string): Promise<InsiderData> {
  const res = await apiClient.get<InsiderData>(`/ai/insiders/${ticker}`)
  return res.data
}

export async function getGurus(ticker: string): Promise<GuruData> {
  const res = await apiClient.get<GuruData>(`/ai/gurus/${ticker}`)
  return res.data
}

/**
 * Stream an AI analysis via Server-Sent Events.
 * Calls onChunk for each text chunk, onDone when complete, onError on failure.
 */
export function streamAnalysis(
  ticker: string,
  question: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): AbortController {
  const ctrl = new AbortController()
  const token = localStorage.getItem('stockiq-token') ?? ''

  // Use the same /api proxy path that apiClient uses so Nginx routes it correctly
  const baseUrl = '/api'

  fetch(`${baseUrl}/ai/analyze/${ticker}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const text = await res.text()
        onError(`Server error ${res.status}: ${text}`)
        return
      }
      const reader = res.body?.getReader()
      if (!reader) { onError('No response body'); return }
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') { onDone(); return }
          try {
            const parsed = JSON.parse(data)
            if (parsed.error) { onError(parsed.error); return }
            if (parsed.text) onChunk(parsed.text)
          } catch { /* ignore malformed line */ }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(String(err))
    })

  return ctrl
}

export function streamInsiderAnalysis(  ticker: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): AbortController {
  const ctrl = new AbortController()
  const token = localStorage.getItem('stockiq-token') ?? ''
  const baseUrl = '/api'

  fetch(`${baseUrl}/ai/insiders/${ticker}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok) { onError(`Server error ${res.status}`); return }
      const reader = res.body?.getReader()
      if (!reader) { onError('No response body'); return }
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') { onDone(); return }
          try {
            const parsed = JSON.parse(data)
            if (parsed.error) { onError(parsed.error); return }
            if (parsed.text) onChunk(parsed.text)
          } catch { /* ignore */ }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(String(err))
    })

  return ctrl
}

/**
 * Stream a buyers-focused AI analysis via POST /ai/buyers/{ticker}.
 * Uses 6 parallel Tavily queries + insider filings + institutional data.
 */
export function streamBuyersAnalysis(
  ticker: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): AbortController {
  const ctrl = new AbortController()
  const token = localStorage.getItem('stockiq-token') ?? ''
  const baseUrl = '/api'

  fetch(`${baseUrl}/ai/buyers/${ticker}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok) { onError(`Server error ${res.status}`); return }
      const reader = res.body?.getReader()
      if (!reader) { onError('No response body'); return }
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') { onDone(); return }
          try {
            const parsed = JSON.parse(data)
            if (parsed.error) { onError(parsed.error); return }
            if (parsed.text) onChunk(parsed.text)
          } catch { /* ignore */ }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(String(err))
    })

  return ctrl
}

// ─── Guru daily trades ────────────────────────────────────────────────────────

export interface GuruTrade {
  guru: string
  ticker: string
  action: 'BUY' | 'SELL' | 'FILED' | 'NEWS'
  shares: number | null
  price: number | null
  date: string
  insider_name: string
  source: string
  confidence: 'high' | 'medium' | 'low'
  title?: string
  content?: string
}

export interface GuruTradesResponse {
  trades: GuruTrade[]
  days: number
}

export async function getGuruTrades(days = 7): Promise<GuruTradesResponse> {
  const res = await apiClient.get<GuruTradesResponse>('/ai/guru-trades', {
    params: { days },
  })
  return res.data
}
