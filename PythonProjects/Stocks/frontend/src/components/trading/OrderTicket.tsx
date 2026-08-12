import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { formatCurrency } from '@/lib/formatters'
import { getQuote } from '@/api/market'
import { getAccount } from '@/api/trading'
import { getPositions } from '@/api/portfolio'
import type { OrderSide, OrderType, PlaceOrderRequest, RealOrderRequest } from '@/api/trading'
import { OrderConfirmModal } from './OrderConfirmModal'
import { RealTradeConfirmModal } from './RealTradeConfirmModal'
import { useTradingConfirmStore } from '@/store/tradingConfirmStore'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface OrderTicketProps {
  isOpen: boolean
  onClose: () => void
  defaultTicker?: string
  defaultSide?: OrderSide
  isRealMoney?: boolean
}

const ORDER_TYPES: { value: OrderType; label: string }[] = [
  { value: 'market', label: 'Market' },
  { value: 'limit', label: 'Limit' },
  { value: 'stop', label: 'Stop' },
  { value: 'stop_limit', label: 'Stop-Limit' },
]

// ---------------------------------------------------------------------------
// Zod schema (base — cross-field validation done in handleSubmit)
// ---------------------------------------------------------------------------

const orderSchema = z.object({
  ticker: z
    .string()
    .min(1, 'Ticker is required')
    .max(5, 'Ticker must be 1–5 characters')
    .transform((v) => v.toUpperCase().trim()),
  quantity: z
    .number()
    .int('Must be a whole number')
    .positive('Must be greater than 0'),
  limit_price: z.number().positive('Must be > 0').optional(),
  stop_price: z.number().positive('Must be > 0').optional(),
})

type OrderFormValues = z.infer<typeof orderSchema>

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function OrderTicket({
  isOpen,
  onClose,
  defaultTicker = '',
  defaultSide = 'buy',
  isRealMoney = false,
}: OrderTicketProps) {
  const [side, setSide] = useState<OrderSide>(defaultSide)
  const [orderType, setOrderType] = useState<OrderType>('market')
  const [crossFieldError, setCrossFieldError] = useState<string | null>(null)
  const [pendingOrder, setPendingOrder] = useState<PlaceOrderRequest | null>(null)

  const { isOpen: isRealConfirmOpen, openConfirmation, closeConfirmation, pendingRealOrder } = useTradingConfirmStore()

  const tickerInputRef = useRef<HTMLInputElement>(null)

  // Sync side when prop changes (e.g., opened from a Buy/Sell button)
  useEffect(() => {
    setSide(defaultSide)
  }, [defaultSide, isOpen])

  // Focus ticker input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => tickerInputRef.current?.focus(), 320) // after slide-in
    }
  }, [isOpen])

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    formState: { errors },
  } = useForm<OrderFormValues>({
    resolver: zodResolver(orderSchema),
    defaultValues: {
      ticker: defaultTicker.toUpperCase(),
      quantity: undefined,
      limit_price: undefined,
      stop_price: undefined,
    },
  })

  // Reset form values when panel re-opens
  useEffect(() => {
    if (isOpen) {
      reset({
        ticker: defaultTicker.toUpperCase(),
        quantity: undefined,
        limit_price: undefined,
        stop_price: undefined,
      })
      setCrossFieldError(null)
      setOrderType('market')
    }
  }, [isOpen, defaultTicker, reset])

  // Watched values for live estimates
  const watchedTicker = watch('ticker') ?? ''
  const watchedQuantity = watch('quantity')
  const watchedLimitPrice = watch('limit_price')

  // Normalised ticker for queries
  const queryTicker = watchedTicker.toUpperCase().trim()

  // ---------------------------------------------------------------------------
  // React Query
  // ---------------------------------------------------------------------------

  const { data: quoteData, isLoading: quoteLoading } = useQuery({
    queryKey: ['quote', queryTicker],
    queryFn: () => getQuote(queryTicker),
    enabled: queryTicker.length >= 1,
    staleTime: 30_000,
  })

  const { data: accountData, isLoading: accountLoading } = useQuery({
    queryKey: ['account'],
    queryFn: getAccount,
    staleTime: 60_000,
  })

  const { data: positionsData } = useQuery({
    queryKey: ['positions'],
    queryFn: getPositions,
    enabled: side === 'sell',
    staleTime: 60_000,
  })

  // ---------------------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------------------

  const currentPrice = quoteData?.price ?? null

  // Price used for estimation: limit_price for limit/stop_limit orders; else market price
  const estimationPrice: number | null =
    orderType === 'limit' || orderType === 'stop_limit'
      ? watchedLimitPrice ?? null
      : currentPrice

  const estimatedValue: number | null =
    watchedQuantity && watchedQuantity > 0 && estimationPrice !== null
      ? watchedQuantity * estimationPrice
      : null

  const buyingPower = accountData?.buying_power ?? null

  const afterTradeBalance: number | null =
    buyingPower !== null && estimatedValue !== null
      ? side === 'buy'
        ? buyingPower - estimatedValue
        : buyingPower + estimatedValue
      : null

  const heldShares: number =
    positionsData?.find((p) => p.ticker === queryTicker)?.quantity ?? 0

  // Determine if the submit button should be enabled
  const canSubmit =
    !errors.ticker &&
    !errors.quantity &&
    !errors.limit_price &&
    !errors.stop_price &&
    queryTicker.length >= 1

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  const onSubmit = (data: OrderFormValues) => {
    setCrossFieldError(null)

    // Cross-field validation
    if (side === 'buy' && estimatedValue !== null && buyingPower !== null) {
      if (estimatedValue > buyingPower) {
        setCrossFieldError(
          `Insufficient buying power. Estimated cost ${formatCurrency(estimatedValue)} exceeds available ${formatCurrency(buyingPower)}.`
        )
        return
      }
    }

    if (side === 'sell' && data.quantity > heldShares) {
      setCrossFieldError(
        `Insufficient shares. You hold ${heldShares} share${heldShares !== 1 ? 's' : ''} of ${data.ticker}.`
      )
      return
    }

    // Require limit_price for limit / stop_limit orders
    if ((orderType === 'limit' || orderType === 'stop_limit') && !data.limit_price) {
      setCrossFieldError('Limit price is required for this order type.')
      return
    }

    // Require stop_price for stop / stop_limit orders
    if ((orderType === 'stop' || orderType === 'stop_limit') && !data.stop_price) {
      setCrossFieldError('Stop price is required for this order type.')
      return
    }

    const orderRequest: PlaceOrderRequest = {
      ticker: data.ticker,
      side,
      order_type: orderType,
      quantity: data.quantity,
      ...(data.limit_price !== undefined ? { limit_price: data.limit_price } : {}),
      ...(data.stop_price !== undefined ? { stop_price: data.stop_price } : {}),
    }

    if (isRealMoney) {
      // Real-money path: use the confirmation store
      const realOrderRequest: RealOrderRequest = {
        ...orderRequest,
        confirmation_text: '', // will be set by the modal
      }
      openConfirmation(realOrderRequest)
      return
    }

    // Paper trading path (unchanged)
    setPendingOrder(orderRequest)
  }

  // ---------------------------------------------------------------------------
  // Price fields visibility
  // ---------------------------------------------------------------------------

  const showLimitPrice = orderType === 'limit' || orderType === 'stop_limit'
  const showStopPrice = orderType === 'stop' || orderType === 'stop_limit'

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <>
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="order-ticket-backdrop"
            className="fixed inset-0 z-50 bg-black/60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Slide-in panel */}
          <motion.div
            key="order-ticket-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Order Ticket"
            className="fixed right-0 top-0 bottom-0 z-50 flex w-full max-w-md flex-col bg-card border-l border-border shadow-2xl"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            {/* Scrollable inner content */}
            <div className="flex flex-col h-full overflow-y-auto">
              {/* ── Header ── */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
                <h2 className="text-lg font-semibold text-foreground">Order Ticket</h2>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Close order ticket"
                  className="text-muted-foreground hover:text-foreground transition-colors rounded-md p-1"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* ── Form body ── */}
              <form
                onSubmit={handleSubmit(onSubmit)}
                className="flex flex-col gap-5 px-5 py-5 flex-1"
                noValidate
              >
                {/* ── Ticker input ── */}
                <div>
                  <label
                    htmlFor="order-ticker"
                    className="block text-sm font-medium text-foreground mb-1"
                  >
                    Ticker Symbol
                  </label>
                  <input
                    id="order-ticker"
                    type="text"
                    placeholder="e.g. AAPL"
                    autoComplete="off"
                    {...register('ticker', {
                      onChange: (e) => {
                        e.target.value = e.target.value.toUpperCase()
                        setValue('ticker', e.target.value)
                      },
                    })}
                    ref={(el) => {
                      // Merge refs: react-hook-form ref + our local ref
                      register('ticker').ref(el)
                      ;(tickerInputRef as React.MutableRefObject<HTMLInputElement | null>).current = el
                    }}
                    className={cn(
                      'w-full px-3 py-2 bg-input border rounded-md text-foreground',
                      'placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm uppercase',
                      errors.ticker ? 'border-destructive' : 'border-border'
                    )}
                  />
                  {errors.ticker && (
                    <p className="text-destructive text-xs mt-1">{errors.ticker.message}</p>
                  )}
                </div>

                {/* ── Quote display ── */}
                <div className="flex items-center gap-3 min-h-[2rem]">
                  {quoteLoading && queryTicker.length >= 1 && (
                    <div className="flex gap-2 animate-pulse">
                      <div className="h-4 w-28 bg-muted rounded" />
                      <div className="h-4 w-16 bg-muted rounded" />
                    </div>
                  )}
                  {!quoteLoading && quoteData && (
                    <>
                      <span className="text-sm font-medium text-foreground">{quoteData.company_name}</span>
                      <span className="text-base font-semibold text-foreground">
                        {formatCurrency(quoteData.price)}
                      </span>
                      <span
                        className={cn(
                          'text-xs font-medium',
                          quoteData.change_pct >= 0 ? 'text-gain' : 'text-loss'
                        )}
                      >
                        {quoteData.change_pct >= 0 ? '+' : ''}
                        {(quoteData.change_pct * 100).toFixed(2)}%
                      </span>
                    </>
                  )}
                </div>

                {/* ── Buy / Sell toggle ── */}
                <div>
                  <span className="block text-sm font-medium text-foreground mb-2">Action</span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setSide('buy')}
                      className={cn(
                        'flex-1 py-2 rounded-md text-sm font-semibold transition-colors',
                        side === 'buy'
                          ? 'bg-green-600 text-white'
                          : 'bg-muted text-muted-foreground hover:bg-muted/80'
                      )}
                    >
                      Buy
                    </button>
                    <button
                      type="button"
                      onClick={() => setSide('sell')}
                      className={cn(
                        'flex-1 py-2 rounded-md text-sm font-semibold transition-colors',
                        side === 'sell'
                          ? 'bg-red-600 text-white'
                          : 'bg-muted text-muted-foreground hover:bg-muted/80'
                      )}
                    >
                      Sell
                    </button>
                  </div>
                  {/* Held shares info for sell side */}
                  {side === 'sell' && queryTicker.length >= 1 && (
                    <p className="text-xs text-muted-foreground mt-1.5">
                      Shares held: <span className="font-medium text-foreground">{heldShares}</span>
                    </p>
                  )}
                </div>

                {/* ── Order type selector ── */}
                <div>
                  <span className="block text-sm font-medium text-foreground mb-2">Order Type</span>
                  <div className="grid grid-cols-4 gap-1.5">
                    {ORDER_TYPES.map(({ value, label }) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setOrderType(value)}
                        className={cn(
                          'py-2 px-1 rounded-md text-xs font-medium transition-colors',
                          orderType === value
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted text-muted-foreground hover:bg-muted/80'
                        )}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* ── Quantity input ── */}
                <div>
                  <label
                    htmlFor="order-quantity"
                    className="block text-sm font-medium text-foreground mb-1"
                  >
                    Shares
                  </label>
                  <input
                    id="order-quantity"
                    type="number"
                    min={1}
                    step={1}
                    placeholder="0"
                    {...register('quantity', { valueAsNumber: true })}
                    className={cn(
                      'w-full px-3 py-2 bg-input border rounded-md text-foreground',
                      'placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm',
                      errors.quantity ? 'border-destructive' : 'border-border'
                    )}
                  />
                  {errors.quantity && (
                    <p className="text-destructive text-xs mt-1">{errors.quantity.message}</p>
                  )}
                </div>

                {/* ── Limit price (conditional) ── */}
                {showLimitPrice && (
                  <div>
                    <label
                      htmlFor="order-limit-price"
                      className="block text-sm font-medium text-foreground mb-1"
                    >
                      Limit Price
                    </label>
                    <input
                      id="order-limit-price"
                      type="number"
                      min={0.01}
                      step={0.01}
                      placeholder="0.00"
                      {...register('limit_price', { valueAsNumber: true })}
                      className={cn(
                        'w-full px-3 py-2 bg-input border rounded-md text-foreground',
                        'placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm',
                        errors.limit_price ? 'border-destructive' : 'border-border'
                      )}
                    />
                    {errors.limit_price && (
                      <p className="text-destructive text-xs mt-1">{errors.limit_price.message}</p>
                    )}
                  </div>
                )}

                {/* ── Stop price (conditional) ── */}
                {showStopPrice && (
                  <div>
                    <label
                      htmlFor="order-stop-price"
                      className="block text-sm font-medium text-foreground mb-1"
                    >
                      Stop Price
                    </label>
                    <input
                      id="order-stop-price"
                      type="number"
                      min={0.01}
                      step={0.01}
                      placeholder="0.00"
                      {...register('stop_price', { valueAsNumber: true })}
                      className={cn(
                        'w-full px-3 py-2 bg-input border rounded-md text-foreground',
                        'placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm',
                        errors.stop_price ? 'border-destructive' : 'border-border'
                      )}
                    />
                    {errors.stop_price && (
                      <p className="text-destructive text-xs mt-1">{errors.stop_price.message}</p>
                    )}
                  </div>
                )}

                {/* ── Estimated cost / proceeds ── */}
                <div className="bg-muted/30 border border-border rounded-lg px-4 py-3 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">
                      {side === 'buy' ? 'Estimated Cost' : 'Estimated Proceeds'}
                    </span>
                    <span className="text-sm font-semibold text-foreground">
                      {estimatedValue !== null ? formatCurrency(estimatedValue) : '—'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Buying Power</span>
                    <span className="text-sm font-semibold text-foreground">
                      {accountLoading ? (
                        <span className="inline-block h-4 w-20 bg-muted rounded animate-pulse" />
                      ) : buyingPower !== null ? (
                        formatCurrency(buyingPower)
                      ) : (
                        '—'
                      )}
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">After Trade Balance</span>
                    <span
                      className={cn(
                        'text-sm font-semibold',
                        afterTradeBalance === null
                          ? 'text-foreground'
                          : afterTradeBalance < 0
                            ? 'text-loss'
                            : 'text-foreground'
                      )}
                    >
                      {afterTradeBalance !== null ? formatCurrency(afterTradeBalance) : '—'}
                    </span>
                  </div>
                </div>

                {/* ── Cross-field validation error ── */}
                {crossFieldError && (
                  <div className="bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-md px-3 py-2">
                    {crossFieldError}
                  </div>
                )}

                {/* ── Submit button ── */}
                <button
                  type="submit"
                  disabled={!canSubmit}
                  className={cn(
                    'w-full py-2.5 rounded-md text-sm font-semibold transition-colors mt-auto',
                    side === 'buy'
                      ? 'bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed'
                      : 'bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  Review Order
                </button>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>

    {/* Order confirmation modal — rendered outside the slide panel so it can stack above it */}
    <OrderConfirmModal
      isOpen={pendingOrder !== null}
      onClose={() => {
        setPendingOrder(null)
        onClose()
      }}
      order={pendingOrder}
      currentPrice={currentPrice}
    />
    <RealTradeConfirmModal
      isOpen={isRealConfirmOpen}
      onClose={closeConfirmation}
      order={pendingRealOrder}
      onConfirmed={() => onClose()}
    />
    </>
  )
}
