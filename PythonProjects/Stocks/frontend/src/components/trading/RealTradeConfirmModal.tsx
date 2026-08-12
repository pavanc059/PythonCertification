import { useState, useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Loader2, X, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { formatCurrency } from '@/lib/formatters'
import { useTradingConfirmStore } from '@/store/tradingConfirmStore'
import { confirmRealOrder } from '@/api/trading'
import type { RealOrderRequest } from '@/api/trading'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RealTradeConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  order: RealOrderRequest | null
  onConfirmed: (orderId: string) => void
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ORDER_TYPE_LABELS: Record<string, string> = {
  market: 'Market',
  limit: 'Limit',
  stop: 'Stop',
  stop_loss: 'Stop-Loss',
  stop_limit: 'Stop-Limit',
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RealTradeConfirmModal({
  isOpen,
  onClose,
  order,
  onConfirmed,
}: RealTradeConfirmModalProps) {
  const [inputValue, setInputValue] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const { expectedConfirmText, isSubmitting, setSubmitting, closeConfirmation } =
    useTradingConfirmStore()

  const isMountedRef = useRef(true)
  const inputRef = useRef<HTMLInputElement>(null)

  // Track mount state to guard async state updates after unmount
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Reset local state when modal opens
  useEffect(() => {
    if (isOpen) {
      setInputValue('')
      setErrorMessage(null)
      // Focus the confirmation input after animation settles
      setTimeout(() => inputRef.current?.focus(), 200)
    }
  }, [isOpen])

  // Escape key — disabled while submitting
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isSubmitting) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isSubmitting, onClose])

  // ---------------------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------------------

  const normalizedInput = inputValue.trim().toUpperCase()
  const canSubmit = expectedConfirmText !== null && normalizedInput === expectedConfirmText

  // Estimated value: use limit_price for limit/stop_limit orders (market orders shown as "Market Price")
  const estimationPrice: number | null =
    order?.order_type === 'limit' || order?.order_type === 'stop_limit'
      ? order.limit_price ?? null
      : null

  const estimatedValue: number | null =
    order && estimationPrice !== null && order.quantity > 0
      ? order.quantity * estimationPrice
      : null

  // ---------------------------------------------------------------------------
  // Submit handler
  // ---------------------------------------------------------------------------

  const handleSubmit = async () => {
    if (!order || !canSubmit) return

    setErrorMessage(null)
    setSubmitting(true)

    try {
      const response = await confirmRealOrder({
        ...order,
        confirmation_text: inputValue.trim(),
      })

      closeConfirmation()
      toast.success('Real order submitted')
      onConfirmed(response.order_id)
    } catch (err: unknown) {
      let message = 'An unexpected error occurred. Please try again.'

      if (err && typeof err === 'object') {
        const axiosErr = err as {
          response?: { status?: number; data?: { detail?: string; message?: string } }
          message?: string
        }
        const status = axiosErr.response?.status
        const detail =
          axiosErr.response?.data?.detail ?? axiosErr.response?.data?.message

        if (status === 422) {
          // Inline error — keep modal open
          message =
            typeof detail === 'string'
              ? detail
              : 'Confirmation text did not match. Please check and try again.'
        } else if (detail) {
          message = typeof detail === 'string' ? detail : JSON.stringify(detail)
        } else if (axiosErr.message) {
          message = axiosErr.message
        }
      }

      if (isMountedRef.current) {
        setErrorMessage(message)
      }
    } finally {
      if (isMountedRef.current) {
        setSubmitting(false)
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <AnimatePresence>
      {isOpen && order && (
        <>
          {/* Backdrop — above everything (z-70) */}
          <motion.div
            key="real-confirm-backdrop"
            className="fixed inset-0 z-70 bg-black/75"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={!isSubmitting ? onClose : undefined}
            aria-hidden="true"
          />

          {/* Dialog panel */}
          <motion.div
            key="real-confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="real-confirm-title"
            className="fixed left-1/2 top-1/2 z-70 w-full max-w-md -translate-x-1/2 -translate-y-1/2 px-4"
            initial={{ opacity: 0, scale: 0.96, y: '-48%' }}
            animate={{ opacity: 1, scale: 1, y: '-50%' }}
            exit={{ opacity: 0, scale: 0.96, y: '-48%' }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
          >
            <div className="bg-card border border-border rounded-xl shadow-2xl overflow-hidden">

              {/* ── Amber warning header band ── */}
              <div className="bg-amber-600 px-5 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-white shrink-0" />
                  <h2
                    id="real-confirm-title"
                    className="text-sm font-bold text-white uppercase tracking-wider"
                  >
                    ⚠ REAL MONEY TRADE
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  aria-label="Close confirmation"
                  className="text-white/80 hover:text-white transition-colors rounded-md p-1 disabled:opacity-50"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* ── Body ── */}
              <div className="px-5 py-5 space-y-5">

                {/* Ticker + side badge */}
                <div className="flex items-center justify-between">
                  <span className="text-xl font-bold text-foreground">{order.ticker}</span>
                  <span
                    className={cn(
                      'px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider',
                      order.side === 'buy'
                        ? 'bg-green-600/20 text-green-400 border border-green-600/40'
                        : 'bg-red-600/20 text-red-400 border border-red-600/40'
                    )}
                  >
                    {order.side === 'buy' ? 'BUY' : 'SELL'}
                  </span>
                </div>

                {/* Order summary rows */}
                <div className="bg-muted/20 border border-border rounded-lg divide-y divide-border">
                  <SummaryRow
                    label="Order Type"
                    value={ORDER_TYPE_LABELS[order.order_type] ?? order.order_type}
                  />
                  <SummaryRow
                    label="Quantity"
                    value={`${order.quantity.toLocaleString()} shares`}
                  />
                  {order.limit_price != null && (
                    <SummaryRow
                      label="Limit Price"
                      value={formatCurrency(order.limit_price)}
                    />
                  )}
                  {order.stop_price != null && (
                    <SummaryRow
                      label="Stop Price"
                      value={formatCurrency(order.stop_price)}
                    />
                  )}
                  <SummaryRow
                    label="Estimated Value"
                    value={
                      estimatedValue !== null
                        ? formatCurrency(estimatedValue)
                        : order.order_type === 'market'
                          ? 'Market Price'
                          : '—'
                    }
                    highlight
                  />
                </div>

                {/* Disclaimer */}
                <div className="bg-amber-600/10 border border-amber-600/30 rounded-lg px-4 py-3">
                  <p className="text-sm text-amber-400 font-medium">
                    This will place a REAL order with REAL money. This action cannot be undone.
                  </p>
                </div>

                {/* Typed confirmation input */}
                <div className="space-y-2">
                  <label
                    htmlFor="real-confirm-input"
                    className="block text-sm font-medium text-foreground"
                  >
                    Type{' '}
                    <span className="font-mono font-bold text-amber-400">
                      &ldquo;{expectedConfirmText ?? `${order.ticker} ${order.quantity} ${order.side.toUpperCase()}`}&rdquo;
                    </span>{' '}
                    to confirm
                  </label>
                  <input
                    id="real-confirm-input"
                    ref={inputRef}
                    type="text"
                    autoComplete="off"
                    value={inputValue}
                    onChange={(e) => {
                      setInputValue(e.target.value)
                      // Clear error when user starts correcting
                      if (errorMessage) setErrorMessage(null)
                    }}
                    disabled={isSubmitting}
                    className={cn(
                      'w-full px-3 py-2 bg-input border rounded-md text-foreground font-mono',
                      'placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-500/50 text-sm',
                      'disabled:opacity-50 disabled:cursor-not-allowed',
                      errorMessage ? 'border-destructive' : 'border-border'
                    )}
                    placeholder={
                      expectedConfirmText ??
                      `${order.ticker} ${order.quantity} ${order.side.toUpperCase()}`
                    }
                  />
                </div>

                {/* Inline error message */}
                {errorMessage && (
                  <div className="bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-md px-3 py-2">
                    {errorMessage}
                  </div>
                )}
              </div>

              {/* ── Actions ── */}
              <div className="flex items-center gap-3 px-5 pb-5">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className={cn(
                    'flex-1 py-2.5 rounded-md text-sm font-medium transition-colors',
                    'bg-secondary text-secondary-foreground hover:bg-secondary/80',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!canSubmit || isSubmitting}
                  className={cn(
                    'flex-1 py-2.5 rounded-md text-sm font-semibold transition-colors',
                    'flex items-center justify-center gap-2',
                    canSubmit && !isSubmitting
                      ? 'bg-amber-600 text-white hover:bg-amber-700'
                      : 'bg-muted text-muted-foreground cursor-not-allowed opacity-50',
                    'disabled:cursor-not-allowed'
                  )}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Submitting…
                    </>
                  ) : (
                    'Confirm Real Order'
                  )}
                </button>
              </div>

            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// ---------------------------------------------------------------------------
// Internal helper component
// ---------------------------------------------------------------------------

function SummaryRow({
  label,
  value,
  highlight = false,
}: {
  label: string
  value: string
  highlight?: boolean
}) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span
        className={cn(
          'text-sm font-medium',
          highlight ? 'text-foreground font-semibold' : 'text-foreground'
        )}
      >
        {value}
      </span>
    </div>
  )
}
