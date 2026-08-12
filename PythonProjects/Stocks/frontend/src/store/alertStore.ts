import { create } from 'zustand'

interface AlertState {
  unreadCount: number
  setUnreadCount: (count: number) => void
  decrementUnread: () => void
  clearUnread: () => void
}

export const useAlertStore = create<AlertState>()((set) => ({
  unreadCount: 0,
  setUnreadCount: (count: number) => set({ unreadCount: count }),
  decrementUnread: () =>
    set((state) => ({ unreadCount: Math.max(0, state.unreadCount - 1) })),
  clearUnread: () => set({ unreadCount: 0 }),
}))
