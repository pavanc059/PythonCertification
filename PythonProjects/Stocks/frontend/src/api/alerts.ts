import apiClient from './client'

// --- Response types ---

export interface Alert {
  id: string
  ticker: string
  alert_type: string
  message: string
  severity: 'info' | 'warning' | 'critical'
  timestamp: string // ISO 8601
  is_read: boolean
}

// --- API functions ---

export async function getAlerts(): Promise<Alert[]> {
  const res = await apiClient.get<Alert[]>('/market/alerts')
  return res.data
}

export async function dismissAlert(id: string): Promise<void> {
  await apiClient.delete(`/market/alerts/${id}`)
}

export async function markAllAlertsRead(): Promise<void> {
  await apiClient.post('/market/alerts/read-all')
}
