// Feature: react-ui-upgrade, Task 16.4 — StockSearchBox error state unit tests
// Validates: Requirements 3.14, 3.15

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { StockSearchBox } from '../StockSearchBox'

// Mock the entire @/api/market module
vi.mock('@/api/market', () => ({
  getQuote: vi.fn(),
  getPrediction: vi.fn(),
  getTickerNews: vi.fn(),
}))

import * as marketApi from '@/api/market'

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  )
}

async function typeAndSubmit(ticker: string) {
  const input = screen.getByRole('textbox', { name: /stock ticker search/i })
  const button = screen.getByRole('button', { name: /search/i })
  await userEvent.type(input, ticker)
  await userEvent.click(button)
}

describe('StockSearchBox — error states', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    // Default: getPrediction and getTickerNews are never reached on error paths
    vi.mocked(marketApi.getPrediction).mockResolvedValue({
      ticker: 'AAPL',
      prediction: 0,
      confidence: 0,
      direction: 'neutral',
    })
    vi.mocked(marketApi.getTickerNews).mockResolvedValue([])
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows "Symbol not found." for a 404 response', async () => {
    // Simulate a 404 error (axios-style error object)
    const err = Object.assign(new Error('Not Found'), {
      response: { status: 404 },
    })
    vi.mocked(marketApi.getQuote).mockRejectedValue(err)

    renderWithProviders(<StockSearchBox />)

    await typeAndSubmit('AAPL')

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Symbol not found.')
  })

  it('shows "Unable to load data — please try again." for a network error', async () => {
    // Simulate a generic network error (no response.status)
    vi.mocked(marketApi.getQuote).mockRejectedValue(new Error('Network Error'))

    renderWithProviders(<StockSearchBox />)

    await typeAndSubmit('AAPL')

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Unable to load data — please try again.')
  })
})
