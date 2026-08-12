import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity, LogIn, TrendingUp, Bot, Gauge, Bookmark,
  ShieldAlert, RefreshCw, ChevronLeft, ChevronRight,
} from 'lucide-react'
import { PageTransition } from '@/components/common/PageTransition'
import { GlassCard, SkeletonPulse } from '@/components/common'
import { getActivityFeed, type ActivityEvent } from '@/api/activity'
import { cn } from '@/lib/utils'

// ─── Category config (icon + colour) ─────────────────────────────────────────

const CATEGORY_CONFIG: Record<string, { icon: React.ElementType; colour: string; label: string }> = {
  auth:       { icon: LogIn,      colour: 'text-blue-400 bg-blue-500/10',    label: 'Auth' },
  trading:    { icon: TrendingUp, colour: 'text-green-400 bg-green-500/10',  label: 'Trading' },
  autotrade:  { icon: Bot,        colour: 'text-[#6366f1] bg-[#6366f1]/10',  label: 'AutoTrade' },
  autopilot:  { icon: Gauge,      colour: 'text-amber-400 bg-amber-500/10',  label: 'AutoPilot' },
  watchlist:  { icon: Bookmark,   colour: 'text-cyan-400 bg-cyan-500/10',    label: 'Watchlist' },
  system:     { icon: ShieldAlert, colour: 'text-red-400 bg-red-500/10',     label: 'System' },
}

const ALL_CATEGORIES = ['all', ...Object.keys(CATEGORY_CONFIG)]

function categoryConfig(cat: string) {
  return CATEGORY_CONFIG[cat] ?? { icon: Activity, colour: 'text-[#94a3b8] bg-[#1f2d40]', label: cat }
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

const PAGE_SIZE = 30

// ─── Event row ────────────────────────────────────────────────────────────────

function EventRow({ event }: { event: ActivityEvent }) {
  const cfg = categoryConfig(event.category)
  const Icon = cfg.icon
  return (
    <div className="flex items-start gap-3 px-4 py-3 hover:bg-[#111827]/60 transition-colors">
      <div className={cn('mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full', cfg.colour)}>
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[#e2e8f0] leading-snug">{event.description}</p>
        {Object.keys(event.metadata ?? {}).length > 0 && (
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
            {Object.entries(event.metadata ?? {}).slice(0, 4).map(([k, v]) => {
              if (k === 'ts' || k === 'email') return null
              return (
                <span key={k} className="text-[10px] text-[#475569]">
                  {k}: <span className="text-[#94a3b8]">{String(v)}</span>
                </span>
              )
            })}
          </div>
        )}
      </div>
      <div className="shrink-0 text-right">
        <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded', cfg.colour)}>
          {cfg.label}
        </span>
        <p className="mt-0.5 text-[10px] text-[#475569]">{relativeTime(event.created_at)}</p>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ActivityPage() {
  const [category, setCategory] = useState('all')
  const [page, setPage] = useState(0)
  const offset = page * PAGE_SIZE

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['activity', 'feed', category, offset],
    queryFn: () => getActivityFeed({
      limit: PAGE_SIZE,
      offset,
      category: category === 'all' ? undefined : category,
    }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl space-y-5">

          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#6366f1]/15">
                <Activity className="h-5 w-5 text-[#6366f1]" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-[#f1f5f9]">Activity Log</h1>
                <p className="text-xs text-[#475569]">
                  {data ? `${data.total.toLocaleString()} events` : 'Your full audit trail'}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-[#94a3b8] border border-[#1f2d40] hover:bg-[#1f2d40] transition-colors disabled:opacity-50"
            >
              <RefreshCw className={cn('h-3.5 w-3.5', isFetching && 'animate-spin')} />
              Refresh
            </button>
          </div>

          {/* Category filter */}
          <div className="flex flex-wrap gap-1.5">
            {ALL_CATEGORIES.map((cat) => {
              const cfg = cat === 'all'
                ? { label: 'All', colour: 'text-[#94a3b8]' }
                : categoryConfig(cat)
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => { setCategory(cat); setPage(0) }}
                  className={cn(
                    'px-3 py-1 rounded-lg text-xs font-medium border transition-colors capitalize',
                    category === cat
                      ? 'bg-[#6366f1] border-[#6366f1] text-white'
                      : 'border-[#1f2d40] text-[#94a3b8] hover:bg-[#1f2d40]',
                  )}
                >
                  {cfg.label ?? cat}
                </button>
              )
            })}
          </div>

          {/* Event list */}
          <GlassCard noHover className="overflow-hidden p-0 divide-y divide-[#1f2d40]">
            {isLoading ? (
              <div className="p-4 space-y-3">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <SkeletonPulse className="h-7 w-7 rounded-full" />
                    <div className="flex-1 space-y-1">
                      <SkeletonPulse className="h-4 w-3/4" />
                      <SkeletonPulse className="h-3 w-1/3" />
                    </div>
                  </div>
                ))}
              </div>
            ) : isError ? (
              <div className="p-8 text-center text-sm text-[#475569]">
                Failed to load activity. <button className="text-[#6366f1] hover:underline" onClick={() => refetch()}>Retry</button>
              </div>
            ) : !data?.items.length ? (
              <div className="p-12 text-center">
                <Activity className="mx-auto h-10 w-10 text-[#1f2d40] mb-3" />
                <p className="text-sm text-[#475569]">No activity yet.</p>
                <p className="text-xs text-[#334155] mt-1">Events will appear here as you use the app.</p>
              </div>
            ) : (
              data.items.map((event) => <EventRow key={event.id} event={event} />)
            )}
          </GlassCard>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between text-sm text-[#475569]">
              <span>Page {page + 1} of {totalPages}</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#1f2d40] hover:bg-[#1f2d40] disabled:opacity-40 transition-colors"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />Prev
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#1f2d40] hover:bg-[#1f2d40] disabled:opacity-40 transition-colors"
                >
                  Next<ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}

        </div>
      </main>
    </PageTransition>
  )
}
