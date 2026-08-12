import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthUser {
  id: string
  name: string
  email: string
  role: string
}

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  isAuthenticated: boolean
  setAuth: (user: AuthUser, token: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      setAuth: (user, accessToken) => {
        localStorage.setItem('stockiq-token', accessToken)
        set({ user, accessToken, isAuthenticated: true })
      },
      clearAuth: () => {
        localStorage.removeItem('stockiq-token')
        set({ user: null, accessToken: null, isAuthenticated: false })
      },
    }),
    {
      name: 'stockiq-auth',
      partialize: (state) => ({ user: state.user, accessToken: state.accessToken }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isAuthenticated = !!state.accessToken
          if (state.accessToken) {
            localStorage.setItem('stockiq-token', state.accessToken)
          }
        }
      },
    }
  )
)
