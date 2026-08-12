import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Bell, Search } from 'lucide-react'
import { useAlertStore } from '@/store/alertStore'
import { cn } from '@/lib/utils'

interface TopHeaderProps {
  title: string
}

/** Map from route path prefix → human-readable page title */
const ROUTE_TITLE_MAP: Record<string, string> = {
  '/dashboard':    'Dashboard',
  '/portfolio':    'Portfolio',
  '/watchlist':    'Watchlist',
  '/trading':      'Trading',
  '/stock/search': 'Stock Search',
  '/stock/':       'Stock Detail',
  '/market':       'Daily Market Brief',
  '/penny-stocks': 'Penny Stocks',
  '/news':         'News Feed',
  '/predictions':  'Predictions',
  '/alerts':       'Alerts',
  '/settings':     'Settings',
}

/** Derive a page title from the current pathname using ROUTE_TITLE_MAP. */
function deriveTitle(pathname: string): string {
  // Exact match first
  if (ROUTE_TITLE_MAP[pathname]) return ROUTE_TITLE_MAP[pathname]

  // Prefix match (e.g. /stock/AAPL → 'Stock Detail')
  for (const prefix of Object.keys(ROUTE_TITLE_MAP)) {
    if (pathname.startsWith(prefix)) {
      return ROUTE_TITLE_MAP[prefix]
    }
  }

  return 'StockIQ'
}

/** Validate 1–10 uppercase alphanumeric characters */
function isValidTicker(value: string): boolean {
  return /^[A-Z0-9]{1,10}$/.test(value)
}

export function TopHeader({ title }: TopHeaderProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const unreadCount = useAlertStore((s) => s.unreadCount)

  const [tickerInput, setTickerInput] = useState('')
  const [inputError, setInputError] = useState(false)

  // Derive the current page title from the route; fall back to the prop
  const pageTitle = deriveTitle(location.pathname) || title

  // Badge text: null if 0, "99+" if > 99, else string count
  const badgeText =
    unreadCount === 0 ? null
    : unreadCount > 99 ? '99+'
    : String(unreadCount)

  const handleSearchSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const ticker = tickerInput.trim().toUpperCase()
    if (!isValidTicker(ticker)) {
      setInputError(true)
      return
    }
    setInputError(false)
    setTickerInput('')
    navigate(`/stock/${ticker}`)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Auto-uppercase as the user types; strip disallowed characters
    const value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '')
    setTickerInput(value)
    if (inputError) setInputError(false)
  }

  return (
    <header className="sticky top-0 z-40 flex items-center justify-between gap-4 px-4 py-3 bg-card border-b border-border">
      {/* Page title */}
      <h1 className="text-lg font-semibold text-foreground truncate shrink-0">
        {pageTitle}
      </h1>

      {/* Right-side controls */}
      <div className="flex items-center gap-3 ml-auto">
        {/* Global stock search */}
        <form
          onSubmit={handleSearchSubmit}
          className="relative flex items-center"
          role="search"
          aria-label="Search stocks"
        >
          <span className="absolute left-2.5 text-muted-foreground pointer-events-none" aria-hidden="true">
            <Search size={15} />
          </span>
          <input
            type="text"
            value={tickerInput}
            onChange={handleInputChange}
            placeholder="Ticker…"
            maxLength={10}
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            aria-label="Stock ticker symbol"
            aria-invalid={inputError}
            className={cn(
              'w-36 pl-8 pr-3 py-1.5 rounded-md text-sm bg-secondary text-foreground placeholder-muted-foreground',
              'border focus:outline-none focus:ring-2 focus:ring-primary/50 transition-colors',
              inputError
                ? 'border-destructive focus:ring-destructive/50'
                : 'border-border'
            )}
          />
          {inputError && (
            <p
              role="alert"
              className="absolute top-full left-0 mt-1 text-xs text-destructive whitespace-nowrap"
            >
              1–10 uppercase alphanumeric
            </p>
          )}
        </form>

        {/* Notification bell */}
        <button
          type="button"
          onClick={() => navigate('/alerts')}
          aria-label={
            badgeText
              ? `Alerts — ${unreadCount} unread`
              : 'Alerts — no unread'
          }
          className="relative p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
        >
          <Bell size={20} />

          {badgeText !== null && (
            <span
              data-testid="alert-badge"
              className={cn(
                'absolute -top-1 -right-1 flex items-center justify-center',
                'min-w-[18px] h-[18px] px-1 rounded-full',
                'bg-destructive text-destructive-foreground text-[10px] font-bold leading-none',
              )}
              aria-hidden="true"
            >
              {badgeText}
            </span>
          )}
        </button>
      </div>
    </header>
  )
}
