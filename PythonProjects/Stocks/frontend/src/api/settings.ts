import apiClient from './client'

// --- Types ---

export interface AppSettings {
  app_env: string
  api_version: string
  log_level: string
  feature_flags: {
    real_time_streaming: boolean
    deep_learning: boolean
    alternative_data: boolean
  }
}

export type FeatureFlagPatch = Partial<AppSettings['feature_flags']>

// --- API functions ---

export async function getSettings(): Promise<AppSettings> {
  const res = await apiClient.get<AppSettings>('/settings')
  return res.data
}

export async function patchSettings(patch: FeatureFlagPatch): Promise<AppSettings> {
  const res = await apiClient.patch<AppSettings>('/settings', patch)
  return res.data
}
