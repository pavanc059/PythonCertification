import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Shield, Users, Activity, TrendingUp, Bot,
  ChevronLeft, ChevronRight, Crown, UserX, RefreshCw,
} from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import { GlassCard, SkeletonPulse } from '@/components/common'
import {
  getAdminUsers, getAdminActivity, getPlatformStats, setUserRole,
  type AdminUser,
} from '@/api/admin'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function relativeTime(iso: string | null) {
  if (!iso) return 'never'
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

const CATEGORY_COLOURS: Record<string, string> = {
  auth:      'bg-blue-500/10 text-blue-400',
  trading:   'bg-green-500/10 text-green-400',
  autotrade: 'bg-[#6366f1]/10 text-[#818cf8]',
  autopilot: 'bg-amber-500/10 text-amber-400',
  watchlist: 'bg-cyan-500/10 text-cyan-400',
  system:    'bg-red-500/10 text-red-400',
}

const PAGE_SIZE = 50

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, icon: Icon, colour }: {
  label: string; value: string | number; sub?: string
  icon: React.ElementType; colour: string
}) {
  return (
    <GlassCard noHover className="p-4 flex items-start gap-3">
      <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-xl', colour)}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs text-[#475569]">{label}</p>
        <p className="text-xl font-bold text-[#f1f5f9] tabular-nums">{value}</p>
        {sub && <p className="text-[10px] text-[#475569] mt-0.5">{sub}</p>}
      </div>
    </GlassCard>
  )
}

// ─── Page tabs ────────────────────────────────────────────────────────────────

type Tab = 'overview' | 'users' | 'activity'

// ─── Users table ─────────────────────────────────────────────────────────────

function UsersPanel() {
  const qc = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const [page, setPage] = useState(0)

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'users', page],
    queryFn: () => getAdminUsers({ limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    staleTime: 30_000,
  })

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: 'user' | 'admin' }) => setUserRole(id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <div className="space-y-4">
      <GlassCard noHover className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1f2d40] bg-[#111827]">
                {['User', 'Role', 'Status', 'Last Login', 'Trades', 'Actions'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wide text-[#475569]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f2d40]">
              {isLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}><td colSpan={6} className="px-4 py-3"><SkeletonPulse className="h-4 w-full" /></td></tr>
                ))
                : data?.users.map((user: AdminUser) => (
                  <tr key={user.id} className="hover:bg-[#111827]/60 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-[#f1f5f9]">{user.name}</p>
                      <p className="text-[11px] text-[#475569]">{user.email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        'text-[10px] font-bold px-2 py-0.5 rounded-full',
                        user.role === 'admin'
                          ? 'bg-amber-500/15 text-amber-400'
                          : 'bg-[#1f2d40] text-[#94a3b8]',
                      )}>
                        {user.role === 'admin' ? '⭐ Admin' : 'User'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn('text-[10px] px-2 py-0.5 rounded-full',
                        user.is_active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                      )}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-[#94a3b8] tabular-nums">
                      {relativeTime(user.last_login_at)}
                    </td>
                    <td className="px-4 py-3 text-xs text-[#94a3b8] tabular-nums">
                      {user.trade_count}
                    </td>
                    <td className="px-4 py-3">
                      {user.id !== currentUser?.id && (
                        <button
                          type="button"
                          onClick={() => roleMutation.mutate({
                            id: user.id,
                            role: user.role === 'admin' ? 'user' : 'admin',
                          })}
                          disabled={roleMutation.isPending}
                          className={cn(
                            'flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded-lg transition-colors',
                            user.role === 'admin'
                              ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                              : 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20',
                          )}
                        >
                          {user.role === 'admin'
                            ? <><UserX className="h-3 w-3" />Demote</>
                            : <><Crown className="h-3 w-3" />Make Admin</>}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-[#475569]">
          <span>Page {page + 1} of {totalPages} · {data?.total} users</span>
          <div className="flex gap-2">
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#1f2d40] hover:bg-[#1f2d40] disabled:opacity-40">
              <ChevronLeft className="h-3.5 w-3.5" />Prev
            </button>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#1f2d40] hover:bg-[#1f2d40] disabled:opacity-40">
              Next<ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Activity panel ───────────────────────────────────────────────────────────

function AdminActivityPanel() {
  const [page, setPage] = useState(0)
  const [category, setCategory] = useState<string | undefined>()

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['admin', 'activity', page, category],
    queryFn: () => getAdminActivity({ limit: PAGE_SIZE, offset: page * PAGE_SIZE, category }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0
  const categories = ['auth', 'trading', 'autotrade', 'autopilot', 'watchlist', 'system']

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => { setCategory(undefined); setPage(0) }}
          className={cn('px-3 py-1 rounded-lg text-xs border transition-colors',
            !category ? 'bg-[#6366f1] border-[#6366f1] text-white' : 'border-[#1f2d40] text-[#94a3b8] hover:bg-[#1f2d40]')}>
          All
        </button>
        {categories.map((cat) => (
          <button key={cat} onClick={() => { setCategory(cat); setPage(0) }}
            className={cn('px-3 py-1 rounded-lg text-xs border capitalize transition-colors',
              category === cat ? 'bg-[#6366f1] border-[#6366f1] text-white' : 'border-[#1f2d40] text-[#94a3b8] hover:bg-[#1f2d40]')}>
            {cat}
          </button>
        ))}
        <button onClick={() => refetch()} disabled={isFetching}
          className="ml-auto flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-[#94a3b8] border border-[#1f2d40] hover:bg-[#1f2d40]">
          <RefreshCw className={cn('h-3 w-3', isFetching && 'animate-spin')} />Refresh
        </button>
      </div>

      <GlassCard noHover className="overflow-hidden p-0 divide-y divide-[#1f2d40]">
        {isLoading
          ? Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <SkeletonPulse className="h-7 w-7 rounded-full" />
              <div className="flex-1 space-y-1">
                <SkeletonPulse className="h-4 w-3/4" />
                <SkeletonPulse className="h-3 w-1/4" />
              </div>
            </div>
          ))
          : !data?.items.length
            ? <div className="p-8 text-center text-sm text-[#475569]">No activity yet.</div>
            : data.items.map((ev) => (
              <div key={ev.id} className="flex items-start gap-3 px-4 py-3 hover:bg-[#111827]/60">
                <span className={cn('mt-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0',
                  CATEGORY_COLOURS[ev.category] ?? 'bg-[#1f2d40] text-[#94a3b8]')}>
                  {ev.category}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[#e2e8f0]">{ev.description}</p>
                  <p className="text-[10px] text-[#475569] mt-0.5">{ev.user_email}</p>
                </div>
                <p className="text-[10px] text-[#475569] shrink-0">{relativeTime(ev.created_at)}</p>
              </div>
            ))}
      </GlassCard>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-[#475569]">
          <span>Page {page + 1} of {totalPages} · {data?.total.toLocaleString()} events</span>
          <div className="flex gap-2">
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#1f2d40] hover:bg-[#1f2d40] disabled:opacity-40">
              <ChevronLeft className="h-3.5 w-3.5" />Prev
            </button>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#1f2d40] hover:bg-[#1f2d40] disabled:opacity-40">
              Next<ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>('overview')
  const user = useAuthStore((s) => s.user)

  // Guard: redirect non-admins at component level
  if (!user || (user as { role?: string }).role !== 'admin') {
    return (
      <PageTransition>
        <div className="flex items-center justify-center min-h-full p-12 text-center">
          <div>
            <Shield className="mx-auto h-12 w-12 text-[#1f2d40] mb-3" />
            <p className="text-sm text-[#475569]">Admin access required.</p>
          </div>
        </div>
      </PageTransition>
    )
  }

  const { data: stats } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: getPlatformStats,
    staleTime: 60_000,
    refetchInterval: 120_000,
  })

  const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'overview', label: 'Overview', icon: Shield },
    { id: 'users',    label: 'Users',    icon: Users },
    { id: 'activity', label: 'Activity', icon: Activity },
  ]

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl space-y-6">

          {/* Header */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/15">
              <Shield className="h-5 w-5 text-amber-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#f1f5f9]">Admin Dashboard</h1>
              <p className="text-xs text-[#475569]">Platform management — admin only</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 border-b border-[#1f2d40]">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px',
                  tab === id
                    ? 'border-[#6366f1] text-[#f1f5f9]'
                    : 'border-transparent text-[#475569] hover:text-[#94a3b8]',
                )}
              >
                <Icon className="h-4 w-4" />{label}
              </button>
            ))}
          </div>

          {/* Overview */}
          {tab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <StatCard label="Total Users" value={stats?.users.total ?? '—'}
                  sub={`${stats?.users.active ?? 0} active`}
                  icon={Users} colour="bg-[#6366f1]/15 text-[#6366f1]" />
                <StatCard label="Filled Orders" value={stats?.orders.filled ?? '—'}
                  sub={`${stats?.orders.total ?? 0} total`}
                  icon={TrendingUp} colour="bg-green-500/15 text-green-400" />
                <StatCard label="Active Bots" value={stats?.automation.active_bots ?? '—'}
                  sub={`${stats?.automation.active_autopilots ?? 0} AutoPilots`}
                  icon={Bot} colour="bg-amber-500/15 text-amber-400" />
                <StatCard label="Activity Events" value={stats?.activity.total_events?.toLocaleString() ?? '—'}
                  sub="all time"
                  icon={Activity} colour="bg-cyan-500/15 text-cyan-400" />
              </div>
            </div>
          )}

          {tab === 'users' && <UsersPanel />}
          {tab === 'activity' && <AdminActivityPanel />}
        </div>
      </main>
    </PageTransition>
  )
}
