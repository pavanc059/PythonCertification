// Feature: react-ui-upgrade, Task 16.5 — AlertsPage dismiss interaction unit tests
// Validates: Requirements 8.5

import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { Alert } from '@/api/alerts'

// ---- Mocks ----------------------------------------------------------------

vi.mock('@/api/alerts', () => ({
  getAlerts: vi.fn(),
  dismissAlert: vi.fn(),
  markAllAlertsRead: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

// Import after mocking so the mocked versions are used
import { getAlerts, dismissAlert } from '@/api/alerts'
import { toast } from 'sonner'
import AlertsPage from '../AlertsPage'

// ---- Test data -------------------------------------------------------------

const ALERTS: Alert[] = [
  {
    id: 'alert-1',
    ticker: 'AAPL',
    alert_type: 'price_target',
    message: 'AAPL has reached your price target of $200.',
    severity: 'info',
    timestamp: new Date(Date.now() - 5 * 60_000).toISOString(),
    is_read: false,
  },
  {
    id: 'alert-2',
    ticker: 'TSLA',
    alert_type: 'volume_spike',
    message: 'TSLA volume spike detected.',
    severity: 'warning',
    timestamp: new Date(Date.now() - 30 * 60_000).toISOString(),
    is_read: true,
  },
]

// ---- Helpers ---------------------------------------------------------------

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function renderAlertsPage(queryClient: QueryClient) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AlertsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ---- Tests -----------------------------------------------------------------

describe('AlertsPage — dismiss interactions', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = makeQueryClient()
    vi.mocked(getAlerts).mockResolvedValue([...ALERTS])
    vi.mocked(dismissAlert).mockResolvedValue(undefined)
    vi.mocked(toast.error).mockClear()
    vi.mocked(toast.success).mockClear()
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  // --- Success case ---

  describe('dismiss success', () => {
    it('removes the dismissed alert card from the list', async () => {
      vi.mocked(dismissAlert).mockResolvedValue(undefined)
      renderAlertsPage(queryClient)

      // Wait for both alert cards to appear
      await waitFor(() => {
        expect(screen.getByLabelText('Dismiss alert for AAPL')).toBeInTheDocument()
        expect(screen.getByLabelText('Dismiss alert for TSLA')).toBeInTheDocument()
      })

      // Click dismiss on the first alert
      const dismissButton = screen.getByLabelText('Dismiss alert for AAPL')
      await userEvent.click(dismissButton)

      // The AAPL card should be optimistically hidden
      await waitFor(() => {
        expect(screen.queryByLabelText('Dismiss alert for AAPL')).not.toBeInTheDocument()
      })

      // TSLA card should still be present
      expect(screen.getByLabelText('Dismiss alert for TSLA')).toBeInTheDocument()
    })

    it('calls dismissAlert with the correct alert id', async () => {
      vi.mocked(dismissAlert).mockResolvedValue(undefined)
      renderAlertsPage(queryClient)

      await waitFor(() => {
        expect(screen.getByLabelText('Dismiss alert for AAPL')).toBeInTheDocument()
      })

      await userEvent.click(screen.getByLabelText('Dismiss alert for AAPL'))

      await waitFor(() => {
        expect(vi.mocked(dismissAlert).mock.calls[0][0]).toBe('alert-1')
      })
    })

    it('does not show an error toast on successful dismiss', async () => {
      vi.mocked(dismissAlert).mockResolvedValue(undefined)
      renderAlertsPage(queryClient)

      await waitFor(() => {
        expect(screen.getByLabelText('Dismiss alert for AAPL')).toBeInTheDocument()
      })

      await userEvent.click(screen.getByLabelText('Dismiss alert for AAPL'))

      // Give mutations time to settle
      await waitFor(() => {
        expect(screen.queryByLabelText('Dismiss alert for AAPL')).not.toBeInTheDocument()
      })

      expect(toast.error).not.toHaveBeenCalled()
    })
  })

  // --- Failure case ---

  describe('dismiss failure', () => {
    it('keeps the alert card in the list when dismiss fails', async () => {
      vi.mocked(dismissAlert).mockRejectedValue(new Error('Network error'))
      renderAlertsPage(queryClient)

      await waitFor(() => {
        expect(screen.getByLabelText('Dismiss alert for AAPL')).toBeInTheDocument()
      })

      await userEvent.click(screen.getByLabelText('Dismiss alert for AAPL'))

      // After the error, card should reappear
      await waitFor(() => {
        expect(screen.getByLabelText('Dismiss alert for AAPL')).toBeInTheDocument()
      })
    })

    it('shows an error toast when dismiss fails', async () => {
      vi.mocked(dismissAlert).mockRejectedValue(new Error('Network error'))
      renderAlertsPage(queryClient)

      await waitFor(() => {
        expect(screen.getByLabelText('Dismiss alert for AAPL')).toBeInTheDocument()
      })

      await userEvent.click(screen.getByLabelText('Dismiss alert for AAPL'))

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Failed to dismiss alert. Please try again.',
        )
      })
    })

    it('retains the other alert card when one dismiss fails', async () => {
      vi.mocked(dismissAlert).mockRejectedValue(new Error('Network error'))
      renderAlertsPage(queryClient)

      await waitFor(() => {
        expect(screen.getByLabelText('Dismiss alert for AAPL')).toBeInTheDocument()
        expect(screen.getByLabelText('Dismiss alert for TSLA')).toBeInTheDocument()
      })

      await userEvent.click(screen.getByLabelText('Dismiss alert for AAPL'))

      // Both cards should still be visible after failure
      await waitFor(() => {
        expect(screen.getByLabelText('Dismiss alert for AAPL')).toBeInTheDocument()
        expect(screen.getByLabelText('Dismiss alert for TSLA')).toBeInTheDocument()
      })
    })
  })
})
