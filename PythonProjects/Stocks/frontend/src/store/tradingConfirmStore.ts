import { create } from 'zustand'
import type { RealOrderRequest } from '../api/trading'

export type { RealOrderRequest }

interface RealTradeConfirmState {
  isOpen: boolean
  pendingRealOrder: RealOrderRequest | null
  expectedConfirmText: string | null
  isSubmitting: boolean

  openConfirmation: (order: RealOrderRequest) => void
  closeConfirmation: () => void
  setSubmitting: (v: boolean) => void
}

export const useTradingConfirmStore = create<RealTradeConfirmState>((set) => ({
  isOpen: false,
  pendingRealOrder: null,
  expectedConfirmText: null,
  isSubmitting: false,
  openConfirmation: (order) => set({
    isOpen: true,
    pendingRealOrder: order,
    expectedConfirmText: `${order.ticker} ${order.quantity} ${order.side.toUpperCase()}`,
  }),
  closeConfirmation: () => set({
    isOpen: false,
    pendingRealOrder: null,
    expectedConfirmText: null,
    isSubmitting: false,
  }),
  setSubmitting: (v) => set({ isSubmitting: v }),
}))
