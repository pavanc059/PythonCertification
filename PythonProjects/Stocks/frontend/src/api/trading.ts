import apiClient from './client'

// --- Request types ---

export type OrderSide = 'buy' | 'sell'
export type OrderType = 'market' | 'limit' | 'stop' | 'stop_loss' | 'stop_limit'
export type OrderStatus = 'pending' | 'filled' | 'cancelled' | 'rejected'

export interface PlaceOrderRequest {
  ticker: string
  side: OrderSide
  order_type: OrderType
  quantity: number
  limit_price?: number
  stop_price?: number
}

// --- Response types ---

export interface AccountSummary {
  account_id: string
  cash: number
  portfolio_value: number
  total_value: number
  buying_power: number
}

export interface OrderResponse {
  order_id: string
  ticker: string
  side: OrderSide
  order_type: OrderType
  quantity: number
  limit_price?: number
  stop_price?: number
  status: OrderStatus
  filled_price?: number
  created_at: string
}

export interface Order {
  order_id: string
  ticker: string
  side: OrderSide
  order_type: OrderType
  quantity: number
  limit_price?: number
  stop_price?: number
  status: OrderStatus
  filled_price?: number
  created_at: string
  updated_at?: string
}

export interface ResetResponse {
  message: string
  new_balance: number
}

// --- API functions ---

export async function getAccount(): Promise<AccountSummary> {
  const res = await apiClient.get<AccountSummary>('/trading/account')
  return res.data
}

export async function placeOrder(data: PlaceOrderRequest): Promise<OrderResponse> {
  const res = await apiClient.post<OrderResponse>('/trading/orders', data)
  return res.data
}

export async function getOrders(): Promise<Order[]> {
  const res = await apiClient.get<Order[]>('/trading/orders')
  return res.data
}

export async function cancelOrder(orderId: string): Promise<void> {
  await apiClient.delete(`/trading/orders/${orderId}`)
}

export async function resetAccount(): Promise<ResetResponse> {
  const res = await apiClient.post<ResetResponse>('/trading/reset')
  return res.data
}

// --- Real-trade confirmation ---

export interface RealOrderRequest {
  ticker: string
  side: OrderSide
  order_type: OrderType
  quantity: number
  limit_price?: number
  stop_price?: number
  confirmation_text: string   // e.g. "AAPL 100 BUY"
}

export interface RealOrderConfirmResponse {
  order_id: string
  status: 'submitted' | 'rejected'
  message: string
}

export async function confirmRealOrder(
  data: RealOrderRequest
): Promise<RealOrderConfirmResponse> {
  const res = await apiClient.post<RealOrderConfirmResponse>(
    '/trading/real/confirm',
    data
  )
  return res.data
}
