import apiClient from './client'

// --- Request types ---

export interface RegisterRequest {
  name: string
  email: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

// --- Response types ---

export interface AuthUser {
  id: string
  name: string
  email: string
  role: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

// --- API functions ---

export async function registerUser(data: RegisterRequest): Promise<AuthResponse> {
  const res = await apiClient.post<AuthResponse>('/auth/register', data)
  return res.data
}

export async function loginUser(data: LoginRequest): Promise<AuthResponse> {
  const res = await apiClient.post<AuthResponse>('/auth/login', data)
  return res.data
}

export async function logoutUser(): Promise<void> {
  await apiClient.post('/auth/logout')
}

export async function refreshToken(): Promise<AuthResponse> {
  const res = await apiClient.post<AuthResponse>('/auth/refresh')
  return res.data
}
