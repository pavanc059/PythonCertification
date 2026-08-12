import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Settings2, Server, Code2, FileText, Zap, Brain, Database, AlertTriangle } from 'lucide-react'
import { GlassCard, SkeletonPulse, PageTransition } from '@/components/common'
import { getSettings, patchSettings } from '@/api/settings'
import type { AppSettings } from '@/api/settings'
import { queryKeys } from '@/api/queryKeys'

// ---- Feature flag configuration ----

interface FeatureFlagConfig {
  key: keyof AppSettings['feature_flags']
  label: string
  description: string
  icon: React.ElementType
}

const FEATURE_FLAGS: FeatureFlagConfig[] = [
  {
    key: 'real_time_streaming',
    label: 'Real-Time Streaming',
    description:
      'Subscribe to live WebSocket price feeds on the Stock Detail page. ' +
      'When off, prices still refresh automatically every 30 seconds via polling. ' +
      'Requires a working WebSocket connection to the backend.',
    icon: Zap,
  },
  {
    key: 'deep_learning',
    label: 'Deep Learning',
    description:
      'Enrich AI predictions with LLM analysis of recent news headlines. ' +
      'The LLM adjusts each prediction\'s confidence score based on sentiment, ' +
      'and writes a plain-English reason shown on every prediction card. ' +
      'Requires GROQ_API_KEY or OPENAI_API_KEY to be configured.',
    icon: Brain,
  },
  {
    key: 'alternative_data',
    label: 'Alternative Data',
    description:
      'Pull news and sentiment from Finnhub and AlphaVantage APIs in addition ' +
      'to the free yfinance feed. Provides richer news coverage and per-ticker ' +
      'sentiment scores for AI predictions and the news feed. ' +
      'Requires FINNHUB_API_KEY and ALPHAVANTAGE_API_KEY to be configured.',
    icon: Database,
  },
]

// ---- Info card configuration ----

interface InfoField {
  key: keyof Omit<AppSettings, 'feature_flags'>
  label: string
  icon: React.ElementType
}

const INFO_FIELDS: InfoField[] = [
  { key: 'app_env',     label: 'Environment',   icon: Server   },
  { key: 'api_version', label: 'API Version',   icon: Code2    },
  { key: 'log_level',   label: 'Log Level',     icon: FileText },
]

// ---- Toggle component ----

interface ToggleSwitchProps {
  id: string
  checked: boolean
  disabled: boolean
  onChange: (newValue: boolean) => void
}

function ToggleSwitch({ id, checked, disabled, onChange }: ToggleSwitchProps) {
  return (
    <button
      id={id}
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={[
        'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6366f1]',
        checked ? 'bg-[#6366f1]' : 'bg-[#1a2235]',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
      ]
        .filter(Boolean)
        .join(' ')}
      aria-label={`Toggle ${id}`}
    >
      <span
        className={[
          'inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform duration-200',
          checked ? 'translate-x-6' : 'translate-x-1',
        ].join(' ')}
      />
    </button>
  )
}

// ---- Main page ----

export default function SettingsPage() {
  const queryClient = useQueryClient()

  // Track which flags are in-flight so we can disable just those toggles
  const [pendingFlags, setPendingFlags] = useState<Set<keyof AppSettings['feature_flags']>>(
    new Set()
  )

  // ----- Query -----
  const {
    data: settings,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: queryKeys.settings.config(),
    queryFn: getSettings,
    staleTime: 300_000,
  })

  // ----- Mutation -----
  const patchMutation = useMutation({
    mutationFn: (vars: { flagKey: keyof AppSettings['feature_flags']; patch: Partial<AppSettings['feature_flags']> }) =>
      patchSettings(vars.patch),
    onMutate: (vars) => {
      setPendingFlags((prev) => new Set(prev).add(vars.flagKey))
    },
    onSuccess: (updatedSettings, vars) => {
      // Persist the new settings into the query cache so UI reflects truth
      queryClient.setQueryData(queryKeys.settings.config(), updatedSettings)
      setPendingFlags((prev) => {
        const next = new Set(prev)
        next.delete(vars.flagKey)
        return next
      })
      toast.success(`${FEATURE_FLAGS.find((f) => f.key === vars.flagKey)?.label ?? 'Setting'} updated.`)
    },
    onError: (_err, vars) => {
      // Revert: invalidate so the query re-fetches the original value from the server
      queryClient.invalidateQueries({ queryKey: queryKeys.settings.config() })
      setPendingFlags((prev) => {
        const next = new Set(prev)
        next.delete(vars.flagKey)
        return next
      })
      toast.error(`Failed to update setting. Change has been reverted.`)
    },
  })

  const handleToggle = (flagKey: keyof AppSettings['feature_flags'], newValue: boolean) => {
    patchMutation.mutate({ flagKey, patch: { [flagKey]: newValue } })
  }

  // ----- Loading skeleton -----
  if (isLoading) {
    return (
      <PageTransition>
        <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl space-y-8">
            <header>
              <h1 className="text-2xl font-bold text-[#f1f5f9]">Settings</h1>
              <p className="mt-1 text-sm text-[#475569]">Application configuration</p>
            </header>

            {/* System info skeletons */}
            <section aria-label="Loading system info" className="space-y-3">
              <SkeletonPulse className="h-5 w-32" />
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <SkeletonPulse key={i} className="h-20 w-full" />
                ))}
              </div>
            </section>

            {/* Feature flag skeletons */}
            <section aria-label="Loading feature flags" className="space-y-3">
              <SkeletonPulse className="h-5 w-40" />
              {Array.from({ length: 3 }).map((_, i) => (
                <SkeletonPulse key={i} className="h-20 w-full" />
              ))}
            </section>
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
          <div className="mx-auto max-w-2xl">
            <header className="mb-6">
              <h1 className="text-2xl font-bold text-[#f1f5f9]">Settings</h1>
            </header>
            <div className="flex flex-col items-center justify-center rounded-xl border border-[#1f2d40] bg-[#111827] py-16 text-center">
              <AlertTriangle className="mb-3 h-10 w-10 text-[#475569]" aria-hidden="true" />
              <p className="text-sm text-[#94a3b8]">Unable to load settings.</p>
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

  const featureFlags = settings!.feature_flags

  return (
    <PageTransition>
      <main className="min-h-full bg-[#0a0e1a] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl space-y-8">

          {/* Page header */}
          <header className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#1a2235]">
              <Settings2 className="h-5 w-5 text-[#6366f1]" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#f1f5f9]">Settings</h1>
              <p className="text-sm text-[#475569]">Application configuration</p>
            </div>
          </header>

          {/* ---- System Information ---- */}
          <section aria-labelledby="system-info-heading">
            <h2
              id="system-info-heading"
              className="mb-3 text-xs font-semibold uppercase tracking-widest text-[#475569]"
            >
              System Information
            </h2>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {INFO_FIELDS.map(({ key, label, icon: Icon }) => (
                <GlassCard key={key} noHover className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className="h-4 w-4 text-[#6366f1] shrink-0" aria-hidden="true" />
                    <span className="text-xs font-medium uppercase tracking-wide text-[#475569]">
                      {label}
                    </span>
                  </div>
                  <p
                    className="text-sm font-semibold text-[#f1f5f9] truncate"
                    title={settings![key]}
                  >
                    {settings![key] || '—'}
                  </p>
                </GlassCard>
              ))}
            </div>
          </section>

          {/* ---- Feature Flags ---- */}
          <section aria-labelledby="feature-flags-heading">
            <h2
              id="feature-flags-heading"
              className="mb-3 text-xs font-semibold uppercase tracking-widest text-[#475569]"
            >
              Feature Flags
            </h2>

            <div className="space-y-3">
              {FEATURE_FLAGS.map(({ key, label, description, icon: Icon }) => {
                const isEnabled = featureFlags[key]
                const isDisabled = pendingFlags.has(key)

                return (
                  <GlassCard key={key} noHover className="p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-start gap-3 min-w-0">
                        <div
                          className={[
                            'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors duration-200',
                            isEnabled ? 'bg-[#6366f1]/15' : 'bg-[#1a2235]',
                          ].join(' ')}
                        >
                          <Icon
                            className={[
                              'h-4 w-4 transition-colors duration-200',
                              isEnabled ? 'text-[#6366f1]' : 'text-[#475569]',
                            ].join(' ')}
                            aria-hidden="true"
                          />
                        </div>

                        <div className="min-w-0">
                          <label
                            htmlFor={`flag-${key}`}
                            className="block text-sm font-semibold text-[#f1f5f9] cursor-pointer"
                          >
                            {label}
                          </label>
                          <p className="mt-0.5 text-xs text-[#475569] leading-relaxed">
                            {description}
                          </p>
                        </div>
                      </div>

                      <div className="flex shrink-0 items-center gap-2">
                        {/* Pending spinner */}
                        {isDisabled && (
                          <span
                            className="block h-4 w-4 animate-spin rounded-full border-2 border-[#475569] border-t-[#6366f1]"
                            aria-hidden="true"
                          />
                        )}

                        <ToggleSwitch
                          id={`flag-${key}`}
                          checked={isEnabled}
                          disabled={isDisabled}
                          onChange={(newValue) => handleToggle(key, newValue)}
                        />
                      </div>
                    </div>

                    {/* Status label */}
                    <div className="mt-3 flex items-center gap-1.5 pl-11">
                      <span
                        className={[
                          'inline-block h-1.5 w-1.5 rounded-full',
                          isEnabled ? 'bg-green-400' : 'bg-[#475569]',
                        ].join(' ')}
                        aria-hidden="true"
                      />
                      <span className="text-xs text-[#475569]">
                        {isDisabled ? 'Updating…' : isEnabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                  </GlassCard>
                )
              })}
            </div>
          </section>

        </div>
      </main>
    </PageTransition>
  )
}
