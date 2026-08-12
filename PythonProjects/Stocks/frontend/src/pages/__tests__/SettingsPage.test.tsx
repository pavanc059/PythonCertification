import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import SettingsPage from '../SettingsPage'

// ---- Mock @/api/settings ----
vi.mock('@/api/settings', () => ({
  getSettings: vi.fn(),
  patchSettings: vi.fn(),
}))

// ---- Mock sonner ----
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

// ---- Mock framer-motion to avoid animation issues in jsdom ----
vi.mock('framer-motion', () => ({
  motion: {
    div: ({
      children,
      whileHover: _wh,
      whileTap: _wt,
      initial: _i,
      animate: _a,
      exit: _e,
      transition: _t,
      variants: _v,
      ...props
    }: React.HTMLAttributes<HTMLDivElement> & Record<string, unknown>) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

import { getSettings, patchSettings } from '@/api/settings'
import { toast } from 'sonner'

const mockGetSettings = getSettings as ReturnType<typeof vi.fn>
const mockPatchSettings = patchSettings as ReturnType<typeof vi.fn>
const mockToastSuccess = toast.success as ReturnType<typeof vi.fn>
const mockToastError = toast.error as ReturnType<typeof vi.fn>

const MOCK_SETTINGS = {
  app_env: 'development',
  api_version: '1.0.0',
  log_level: 'info',
  feature_flags: {
    real_time_streaming: false,
    deep_learning: false,
    alternative_data: false,
  },
}

function renderSettingsPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        // No stale time so query fires immediately in tests
        staleTime: 0,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('SettingsPage – toggle interactions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetSettings.mockResolvedValue(MOCK_SETTINGS)
  })

  // ------------------------------------------------------------------
  // Requirement 12.4 – toggle change fires PATCH and disables during flight
  // ------------------------------------------------------------------
  describe('toggle change triggers PATCH and disables toggle during in-flight request', () => {
    it('calls patchSettings with the new flag value when a toggle is clicked', async () => {
      // Resolve after a short delay so we can observe the pending state
      let resolvePatch!: (value: typeof MOCK_SETTINGS) => void
      mockPatchSettings.mockReturnValue(
        new Promise<typeof MOCK_SETTINGS>((resolve) => {
          resolvePatch = resolve
        })
      )

      renderSettingsPage()

      // Wait for settings to load
      const toggle = await screen.findByRole('switch', { name: /toggle flag-real_time_streaming/i })
      expect(toggle).toBeInTheDocument()

      // Initially enabled (not disabled)
      expect(toggle).not.toBeDisabled()

      // Click the toggle
      await userEvent.click(toggle)

      // patchSettings should have been called
      expect(mockPatchSettings).toHaveBeenCalledTimes(1)
      expect(mockPatchSettings).toHaveBeenCalledWith({ real_time_streaming: true })

      // Toggle should now be disabled while request is in flight
      expect(toggle).toBeDisabled()

      // Resolve the request
      resolvePatch({ ...MOCK_SETTINGS, feature_flags: { ...MOCK_SETTINGS.feature_flags, real_time_streaming: true } })

      // Toggle becomes enabled again after success
      await waitFor(() => expect(toggle).not.toBeDisabled())
    })

    it('toggle is re-enabled and toast.success is called after successful PATCH', async () => {
      const updatedSettings = {
        ...MOCK_SETTINGS,
        feature_flags: { ...MOCK_SETTINGS.feature_flags, real_time_streaming: true },
      }
      mockPatchSettings.mockResolvedValue(updatedSettings)

      renderSettingsPage()

      const toggle = await screen.findByRole('switch', { name: /toggle flag-real_time_streaming/i })
      await userEvent.click(toggle)

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalledTimes(1)
        expect(mockToastSuccess).toHaveBeenCalledWith(expect.stringContaining('Real-Time Streaming'))
      })

      expect(toggle).not.toBeDisabled()
    })
  })

  // ------------------------------------------------------------------
  // Requirement 12.5 – PATCH failure reverts toggle + shows error toast
  // ------------------------------------------------------------------
  describe('PATCH failure reverts toggle and shows error toast', () => {
    it('calls toast.error and re-enables toggle when patchSettings rejects', async () => {
      mockPatchSettings.mockRejectedValue(new Error('Network error'))

      renderSettingsPage()

      const toggle = await screen.findByRole('switch', { name: /toggle flag-real_time_streaming/i })

      await userEvent.click(toggle)

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledTimes(1)
        expect(mockToastError).toHaveBeenCalledWith(
          expect.stringContaining('Failed to update setting')
        )
      })

      // Toggle should be re-enabled after the error
      expect(toggle).not.toBeDisabled()
    })

    it('does not call toast.success when patchSettings rejects', async () => {
      mockPatchSettings.mockRejectedValue(new Error('Server error'))

      renderSettingsPage()

      const toggle = await screen.findByRole('switch', { name: /toggle flag-real_time_streaming/i })
      await userEvent.click(toggle)

      await waitFor(() => expect(mockToastError).toHaveBeenCalledTimes(1))

      expect(mockToastSuccess).not.toHaveBeenCalled()
    })
  })
})
