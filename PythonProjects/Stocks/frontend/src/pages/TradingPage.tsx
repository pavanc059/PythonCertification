import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { formatCurrency } from '@/lib/formatters'
import { getAccount, getOrders, resetAccount } from '@/api/trading'
import { getPositions, getPortfolioHistory } from '@/api/portfolio'
import { PageTransition } from '@/components/common/PageTransition'
import { PaperTradingBanner } from '@/components/trading/PaperTradingBanner'
import { OrderTicket } from '@/components/trading/OrderTicket'
import { PositionsTable } from '@/components/positions/PositionsTable'
import { PendingOrdersTable } from '@/components/trading/PendingOrdersTable'
import { TradeHistoryTable } from '@/components/positions/TradeHistoryTable'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { OrderSide } from '@/api/trading'

// ---------------------------------------------------------------------------
// Tab types
// ---------------------------------------------------------------------------

type Tab = 'positions' | 'pending' | 'history'

const TABS: { id: Tab; label: string }[] = [
  { id: 'positions', label: 'Positions' },
  { id: 'pending', label: 'Pending Orders' },
  { id: 'history', label: 'Trade History' },
]

// ---------------------------------------------------------------------------
// Account summary skeleton
// ---------------------------------------------------------------------------

function SummarySkeletonSpan() {
  return (
    <span className="inline-block h-4 w-24 bg-muted/50 rounded animate-pulse align-middle" />
  )
}

// ---------------------------------------------------------------------------
// TradingPage
// ---------------------------------------------------------------------------

export default function TradingPage() {
  const queryClient = useQueryClient()

  // ── Tab state ──
  const [activeTab, setActiveTab] = useState<Tab>('positions')

  // ── OrderTicket state ──
  const [orderTicketOpen, setOrderTicketOpen] = useState(false)
  const [orderTicketTicker, setOrderTicketTicker] = useState<string | undefined>(undefined)
  const [orderTicketSide, setOrderTicketSide] = useState<OrderSide>('buy')

  // ── Reset account dialog state ──
  const [resetDialogOpen, setResetDialogOpen] = useState(false)
  const [isResetting, setIsResetting] = useState(false)

  // ---------------------------------------------------------------------------
  // Data queries
  // ---------------------------------------------------------------------------

  const { data: account, isLoading: accountLoading } = useQuery({
    queryKey: ['account'],
    queryFn: getAccount,
    refetchInterval: 30_000,
  })

  const { data: positions = [], isLoading: positionsLoading } = useQuery({
    queryKey: ['positions'],
    queryFn: getPositions,
    refetchInterval: 30_000,
  })

  const { data: orders = [], isLoading: ordersLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: getOrders,
    refetchInterval: 30_000,
  })

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['history'],
    queryFn: getPortfolioHistory,
    refetchInterval: 30_000,
  })

  // ---------------------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------------------

  const trades = history?.closed_trades ?? []

  // Total unrealized P&L from positions
  const totalUnrealizedPnl = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0)
  const totalRealizedPnl = history?.total_realized_pnl ?? 0
  const totalPnl = totalUnrealizedPnl + totalRealizedPnl

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleOpenNewOrder = () => {
    setOrderTicketTicker(undefined)
    setOrderTicketSide('buy')
    setOrderTicketOpen(true)
  }

  const handleSellFromPositions = (ticker: string) => {
    setOrderTicketTicker(ticker)
    setOrderTicketSide('sell')
    setOrderTicketOpen(true)
  }

  const handleCloseOrderTicket = () => {
    setOrderTicketOpen(false)
  }

  const handleResetAccount = async () => {
    setIsResetting(true)
    try {
      await resetAccount()
      // Invalidate all relevant queries
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['account'] }),
        queryClient.invalidateQueries({ queryKey: ['positions'] }),
        queryClient.invalidateQueries({ queryKey: ['orders'] }),
        queryClient.invalidateQueries({ queryKey: ['history'] }),
      ])
      toast.success('Account reset to $100,000')
    } catch {
      toast.error('Failed to reset account. Please try again.')
    } finally {
      setIsResetting(false)
    }
  }

  const handleOrderCancelSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['orders'] })
    queryClient.invalidateQueries({ queryKey: ['account'] })
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <PageTransition>
      <div className="relative flex flex-col gap-4 p-4 md:p-6 pb-24 min-h-full">

        {/* ── Paper Trading Banner ── */}
        <PaperTradingBanner />

        {/* ── Account Summary Strip ── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <AccountSummaryCard
            label="Cash"
            value={accountLoading ? null : account ? formatCurrency(account.cash) : '—'}
          />
          <AccountSummaryCard
            label="Buying Power"
            value={accountLoading ? null : account ? formatCurrency(account.buying_power) : '—'}
          />
          <AccountSummaryCard
            label="Portfolio Value"
            value={accountLoading ? null : account ? formatCurrency(account.portfolio_value) : '—'}
          />
          <AccountSummaryCard
            label="Total P&L"
            value={accountLoading && historyLoading ? null : formatCurrency(totalPnl)}
            pnl={accountLoading && historyLoading ? undefined : totalPnl}
          />
        </div>

        {/* ── Tabs + Reset Button ── */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex rounded-md border border-border overflow-hidden">
            {TABS.map(tab => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap',
                  activeTab === tab.id
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card text-muted-foreground hover:bg-muted/50'
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Reset Account button — pushed to the right */}
          <button
            type="button"
            onClick={() => setResetDialogOpen(true)}
            disabled={isResetting}
            className={cn(
              'ml-auto flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium',
              'border border-border bg-card text-muted-foreground',
              'hover:bg-destructive/10 hover:text-destructive hover:border-destructive/40',
              'transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset Account
          </button>
        </div>

        {/* ── Tab Content ── */}
        <div className="flex-1">
          {activeTab === 'positions' && (
            <PositionsTable
              positions={positions}
              onSell={handleSellFromPositions}
              isLoading={positionsLoading}
            />
          )}

          {activeTab === 'pending' && (
            <PendingOrdersTable
              orders={orders}
              onCancelSuccess={handleOrderCancelSuccess}
              isLoading={ordersLoading}
            />
          )}

          {activeTab === 'history' && (
            <TradeHistoryTable
              trades={trades}
              isLoading={historyLoading}
            />
          )}
        </div>
      </div>

      {/* ── Floating "New Order" FAB ── */}
      <button
        type="button"
        onClick={handleOpenNewOrder}
        aria-label="New Order"
        className={cn(
          'fixed bottom-6 right-6 z-40',
          'flex items-center gap-2 px-4 py-3 rounded-full shadow-lg',
          'bg-primary text-primary-foreground',
          'hover:bg-primary/90 active:scale-95 transition-all',
          'text-sm font-semibold'
        )}
      >
        <Plus className="h-4 w-4" />
        New Order
      </button>

      {/* ── OrderTicket (page-level) ── */}
      <OrderTicket
        isOpen={orderTicketOpen}
        onClose={handleCloseOrderTicket}
        defaultTicker={orderTicketTicker}
        defaultSide={orderTicketSide}
      />

      {/* ── Reset Account Confirm Dialog ── */}
      <ConfirmDialog
        open={resetDialogOpen}
        onOpenChange={setResetDialogOpen}
        title="Reset Paper Trading Account"
        description="This will reset your account to $100,000 and clear all positions and orders. This action cannot be undone."
        confirmLabel="Reset Account"
        cancelLabel="Cancel"
        onConfirm={handleResetAccount}
        destructive
      />
    </PageTransition>
  )
}

// ---------------------------------------------------------------------------
// Account summary card
// ---------------------------------------------------------------------------

interface AccountSummaryCardProps {
  label: string
  value: string | null
  pnl?: number
}

function AccountSummaryCard({ label, value, pnl }: AccountSummaryCardProps) {
  const valueClass =
    pnl !== undefined
      ? pnl > 0
        ? 'text-gain'
        : pnl < 0
          ? 'text-loss'
          : 'text-foreground'
      : 'text-foreground'

  return (
    <div className="bg-card border border-border rounded-lg px-4 py-3 flex flex-col gap-1">
      <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
      {value === null ? (
        <SummarySkeletonSpan />
      ) : (
        <span className={cn('text-base font-semibold', valueClass)}>{value}</span>
      )}
    </div>
  )
}
