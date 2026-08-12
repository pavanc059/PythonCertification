import apiClient from './client'

export interface ActivityEvent {
  id: string
  user_id: string
  category: string
  event_type: string
  description: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface ActivityFeedResponse {
  total: number
  offset: number
  limit: number
  items: ActivityEvent[]
}

export async function getActivityFeed(params?: {
  limit?: number
  offset?: number
  category?: string
}): Promise<ActivityFeedResponse> {
  const res = await apiClient.get<ActivityFeedResponse>('/activity', { params })
  return res.data
}
