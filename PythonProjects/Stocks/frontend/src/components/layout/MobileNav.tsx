import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Newspaper, Zap, Rss, BellRing } from 'lucide-react'
import { cn } from '@/lib/utils'

const tabs = [
  { path: '/dashboard',    icon: LayoutDashboard, label: 'Home' },
  { path: '/market',       icon: Newspaper,       label: 'Market' },
  { path: '/penny-stocks', icon: Zap,             label: 'Penny' },
  { path: '/news',         icon: Rss,             label: 'News' },
  { path: '/alerts',       icon: BellRing,        label: 'Alerts' },
]

export function MobileNav() {
  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 bg-card border-t border-border z-50"
      aria-label="Mobile navigation"
    >
      <div className="flex">
        {tabs.map(({ path, icon: Icon, label }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              cn(
                'flex-1 flex flex-col items-center py-3 text-xs font-medium transition-colors',
                isActive ? 'text-primary' : 'text-muted-foreground'
              )
            }
          >
            <Icon size={20} />
            <span className="mt-1">{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
