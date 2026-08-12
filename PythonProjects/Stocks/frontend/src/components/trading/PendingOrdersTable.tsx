import { useState } from 'react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import { cancelOrder } from '@/api/trading'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { Order, OrderStatus } from '@/api/trading'

interface PendingOrdersTableProps {
  orders: Order[]
  onCancelSuccess?: () => void
  isLoading?: boolean
}

function SkeletonRow() {
  return (
    <tr className="even:bg-muted/20">
      {Array.from({ length: 8 }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-muted/50 rounded animate-pulse w-full max-w-[80px]" />
        </td>
      ))}
    </tr>
  )
}

function StatusBadge({ status }: { status: OrderStatus }) {
  const styles: Record<OrderStatus, string> = {
    pending: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    filled: 'bg-green-500/20 text-green-400 border border-green-500/30',
    cancelled: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
    rejected: 'bg-red-500/20 text-red-400 border border-red-500/30',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize',
        styles[status]
      )}
    >
      {status}
    </span>
  )
}

function CancelButton({ order, onSuccess }: { order: Order; onSuccess?: () => void }) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)

  const handleConfirm = async () => {
    setIsCancelling(true)
    try {
      await cancelOrder(order.order_id)
      toast.success(`Order for ${order.ticker} cancelled`)
      onSuccess?.()
    } catch {
      toast.error('Failed to cancel order. Please try again.')
    } finally {
      setIsCancelling(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setDialogOpen(true)}
        disabled={isCancelling}
        className="px-3 py-1 rounded text-xs font-medium bg-muted text-foreground hover:bg-muted/70 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isCancelling ? 'Cancelling…' : 'Cancel'}
      </button>
      <ConfirmDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Cancel Order"
        description={`Are you sure you want to cancel the ${order.side.toUpperCase()} order for ${order.quantity} share(s) of ${order.ticker}?`}
        confirmLabel="Cancel Order"
        cancelLabel="Keep Order"
        onConfirm={handleConfirm}
        destructive
      />
    </>
  )
}

export function PendingOrdersTable({
  orders,
  onCancelSuccess,
  isLoading = false,
}: PendingOrdersTableProps) {
  const pendingOrders = orders.filter(o => o.status === 'pending')

  const thClass = cn(
    'px-4 py-3 text-left text-xs uppercase text-muted-foreground font-medium whitespace-nowrap'
  )

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-0 bg-card border-b border-border">
          <tr>
            <th className={thClass}>Ticker</th>
            <th className={thClass}>Type</th>
            <th className={thClass}>Side</th>
            <th className={thClass}>Qty</th>
            <th className={thClass}>Limit / Stop Price</th>
            <th className={thClass}>Status</th>
            <th className={thClass}>Created</th>
            <th className={thClass}>Action</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </>
          ) : pendingOrders.length === 0 ? (
            <tr>
              <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                No pending orders
              </td>
            </tr>
          ) : (
            pendingOrders.map(order => {
              const limitStopPrice =
                order.limit_price != null
                  ? formatCurrency(order.limit_price)
                  : order.stop_price != null
                  ? formatCurrency(order.stop_price)
                  : '—'

              return (
                <tr
                  key={order.order_id}
                  className="even:bg-muted/20 hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-3 whitespace-nowrap font-semibold">{order.ticker}</td>
                  <td className="px-4 py-3 whitespace-nowrap capitalize">
                    {order.order_type.replace('_', ' ')}
                  </td>
                  <td
                    className={cn(
                      'px-4 py-3 whitespace-nowrap uppercase font-medium',
                      order.side === 'buy' ? 'text-gain' : 'text-loss'
                    )}
                  >
                    {order.side}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">{order.quantity}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{limitStopPrice}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <StatusBadge status={order.status} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-muted-foreground">
                    {formatDateTime(order.created_at)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <CancelButton order={order} onSuccess={onCancelSuccess} />
                  </td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>
    </div>
  )
}
