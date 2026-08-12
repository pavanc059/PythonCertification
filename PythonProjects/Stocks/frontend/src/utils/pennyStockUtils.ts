import type { PennyStock } from '@/api/market'

export type SortField = 'rank' | 'ticker' | 'price' | 'price_change_pct'
  | 'volume_ratio' | 'momentum_score' | 'risk_level'
export type SortDir = 'asc' | 'desc'

const RISK_ORDER: Record<PennyStock['risk_level'], number> = {
  low: 0,
  medium: 1,
  high: 2,
  extreme: 3,
}

/**
 * Pure sort utility for penny stock rows.
 * Returns a new array — does not mutate the input.
 */
export function sortPennyStocks(
  rows: PennyStock[],
  field: SortField,
  dir: SortDir
): PennyStock[] {
  return [...rows].sort((a, b) => {
    let cmp = 0

    switch (field) {
      case 'ticker':
        cmp = a.ticker.localeCompare(b.ticker)
        break
      case 'price':
        cmp = a.price - b.price
        break
      case 'price_change_pct':
        cmp = a.price_change_pct - b.price_change_pct
        break
      case 'volume_ratio':
        cmp = a.volume_ratio - b.volume_ratio
        break
      case 'momentum_score':
        cmp = a.momentum_score - b.momentum_score
        break
      case 'risk_level':
        cmp = RISK_ORDER[a.risk_level] - RISK_ORDER[b.risk_level]
        break
      case 'rank':
      default:
        // rank = by momentum_score desc (no explicit rank field)
        cmp = a.momentum_score - b.momentum_score
        break
    }

    return dir === 'asc' ? cmp : -cmp
  })
}

/**
 * Returns the top `limit` penny stocks from the array.
 * Length is always Math.min(rows.length, limit).
 */
export function selectTopPennyStocks(rows: PennyStock[], limit: number): PennyStock[] {
  return rows.slice(0, limit)
}
