import { useState, useRef } from 'react'
import { Plus, Loader2, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getQuote } from '@/api/market'

interface AddTickerInputProps {
  /**
   * Called when a ticker has been successfully validated.
   * Receives the uppercased ticker symbol and the company name from the quote.
   */
  onAdd: (ticker: string, companyName: string) => void
  /** Disables the input while a parent operation (e.g. saving) is in progress */
  isLoading?: boolean
  className?: string
}

/**
 * Controlled search input that validates a ticker symbol against the market
 * quote API before calling `onAdd`.
 *
 * Satisfies R3.1: users can type a ticker symbol to add it to their watchlist.
 */
export function AddTickerInput({ onAdd, isLoading = false, className }: AddTickerInputProps) {
  const [value, setValue] = useState('')
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const isDisabled = isLoading || validating

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Force uppercase and strip non-word characters (letters, digits, dots, hyphens)
    const raw = e.target.value.toUpperCase().replace(/[^A-Z0-9.\-]/g, '')
    setValue(raw)
    // Clear any previous error as soon as the user edits the input
    if (error) setError(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      void submit()
    }
  }

  const submit = async () => {
    const ticker = value.trim().toUpperCase()
    if (!ticker) return

    setValidating(true)
    setError(null)

    try {
      const quote = await getQuote(ticker)
      // Success — notify parent and reset
      onAdd(ticker, quote.company_name)
      setValue('')
      inputRef.current?.focus()
    } catch {
      setError('Invalid ticker symbol. Please try again.')
    } finally {
      setValidating(false)
    }
  }

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div className="flex items-center gap-2">
        {/* Ticker input */}
        <div className="relative flex-1">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={isDisabled}
            placeholder="Enter ticker (e.g. AAPL)"
            aria-label="Ticker symbol"
            aria-describedby={error ? 'ticker-error' : undefined}
            aria-invalid={error ? 'true' : 'false'}
            maxLength={10}
            className={cn(
              'w-full px-3 py-2 text-sm rounded-md',
              'bg-input border text-foreground placeholder:text-muted-foreground',
              'focus:outline-none focus:ring-2 focus:ring-ring',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-colors',
              error ? 'border-destructive focus:ring-destructive/40' : 'border-border'
            )}
          />
        </div>

        {/* Add button */}
        <button
          type="button"
          onClick={() => void submit()}
          disabled={isDisabled || !value.trim()}
          aria-label="Add ticker to watchlist"
          className={cn(
            'flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md',
            'bg-primary text-primary-foreground',
            'hover:opacity-90 active:opacity-80',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'transition-opacity whitespace-nowrap'
          )}
        >
          {validating ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Plus className="h-4 w-4" aria-hidden="true" />
          )}
          Add
        </button>
      </div>

      {/* Inline error message */}
      {error && (
        <p
          id="ticker-error"
          role="alert"
          className="flex items-center gap-1 text-xs text-destructive mt-0.5"
        >
          <AlertCircle className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  )
}

export default AddTickerInput
