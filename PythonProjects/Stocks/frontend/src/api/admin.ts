import apiClient from './client'
import type { ActivityEvent } from './activity'

export interface AdminUser {
  id: string
  email: string
  name: string
  role: 'user' | 'admin'
  is_active: boolean
  created_at: string
  last_login_at: string | null
  trade_count: number
}

export interface AdminUsersResponse {
  total: number
  offset: number
  limit: number
  users: AdminUser[]
}

export interface AdminActivityEvent extends ActivityEvent {
  user_email: string
}

export interface AdminActivityResponse {
  total: number
  offset: number
  limit: number
  items: AdminActivityEvent[]
}

export interface PlatformStats {
  users: { total: number; active: number; admins: number }
  orders: { total: number; filled: number }
  automation: { active_bots: number; active_autopilots: number }
  activity: { total_events: number }
}

export async function getAdminUsers(params?: {
  limit?: number
  offset?: number
}): Promise<AdminUsersResponse> {
  const res = await apiClient.get<AdminUsersResponse>('/admin/users', { params })
  return res.data
}

export async function setUserRole(
  userId: string,
  role: 'user' | 'admin',
): Promise<AdminUser> {
  const res = await apiClient.patch<AdminUser>(`/admin/users/${userId}/role`, { role })
  return res.data
}

export async function getAdminActivity(params?: {
  limit?: number
  offset?: number
  user_id?: string
  category?: string
  event_type?: string
}): Promise<AdminActivityResponse> {
  const res = await apiClient.get<AdminActivityResponse>('/admin/activity', { params })
  return res.data
}

export async function getPlatformStats(): Promise<PlatformStats> {
  const res = await apiClient.get<PlatformStats>('/admin/stats')
  return res.data
}
