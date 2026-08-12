import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { MobileNav } from './MobileNav'
import { TopHeader } from './TopHeader'
import { AssistantWidget } from '@/components/assistant/AssistantWidget'

/** Map path prefixes/exact paths to human-readable page titles. */
const ROUTE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/portfolio': 'Portfolio',
  '/watchlist': 'Watchlist',
  '/trading': 'Trading',
  '/market': 'Daily Market Brief',
  '/penny-stocks': 'Penny Stocks',
  '/news': 'News Feed',
  '/predictions': 'Predictions',
  '/alerts': 'Alerts',
  '/settings': 'Settings',
  '/stock': 'Stock Detail',
  '/stock/search': 'Stock Search',
}

function deriveTitle(pathname: string): string {
  // Exact match first
  if (ROUTE_TITLES[pathname]) return ROUTE_TITLES[pathname]

  // Prefix match — longest prefix wins
  const match = Object.keys(ROUTE_TITLES)
    .filter((key) => pathname.startsWith(key + '/') || pathname === key)
    .sort((a, b) => b.length - a.length)[0]

  return match ? ROUTE_TITLES[match] : 'Tradewell'
}

interface AppShellProps {
  children?: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const pageTitle = deriveTitle(location.pathname)

  return (
    <div className="flex min-h-screen h-screen bg-background overflow-hidden">
      {/* Desktop sidebar — hidden on mobile */}
      <div className="hidden md:flex">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      </div>

      {/* Main content area — flex column so header stacks above page content */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Sticky top header */}
        <TopHeader title={pageTitle} />

        {/* Scrollable page content */}
        <main className="flex-1 overflow-y-auto pb-16 md:pb-0">
          {children}
        </main>
      </div>

      {/* Mobile bottom tab navigation */}
      <MobileNav />

      {/* Floating AI assistant — available on every page */}
      <AssistantWidget />
    </div>
  )
}
