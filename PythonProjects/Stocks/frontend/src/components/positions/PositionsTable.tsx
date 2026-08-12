import { useState, useMemo } from 'react'
import { cn } from '@/lib/utils'
import { formatCurrency, formatPercent, getPnlClass } from '@/lib/formatters'
import type { Position } from '@/api/portfolio'

type SortColumn = 'ticker' | 'quantity' | 'market_value' | 'unrealized_pnl_pct' | 'day_change_pct'
type SortDirection = 'asc' | 'desc'

interface SortState {
  column: SortColumn | null
  direction: SortDirection
}

interface PositionsTableProps {
  positions: Position[]
  onSell: (ticker: string) => void
  isLoading?: boolean
}

function SkeletonRow() {
  return (
    <tr className="even:bg-muted/20">
      {Array.from({ length: 9 }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-muted/50 rounded animate-pulse w-full max-w-[80px]" />
        </td>
      ))}
    </tr>
  )
}

function SortArrow({ column, sortState }: { column: SortColumn; sortState: SortState }) {
  if (sortState.column !== column) {
    return <span className="ml-1 text-muted-foreground/40">↕</span>
  }
  return (
    <span className="ml-1 text-foreground">
      {sortState.direction === 'asc' ? '▲' : '▼'}
    </span>
  )
}

export function PositionsTable({ positions, onSell, isLoading = false }: PositionsTableProps) {
  const [sortState, setSortState] = useState<SortState>({ column: null, direction: 'asc' })

  const handleSort = (column: SortColumn) => {
    setSortState(prev =>
      prev.column === column
        ? { column, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { column, direction: 'asc' }
    )
  }

  const sortedPositions = useMemo(() => {
    if (!sortState.column) return positions
    return [...positions].sort((a, b) => {
      const col = sortState.column!
      let aVal: string | number
      let bVal: string | number

      switch (col) {
        case 'ticker':
          aVal = a.ticker
          bVal = b.ticker
          break
        case 'quantity':
          aVal = a.quantity
          bVal = b.quantity
          break
        case 'market_value':
          aVal = a.market_value
          bVal = b.market_value
          break
        case 'unrealized_pnl_pct':
          aVal = a.unrealized_pnl_pct
          bVal = b.unrealized_pnl_pct
          break
        case 'day_change_pct':
          aVal = a.day_change_pct ?? 0
          bVal = b.day_change_pct ?? 0
          break
        default:
          return 0
      }

      if (typeof aVal === 'string') {
        return sortState.direction === 'asc'
          ? aVal.localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal)
      }
      return sortState.direction === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number)
    })
  }, [positions, sortState])

  const thClass = (col?: SortColumn) =>
    cn(
      'px-4 py-3 text-left text-xs uppercase text-muted-foreground font-medium whitespace-nowrap',
      col && 'cursor-pointer hover:text-foreground select-none'
    )

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-0 bg-card border-b border-border">
          <tr>
            <th className={thClass('ticker')} onClick={() => handleSort('ticker')}>
              Ticker <SortArrow column="ticker" sortState={sortState} />
            </th>
            <th className={thClass('quantity')} onClick={() => handleSort('quantity')}>
              Qty <SortArrow column="quantity" sortState={sortState} />
            </th>
            <th className={thClass()}>Avg Price</th>
            <th className={thClass()}>Current Price</th>
            <th className={thClass('market_value')} onClick={() => handleSort('market_value')}>
              Market Value <SortArrow column="market_value" sortState={sortState} />
            </th>
            <th className={thClass()}>Unrealized P&L ($)</th>
            <th
              className={thClass('unrealized_pnl_pct')}
              onClick={() => handleSort('unrealized_pnl_pct')}
            >
              Unrealized P&L (%) <SortArrow column="unrealized_pnl_pct" sortState={sortState} />
            </th>
            <th
              className={thClass('day_change_pct')}
              onClick={() => handleSort('day_change_pct')}
            >
              Day Change % <SortArrow column="day_change_pct" sortState={sortState} />
            </th>
            <th className={thClass()}>Action</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </>
          ) : sortedPositions.length === 0 ? (
            <tr>
              <td colSpan={9} className="px-4 py-12 text-center text-muted-foreground">
                No open positions
              </td>
            </tr>
          ) : (
            sortedPositions.map(pos => (
              <tr key={pos.ticker} className="even:bg-muted/20 hover:bg-muted/30 transition-colors">
                <td className="px-4 py-3 whitespace-nowrap font-semibold">{pos.ticker}</td>
                <td className="px-4 py-3 whitespace-nowrap">{pos.quantity}</td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {formatCurrency(pos.avg_entry_price)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {formatCurrency(pos.current_price)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {formatCurrency(pos.market_value)}
                </td>
                <td className={cn('px-4 py-3 whitespace-nowrap', getPnlClass(pos.unrealized_pnl))}>
                  {formatCurrency(pos.unrealized_pnl)}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 whitespace-nowrap',
                    getPnlClass(pos.unrealized_pnl_pct)
                  )}
                >
                  {formatPercent(pos.unrealized_pnl_pct)}
                </td>
                <td
                  className={cn(
                    'px-4 py-3 whitespace-nowrap',
                    pos.day_change_pct != null ? getPnlClass(pos.day_change_pct) : 'text-muted-foreground'
                  )}
                >
                  {pos.day_change_pct != null ? formatPercent(pos.day_change_pct) : '—'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => onSell(pos.ticker)}
                    className="px-3 py-1 rounded text-xs font-medium bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors"
                  >
                    Sell
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
