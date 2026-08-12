import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import type { PennyStock } from '@/api/market'
import { SkeletonPulse } from '@/components/common'
import { cn } from '@/lib/utils'
import { sortPennyStocks, type SortField, type SortDir } from '@/utils/pennyStockUtils'

export interface MomentumTableProps {
  rows: PennyStock[]
  isLoading: boolean
}

const RISK_CLASSES: Record<PennyStock['risk_level'], string> = {
  low: 'bg-green-500/15 text-green-400 border border-green-500/30',
  medium: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  high: 'bg-orange-500/15 text-orange-400 border border-orange-500/30',
  extreme: 'bg-red-500/15 text-red-400 border border-red-500/30',
}

interface Column {
  field: SortField
  label: string
  className?: string
  align?: 'left' | 'right'
}

const COLUMNS: Column[] = [
  { field: 'rank',             label: '#',         className: 'w-8',   align: 'right' },
  { field: 'ticker',           label: 'Ticker',    className: 'w-20',  align: 'left'  },
  { field: 'price',            label: 'Price',     className: 'w-20',  align: 'right' },
  { field: 'price_change_pct', label: 'Chg %',     className: 'w-20',  align: 'right' },
  { field: 'volume_ratio',     label: 'Vol ×',     className: 'w-20',  align: 'right' },
  { field: 'momentum_score',   label: 'Score',     className: 'w-20',  align: 'right' },
  { field: 'risk_level',       label: 'Risk',      className: 'w-24',  align: 'left'  },
]

function SortIcon({ field, sortField, sortDir }: {
  field: SortField
  sortField: SortField
  sortDir: SortDir
}) {
  if (field !== sortField) {
    return <ChevronsUpDown className="h-3 w-3 text-slate-500" aria-hidden="true" />
  }
  return sortDir === 'asc'
    ? <ChevronUp className="h-3 w-3 text-[#6366f1]" aria-hidden="true" />
    : <ChevronDown className="h-3 w-3 text-[#6366f1]" aria-hidden="true" />
}

export function MomentumTable({ rows, isLoading }: MomentumTableProps) {
  const [sortField, setSortField] = useState<SortField>('momentum_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  function handleSort(field: SortField) {
    if (field === sortField) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  const sorted = sortPennyStocks(rows, sortField, sortDir)

  return (
    <div className="overflow-x-auto rounded-xl border border-[#1f2d40]">
      <table className="w-full text-sm" role="table" aria-label="Penny stocks momentum">
        <thead>
          <tr className="border-b border-[#1f2d40] bg-[#0a0e1a]">
            {COLUMNS.map((col) => (
              <th
                key={col.field}
                scope="col"
                className={cn(
                  'px-3 py-2.5 font-medium text-xs text-slate-400 select-none cursor-pointer',
                  'hover:text-slate-200 transition-colors',
                  col.align === 'right' ? 'text-right' : 'text-left',
                  col.className
                )}
                onClick={() => handleSort(col.field)}
                aria-sort={
                  col.field === sortField
                    ? sortDir === 'asc' ? 'ascending' : 'descending'
                    : 'none'
                }
              >
                <span className="inline-flex items-center gap-1">
                  {col.align === 'right' && (
                    <SortIcon field={col.field} sortField={sortField} sortDir={sortDir} />
                  )}
                  {col.label}
                  {col.align !== 'right' && (
                    <SortIcon field={col.field} sortField={sortField} sortDir={sortDir} />
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading &&
            Array.from({ length: 8 }).map((_, i) => (
              <tr key={i} className="border-b border-[#1f2d40]">
                {COLUMNS.map((col) => (
                  <td key={col.field} className="px-3 py-2.5">
                    <SkeletonPulse className="h-4 w-full" />
                  </td>
                ))}
              </tr>
            ))}

          {!isLoading && sorted.length === 0 && (
            <tr>
              <td
                colSpan={COLUMNS.length}
                className="px-3 py-10 text-center text-sm text-slate-500"
              >
                No penny stocks available.
              </td>
            </tr>
          )}

          {!isLoading &&
            sorted.map((stock, idx) => {
              const changePositive = stock.price_change_pct >= 0
              return (
                <tr
                  key={stock.ticker}
                  className="border-b border-[#1f2d40] bg-[#111827] hover:bg-[#1a2235] transition-colors"
                >
                  {/* Rank */}
                  <td className="px-3 py-2.5 text-right text-xs text-slate-500">
                    {idx + 1}
                  </td>

                  {/* Ticker */}
                  <td className="px-3 py-2.5">
                    <span className="font-semibold text-[#6366f1] tracking-wide">
                      {stock.ticker}
                    </span>
                  </td>

                  {/* Price */}
                  <td className="px-3 py-2.5 text-right font-medium text-slate-200">
                    ${stock.price.toFixed(2)}
                  </td>

                  {/* Change % */}
                  <td className={cn(
                    'px-3 py-2.5 text-right font-medium text-xs',
                    changePositive ? 'text-green-400' : 'text-red-400'
                  )}>
                    {changePositive ? '+' : ''}{stock.price_change_pct.toFixed(2)}%
                  </td>

                  {/* Volume ratio */}
                  <td className="px-3 py-2.5 text-right text-slate-300 text-xs">
                    {stock.volume_ratio.toFixed(1)}×
                  </td>

                  {/* Momentum score */}
                  <td className="px-3 py-2.5 text-right">
                    <span className={cn(
                      'font-semibold text-xs tabular-nums',
                      stock.momentum_score >= 80 ? 'text-green-400'
                        : stock.momentum_score >= 50 ? 'text-yellow-400'
                        : 'text-slate-400'
                    )}>
                      {stock.momentum_score.toFixed(1)}
                    </span>
                  </td>

                  {/* Risk level */}
                  <td className="px-3 py-2.5">
                    <span className={cn(
                      'inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize',
                      RISK_CLASSES[stock.risk_level]
                    )}>
                      {stock.risk_level}
                    </span>
                  </td>
                </tr>
              )
            })}
        </tbody>
      </table>
    </div>
  )
}
