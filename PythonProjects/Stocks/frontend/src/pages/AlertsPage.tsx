import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { toast } from 'sonner'
import { BellOff, CheckCheck, AlertTriangle, Info, AlertCircle, X } from 'lucide-react'
import { GlassCard, SkeletonPulse, PageTransition } from '@/components/common'
import { getAlerts, dismissAlert, markAllAlertsRead } from '@/api/alerts'
import type { Alert } from '@/api/alerts'
import { useAlertStore } from '@/store/alertStore'
import { queryKeys } from '@/api/queryKeys'

// Alert card animation variants (from design document)
const alertCardVariants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit:    { opacity: 0, x: 20, transition: { duration: 0.2 } },
}

const alertCardTransition = { duration: 0.2, ease: 'easeOut' as const }

// Severity icon mapping
function SeverityIcon({ severity }: { severity: Alert['severity'] }) {
  switch (severity) {
    case 'critical':
      return <AlertCircle className="h-4 w-4 text-red-400 shrink-0" aria-hidden="true" />
    case 'warning':
      return <AlertTriangle className="h-4 w-4 text-yellow-400 shrink-0" aria-hidden="true" />
    default:
      return <Info className="h-4 w-4 text-blue-400 shrink-0" aria-hidden="true" />
  }
}

// Severity label colours
function severityBadgeClasses(severity: Alert['severity']): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-500/15 text-red-400 border border-red-500/30'
    case 'warning':
      return 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30'
    default:
      return 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
  }
}

// Relative timestamp
function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export default function AlertsPage() {
  const queryClient = useQueryClient()
  const alertStore = useAlertStore()

  // Local state for optimistically hidden alert IDs
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(new Set())

  // ----- Query -----
  const {
    data: alerts,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: queryKeys.alerts.list(),
    queryFn: getAlerts,
    staleTime: 0,
    refetchInterval: 30_000,
  })

  // After each successful fetch, sync unread count into the alert store
  useEffect(() => {
    if (alerts !== undefined) {
      const unreadCount = alerts.filter((a) => !a.is_read).length
      alertStore.setUnreadCount(unreadCount)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alerts])

  // ----- Dismiss mutation -----
  const dismissMutation = useMutation({
    mutationFn: dismissAlert,
    onMutate: (id: string) => {
      // Optimistically hide the card
      setHiddenIds((prev) => new Set(prev).add(id))
    },
    onSuccess: (_data, _id) => {
      alertStore.decrementUnread()
      // Invalidate to sync server state
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.list() })
      // Keep the card hidden (it's been dismissed)
    },
    onError: (_error, id) => {
      // Restore the card on failure
      setHiddenIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
      toast.error('Failed to dismiss alert. Please try again.')
    },
  })

  // ----- Mark all read mutation -----
  const markAllMutation = useMutation({
    mutationFn: markAllAlertsRead,
    onSuccess: () => {
      alertStore.clearUnread()
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.list() })
      toast.success('All alerts marked as read.')
    },
    onError: () => {
      toast.error('Failed to mark all alerts as read. Please try again.')
    },
  })

  // Visible alerts = fetched alerts minus optimistically hidden ones
  const visibleAlerts = (alerts ?? []).filter((a) => !hiddenIds.has(a.id))
  const hasUnread = visibleAlerts.some((a) => !a.is_read)

  // ----- Loading skeleton -----
  if (isLoading) {
    return (
      <PageTransition>
        <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl space-y-6">
            <header>
              <h1 className="text-2xl font-bold text-[#f1f5f9]">Alerts</h1>
              <p className="mt-1 text-sm text-[#475569]">Your active market alerts</p>
            </header>
            <div className="space-y-3" role="status" aria-label="Loading alerts">
              {Array.from({ length: 5 }).map((_, i) => (
                <SkeletonPulse key={i} className="h-20 w-full" />
              ))}
            </div>
          </div>
        </main>
      </PageTransition>
    )
  }

  // ----- Error state -----
  if (isError) {
    return (
      <PageTransition>
        <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl space-y-6">
            <header>
              <h1 className="text-2xl font-bold text-[#f1f5f9]">Alerts</h1>
            </header>
            <div className="flex flex-col items-center justify-center rounded-xl border border-[#1f2d40] bg-[#111827] py-16 text-center">
              <AlertTriangle className="mb-3 h-10 w-10 text-[#475569]" aria-hidden="true" />
              <p className="text-sm text-[#94a3b8]">Unable to load alerts.</p>
              <button
                onClick={() => refetch()}
                className="mt-4 rounded-lg bg-[#6366f1] px-4 py-2 text-sm font-medium text-white hover:bg-[#818cf8] transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </main>
      </PageTransition>
    )
  }

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl space-y-6">

          {/* Page header */}
          <header className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-[#f1f5f9]">Alerts</h1>
              <p className="mt-1 text-sm text-[#475569]">
                {visibleAlerts.length > 0
                  ? `${visibleAlerts.length} active alert${visibleAlerts.length !== 1 ? 's' : ''}`
                  : 'Your active market alerts'}
              </p>
            </div>

            {/* Mark all read button */}
            {hasUnread && (
              <button
                onClick={() => markAllMutation.mutate()}
                disabled={markAllMutation.isPending}
                className="flex items-center gap-2 rounded-lg border border-[#1f2d40] bg-[#111827] px-3 py-2 text-sm text-[#94a3b8] hover:border-[#6366f1]/40 hover:text-[#f1f5f9] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Mark all alerts as read"
              >
                <CheckCheck className="h-4 w-4" aria-hidden="true" />
                {markAllMutation.isPending ? 'Marking…' : 'Mark all read'}
              </button>
            )}
          </header>

          {/* Alert list */}
          {visibleAlerts.length === 0 ? (
            /* Empty state */
            <div className="flex flex-col items-center justify-center rounded-xl border border-[#1f2d40] bg-[#111827] py-20 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[#1a2235]">
                <BellOff className="h-8 w-8 text-[#475569]" aria-hidden="true" />
              </div>
              <p className="text-base font-semibold text-[#94a3b8]">No active alerts.</p>
              <p className="mt-1 text-sm text-[#475569]">
                You're all caught up. Alerts will appear here as they arrive.
              </p>
            </div>
          ) : (
            <div className="space-y-3" role="list" aria-label="Alert list">
              <AnimatePresence mode="sync" initial={false}>
                {visibleAlerts.map((alert) => (
                  <motion.div
                    key={alert.id}
                    variants={alertCardVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    transition={alertCardTransition}
                    role="listitem"
                    layout
                  >
                    <AlertCard
                      alert={alert}
                      onDismiss={() => dismissMutation.mutate(alert.id)}
                      isDismissing={
                        dismissMutation.isPending &&
                        dismissMutation.variables === alert.id
                      }
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}

        </div>
      </main>
    </PageTransition>
  )
}

// ---- AlertCard sub-component ----

interface AlertCardProps {
  alert: Alert
  onDismiss: () => void
  isDismissing: boolean
}

function AlertCard({ alert, onDismiss, isDismissing }: AlertCardProps) {
  const isCritical = alert.severity === 'critical'

  return (
    <GlassCard
      noHover
      className={[
        'p-4',
        // Critical alerts: red left border
        isCritical ? 'border-l-4 border-l-red-500' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="flex items-start gap-3">
        {/* Left: severity icon + critical pulsing dot */}
        <div className="relative mt-0.5">
          <SeverityIcon severity={alert.severity} />
          {isCritical && (
            <span
              className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-red-500 animate-ping"
              aria-hidden="true"
            />
          )}
        </div>

        {/* Middle: content */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {/* Ticker */}
            <span className="text-sm font-bold text-[#6366f1] tracking-wide">
              {alert.ticker}
            </span>
            {/* Severity badge */}
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${severityBadgeClasses(alert.severity)}`}
            >
              {alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1)}
            </span>
            {/* Alert type */}
            {alert.alert_type && (
              <span className="text-xs text-[#475569]">{alert.alert_type}</span>
            )}
            {/* Read status indicator */}
            {!alert.is_read && (
              <span
                className="h-1.5 w-1.5 rounded-full bg-[#6366f1] shrink-0"
                aria-label="Unread"
              />
            )}
          </div>

          {/* Message */}
          <p className="mt-1 text-sm text-[#cbd5e1] leading-relaxed">
            {alert.message}
          </p>

          {/* Timestamp */}
          <p className="mt-1.5 text-xs text-[#475569]">
            <time dateTime={alert.timestamp}>{relativeTime(alert.timestamp)}</time>
          </p>
        </div>

        {/* Right: dismiss button */}
        <button
          onClick={onDismiss}
          disabled={isDismissing}
          className="ml-2 shrink-0 rounded-md p-1 text-[#475569] hover:bg-[#1a2235] hover:text-[#f1f5f9] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label={`Dismiss alert for ${alert.ticker}`}
          title="Dismiss"
        >
          {isDismissing ? (
            <span className="block h-4 w-4 animate-spin rounded-full border-2 border-[#475569] border-t-transparent" />
          ) : (
            <X className="h-4 w-4" aria-hidden="true" />
          )}
        </button>
      </div>
    </GlassCard>
  )
}
