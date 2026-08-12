import { useState, useMemo } from 'react'
import { cn } from '@/lib/utils'
import { formatCurrency, formatDate, getPnlClass } from '@/lib/formatters'
import type { ClosedTradeRecord } from '@/api/portfolio'

type SortColumn = 'closed_at' | 'ticker' | 'realized_pnl'
type SortDirection = 'asc' | 'desc'
type SideFilter = 'all' | 'buy' | 'sell'

interface SortState {
  column: SortColumn | null
  direction: SortDirection
}

interface FilterState {
  ticker: string
  dateFrom: string
  dateTo: string
  side: SideFilter
}

interface TradeHistoryTableProps {
  trades: ClosedTradeRecord[]
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

function SideBadge({ side }: { side: string }) {
  const isBuy = side.toLowerCase() === 'buy'
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase',
        isBuy
          ? 'bg-green-500/20 text-gain border border-green-500/30'
          : 'bg-red-500/20 text-loss border border-red-500/30'
      )}
    >
      {side}
    </span>
  )
}

function buildCsvContent(trades: ClosedTradeRecord[]): string {
  const headers = [
    'Date',
    'Ticker',
    'Side',
    'Qty',
    'Fill Price',
    'Commission',
    'Slippage',
    'Realized P&L',
  ]
  const rows = trades.map(t => [
    formatDate(t.closed_at),
    t.ticker,
    t.side.toUpperCase(),
    String(t.quantity),
    t.exit_price.toFixed(2),
    '—',
    '—',
    t.realized_pnl.toFixed(2),
  ])
  return [headers, ...rows].map(row => row.join(',')).join('\n')
}

function downloadCsv(content: string) {
  const today = new Date().toISOString().slice(0, 10)
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `trade-history-${today}.csv`
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function TradeHistoryTable({ trades, isLoading = false }: TradeHistoryTableProps) {
  const [sortState, setSortState] = useState<SortState>({ column: 'closed_at', direction: 'desc' })
  const [filters, setFilters] = useState<FilterState>({
    ticker: '',
    dateFrom: '',
    dateTo: '',
    side: 'all',
  })

  const handleSort = (column: SortColumn) => {
    setSortState(prev =>
      prev.column === column
        ? { column, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { column, direction: 'asc' }
    )
  }

  const filteredAndSorted = useMemo(() => {
    let result = [...trades]

    // Filter by ticker
    if (filters.ticker.trim()) {
      const q = filters.ticker.trim().toLowerCase()
      result = result.filter(t => t.ticker.toLowerCase().includes(q))
    }

    // Filter by date range
    if (filters.dateFrom) {
      const from = new Date(filters.dateFrom).getTime()
      result = result.filter(t => new Date(t.closed_at).getTime() >= from)
    }
    if (filters.dateTo) {
      // Include the full "to" day
      const to = new Date(filters.dateTo).getTime() + 86_400_000 - 1
      result = result.filter(t => new Date(t.closed_at).getTime() <= to)
    }

    // Filter by side
    if (filters.side !== 'all') {
      result = result.filter(t => t.side.toLowerCase() === filters.side)
    }

    // Sort
    if (sortState.column) {
      const col = sortState.column
      result.sort((a, b) => {
        let aVal: string | number
        let bVal: string | number
        switch (col) {
          case 'closed_at':
            aVal = new Date(a.closed_at).getTime()
            bVal = new Date(b.closed_at).getTime()
            break
          case 'ticker':
            aVal = a.ticker
            bVal = b.ticker
            break
          case 'realized_pnl':
            aVal = a.realized_pnl
            bVal = b.realized_pnl
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
    }

    return result
  }, [trades, filters, sortState])

  const handleExportCsv = () => {
    const content = buildCsvContent(filteredAndSorted)
    downloadCsv(content)
  }

  const thSortable = (col: SortColumn, label: string) => (
    <th
      className="px-4 py-3 text-left text-xs uppercase text-muted-foreground font-medium whitespace-nowrap cursor-pointer hover:text-foreground select-none"
      onClick={() => handleSort(col)}
    >
      {label} <SortArrow column={col} sortState={sortState} />
    </th>
  )

  const thStatic = (label: string) => (
    <th className="px-4 py-3 text-left text-xs uppercase text-muted-foreground font-medium whitespace-nowrap">
      {label}
    </th>
  )

  return (
    <div className="flex flex-col gap-3">
      {/* Filter row */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Ticker search */}
        <input
          type="text"
          placeholder="Filter by ticker…"
          value={filters.ticker}
          onChange={e => setFilters(prev => ({ ...prev, ticker: e.target.value }))}
          className="px-3 py-1.5 rounded-md border border-border bg-input text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring w-40"
        />

        {/* Date from */}
        <div className="flex items-center gap-1">
          <label className="text-xs text-muted-foreground whitespace-nowrap">From:</label>
          <input
            type="date"
            value={filters.dateFrom}
            onChange={e => setFilters(prev => ({ ...prev, dateFrom: e.target.value }))}
            className="px-3 py-1.5 rounded-md border border-border bg-input text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>

        {/* Date to */}
        <div className="flex items-center gap-1">
          <label className="text-xs text-muted-foreground whitespace-nowrap">To:</label>
          <input
            type="date"
            value={filters.dateTo}
            onChange={e => setFilters(prev => ({ ...prev, dateTo: e.target.value }))}
            className="px-3 py-1.5 rounded-md border border-border bg-input text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>

        {/* Side filter */}
        <div className="flex rounded-md border border-border overflow-hidden text-xs font-medium">
          {(['all', 'buy', 'sell'] as SideFilter[]).map(s => (
            <button
              key={s}
              type="button"
              onClick={() => setFilters(prev => ({ ...prev, side: s }))}
              className={cn(
                'px-3 py-1.5 capitalize transition-colors',
                filters.side === s
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card text-muted-foreground hover:bg-muted/50'
              )}
            >
              {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        {/* CSV export */}
        <button
          type="button"
          onClick={handleExportCsv}
          disabled={filteredAndSorted.length === 0}
          className="ml-auto px-3 py-1.5 rounded-md border border-border bg-card text-sm text-foreground hover:bg-muted/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"
            />
          </svg>
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm border-collapse">
          <thead className="sticky top-0 bg-card border-b border-border">
            <tr>
              {thSortable('closed_at', 'Date')}
              {thSortable('ticker', 'Ticker')}
              {thStatic('Side')}
              {thStatic('Qty')}
              {thStatic('Fill Price')}
              {thStatic('Commission')}
              {thStatic('Slippage')}
              {thSortable('realized_pnl', 'Realized P&L')}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <>
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
              </>
            ) : filteredAndSorted.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                  No trade history
                </td>
              </tr>
            ) : (
              filteredAndSorted.map((trade, idx) => (
                <tr
                  key={`${trade.ticker}-${trade.closed_at}-${idx}`}
                  className="even:bg-muted/20 hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-3 whitespace-nowrap text-muted-foreground">
                    {formatDate(trade.closed_at)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap font-semibold">{trade.ticker}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <SideBadge side={trade.side} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">{trade.quantity}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {formatCurrency(trade.exit_price)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-muted-foreground">—</td>
                  <td className="px-4 py-3 whitespace-nowrap text-muted-foreground">—</td>
                  <td
                    className={cn(
                      'px-4 py-3 whitespace-nowrap font-medium',
                      getPnlClass(trade.realized_pnl)
                    )}
                  >
                    {formatCurrency(trade.realized_pnl)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
