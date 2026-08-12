import { create } from 'zustand'

type Theme = 'dark' | 'light'

const STORAGE_KEY = 'stockiq-theme'

/** Apply the theme class to <html> and persist to localStorage. */
function applyTheme(theme: Theme): void {
  const root = document.documentElement
  if (theme === 'light') {
    root.classList.add('light')
    root.classList.remove('dark')
  } else {
    root.classList.remove('light')
    root.classList.add('dark')
  }
  localStorage.setItem(STORAGE_KEY, theme)
}

/** Read the saved theme from localStorage, falling back to 'dark'. */
function getInitialTheme(): Theme {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch {
    // localStorage unavailable (SSR, private browsing restriction, etc.)
  }
  return 'dark'
}

interface ThemeState {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

const initialTheme = getInitialTheme()
// Apply immediately so the correct class is on <html> before first render.
applyTheme(initialTheme)

export const useThemeStore = create<ThemeState>((set) => ({
  theme: initialTheme,

  toggleTheme: () =>
    set((state) => {
      const next: Theme = state.theme === 'dark' ? 'light' : 'dark'
      applyTheme(next)
      return { theme: next }
    }),

  setTheme: (theme: Theme) => {
    applyTheme(theme)
    set({ theme })
  },
}))
