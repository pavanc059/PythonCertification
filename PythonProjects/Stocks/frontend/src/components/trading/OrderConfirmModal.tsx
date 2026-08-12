import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { formatCurrency } from '@/lib/formatters'
import { placeOrder } from '@/api/trading'
import type { PlaceOrderRequest } from '@/api/trading'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface OrderConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  order: PlaceOrderRequest | null
  currentPrice?: number | null
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ORDER_TYPE_LABELS: Record<string, string> = {
  market: 'Market',
  limit: 'Limit',
  stop: 'Stop',
  stop_limit: 'Stop-Limit',
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function OrderConfirmModal({
  isOpen,
  onClose,
  order,
  currentPrice,
}: OrderConfirmModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const queryClient = useQueryClient()

  // Estimated value calculation — mirrors OrderTicket logic
  const estimationPrice: number | null =
    order?.order_type === 'limit' || order?.order_type === 'stop_limit'
      ? order.limit_price ?? null
      : currentPrice ?? null

  const estimatedValue: number | null =
    order && order.quantity > 0 && estimationPrice !== null
      ? order.quantity * estimationPrice
      : null

  const handleConfirm = async () => {
    if (!order) return

    setIsSubmitting(true)
    try {
      const response = await placeOrder(order)

      if (response.status === 'filled') {
        const action = order.side === 'buy' ? 'Bought' : 'Sold'
        const priceStr =
          response.filled_price != null
            ? ` @ ${formatCurrency(response.filled_price)}`
            : ''
        toast.success(
          `Order Filled — ${action} ${order.quantity} ${order.ticker}${priceStr}`
        )
        // Invalidate caches after a fill
        queryClient.invalidateQueries({ queryKey: ['positions'] })
        queryClient.invalidateQueries({ queryKey: ['orders'] })
        queryClient.invalidateQueries({ queryKey: ['account'] })
      } else if (response.status === 'pending') {
        toast.info(
          `Order Pending — ${order.quantity} ${order.ticker} ${ORDER_TYPE_LABELS[order.order_type]} order queued`
        )
        // Invalidate orders cache so pending list updates
        queryClient.invalidateQueries({ queryKey: ['orders'] })
        queryClient.invalidateQueries({ queryKey: ['account'] })
      } else if (response.status === 'rejected') {
        toast.error(`Order Rejected — ${order.ticker}`)
      }

      onClose()
    } catch (err: unknown) {
      // Extract the most useful error message from Axios / fetch errors
      let message = 'Failed to place order. Please try again.'
      if (err && typeof err === 'object') {
        const axiosErr = err as {
          response?: { data?: { detail?: string; message?: string } }
          message?: string
        }
        const detail = axiosErr.response?.data?.detail ?? axiosErr.response?.data?.message
        if (detail) {
          message = typeof detail === 'string' ? detail : JSON.stringify(detail)
        } else if (axiosErr.message) {
          message = axiosErr.message
        }
      }
      toast.error(`Order Failed — ${message}`)
      // Keep modal open on error so the user can retry
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && order && (
        <>
          {/* Backdrop — sits above the OrderTicket (z-50) */}
          <motion.div
            key="confirm-backdrop"
            className="fixed inset-0 z-60 bg-black/70"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={!isSubmitting ? onClose : undefined}
            aria-hidden="true"
          />

          {/* Dialog panel */}
          <motion.div
            key="confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="order-confirm-title"
            className="fixed left-1/2 top-1/2 z-60 w-full max-w-md -translate-x-1/2 -translate-y-1/2 px-4"
            initial={{ opacity: 0, scale: 0.96, y: '-48%' }}
            animate={{ opacity: 1, scale: 1, y: '-50%' }}
            exit={{ opacity: 0, scale: 0.96, y: '-48%' }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
          >
            <div className="bg-card border border-border rounded-xl shadow-2xl overflow-hidden">
              {/* ── Header ── */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                <h2
                  id="order-confirm-title"
                  className="text-base font-semibold text-foreground"
                >
                  Confirm Order
                </h2>
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  aria-label="Close confirmation"
                  className="text-muted-foreground hover:text-foreground transition-colors rounded-md p-1 disabled:opacity-50"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* ── Order summary ── */}
              <div className="px-5 py-5 space-y-4">
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

                {/* Summary rows */}
                <div className="bg-muted/20 border border-border rounded-lg divide-y divide-border">
                  <SummaryRow label="Order Type" value={ORDER_TYPE_LABELS[order.order_type]} />
                  <SummaryRow label="Quantity" value={`${order.quantity.toLocaleString()} shares`} />
                  {order.limit_price != null && (
                    <SummaryRow label="Limit Price" value={formatCurrency(order.limit_price)} />
                  )}
                  {order.stop_price != null && (
                    <SummaryRow label="Stop Price" value={formatCurrency(order.stop_price)} />
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

                {/* Paper trading note */}
                <p className="text-xs text-muted-foreground text-center">
                  Paper trading — no real commissions
                </p>
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
                  onClick={handleConfirm}
                  disabled={isSubmitting}
                  className={cn(
                    'flex-1 py-2.5 rounded-md text-sm font-semibold transition-colors',
                    'flex items-center justify-center gap-2',
                    order.side === 'buy'
                      ? 'bg-green-600 text-white hover:bg-green-700 disabled:opacity-70'
                      : 'bg-red-600 text-white hover:bg-red-700 disabled:opacity-70',
                    'disabled:cursor-not-allowed'
                  )}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Placing…
                    </>
                  ) : (
                    'Confirm Order'
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
