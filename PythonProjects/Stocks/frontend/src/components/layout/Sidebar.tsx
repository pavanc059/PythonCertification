import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, BarChart2, Bookmark, TrendingUp, Search,
  Newspaper, Zap, Rss, Brain, BellRing, Settings2, FlaskConical,
  LogOut, ChevronLeft, ChevronRight, Bot, Activity, Shield,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import { logoutUser } from '@/api/auth'
import { getPortfolioSummary } from '@/api/portfolio'
import { cn } from '@/lib/utils'
import { formatCurrency, formatPercent } from '@/lib/formatters'

/** Tradewell SVG logo mark — inline so it loads instantly with no external request. */
function TradewellLogo({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Tradewell logo"
    >
      <rect width="64" height="64" rx="14" fill="#0f1729" />
      <polyline
        points="8,46 20,36 30,40 40,24 56,12"
        stroke="#6366f1"
        strokeWidth="4.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="56" cy="12" r="4.5" fill="#818cf8" />
      <circle cx="56" cy="12" r="7" fill="#6366f1" opacity="0.3" />
      <path
        d="M28 50 L24 57 L29 57 L25 64"
        stroke="#f59e0b"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

const navItems = [
  { path: '/dashboard',    icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/portfolio',    icon: BarChart2,        label: 'Portfolio' },
  { path: '/watchlist',    icon: Bookmark,         label: 'Watchlist' },
  { path: '/trading',      icon: TrendingUp,       label: 'Trading' },
  { path: '/backtest',     icon: FlaskConical,     label: 'Backtester' },
  { path: '/autotrade',    icon: Bot,              label: 'Auto-Trade' },
  { path: '/stock/search', icon: Search,           label: 'Stock Search' },
  { path: '/ai-research',  icon: Brain,             label: 'AI Research' },
  { path: '/market',       icon: Newspaper,        label: 'Daily Market Brief' },
  { path: '/penny-stocks', icon: Zap,              label: 'Penny Stocks' },
  { path: '/news',         icon: Rss,              label: 'News Feed' },
  { path: '/predictions',  icon: Brain,            label: 'Predictions' },
  { path: '/alerts',       icon: BellRing,         label: 'Alerts' },
  { path: '/activity',     icon: Activity,         label: 'Activity Log' },
  { path: '/settings',     icon: Settings2,        label: 'Settings' },
]

// Admin-only nav items
const adminNavItems = [
  { path: '/admin', icon: Shield, label: 'Admin' },
]

/** Derive 1–2 character initials from a display name. */
function getInitials(name: string | undefined | null): string {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const user = useAuthStore((s) => s.user)
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const navigate = useNavigate()

  const { data: portfolio } = useQuery({
    queryKey: ['portfolioSummary'],
    queryFn: getPortfolioSummary,
    staleTime: 60_000,
    refetchInterval: 60_000,
  })

  const handleLogout = async () => {
    try {
      await logoutUser()
    } catch {
      // ignore logout API errors — clear local state regardless
    }
    clearAuth()
    navigate('/login')
  }

  const initials = getInitials(user?.name)
  const totalValue = portfolio?.total_value
  const returnPct = portfolio?.total_return_pct ?? 0
  const isPositive = returnPct >= 0

  return (
    <aside
      className={cn(
        'flex flex-col h-full bg-card border-r border-border transition-all duration-300',
        collapsed ? 'w-12' : 'w-60'
      )}
    >
      {/* Logo + toggle */}
      <div
        className={cn(
          'flex items-center border-b border-border p-4',
          collapsed ? 'justify-center' : 'justify-between'
        )}
      >
        {!collapsed && (
          <div className="flex items-center gap-2.5 min-w-0">
            <TradewellLogo size={32} />
            <span className="text-lg font-bold text-foreground tracking-tight">Tradewell</span>
          </div>
        )}
        {collapsed && <TradewellLogo size={28} />}
        <button
          onClick={onToggle}
          className="text-muted-foreground hover:text-foreground p-1 rounded"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Nav links */}
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto" aria-label="Primary navigation">
        {navItems.map(({ path, icon: Icon, label }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-[40px]',
                collapsed && 'justify-center',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
              )
            }
            title={collapsed ? label : undefined}
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span className="truncate max-w-[140px]">{label}</span>}
          </NavLink>
        ))}

        {/* Admin-only items */}
        {(user as { role?: string } | null)?.role === 'admin' && (
          <>
            {!collapsed && (
              <div className="pt-2 pb-1 px-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/50">Admin</span>
              </div>
            )}
            {adminNavItems.map(({ path, icon: Icon, label }) => (
              <NavLink
                key={path}
                to={path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-[40px]',
                    collapsed && 'justify-center',
                    isActive
                      ? 'bg-amber-500/10 text-amber-400'
                      : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                  )
                }
                title={collapsed ? label : undefined}
              >
                <Icon size={18} className="shrink-0" />
                {!collapsed && <span className="truncate max-w-[140px]">{label}</span>}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* User footer + logout */}
      <div className="p-3 border-t border-border">
        {!collapsed ? (
          <div className="flex items-start justify-between gap-2">
            {/* Avatar */}
            <div
              className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
              aria-hidden="true"
            >
              {initials}
            </div>

            {/* Name + account value */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{user?.name}</p>
              {totalValue !== undefined ? (
                <p
                  className={cn(
                    'text-xs font-medium',
                    isPositive ? 'text-gain' : 'text-loss'
                  )}
                >
                  {formatCurrency(totalValue)}{' '}
                  <span className="text-muted-foreground font-normal">
                    ({formatPercent(returnPct / 100)})
                  </span>
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">--</p>
              )}
            </div>

            {/* Logout */}
            <button
              onClick={handleLogout}
              className="text-muted-foreground hover:text-foreground p-1 rounded shrink-0"
              title="Logout"
              aria-label="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            {/* Avatar (collapsed) */}
            <div
              className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs font-bold"
              title={user?.name ?? ''}
              aria-hidden="true"
            >
              {initials}
            </div>

            {/* Logout (collapsed) */}
            <button
              onClick={handleLogout}
              className="w-full flex justify-center text-muted-foreground hover:text-foreground p-1 rounded"
              title="Logout"
              aria-label="Logout"
            >
              <LogOut size={18} />
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
