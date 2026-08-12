// Feature: react-ui-upgrade, Task 16.9 — DailyBriefPage movers error and breaking news
// Validates: Requirements 3.11, 3.18

import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import DailyBriefPage from '../DailyBriefPage'
import * as marketApi from '@/api/market'
import type { NewsArticle, MoversResponse, EnsemblePrediction } from '@/api/market'

// ---------------------------------------------------------------------------
// Mock the entire @/api/market module
// ---------------------------------------------------------------------------
vi.mock('@/api/market', async (importOriginal) => {
  const original = await importOriginal<typeof marketApi>()
  return {
    ...original,
    getMovers: vi.fn(),
    getNews: vi.fn(),
    getPredictions: vi.fn(),
    getTickerNews: vi.fn(),
    getPrediction: vi.fn(),
  }
})

const mockedGetMovers = vi.mocked(marketApi.getMovers)
const mockedGetNews = vi.mocked(marketApi.getNews)
const mockedGetPredictions = vi.mocked(marketApi.getPredictions)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildArticle(overrides: Partial<NewsArticle> = {}): NewsArticle {
  return {
    id: `art-${Math.random().toString(36).slice(2)}`,
    title: 'Test article title',
    source: 'Reuters',
    published_at: new Date().toISOString(),
    sentiment_score: 0.1,
    category: 'Earnings',
    is_breaking: false,
    summary: 'Article summary text.',
    tickers: [],
    url: 'https://example.com/article',
    ...overrides,
  }
}

const emptyMovers: MoversResponse = { gainers: [], losers: [] }
const emptyPredictions: EnsemblePrediction[] = []

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DailyBriefPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DailyBriefPage — movers fetch failure', () => {
  it('shows an inline error alert with "Failed to load market movers." when getMovers rejects', async () => {
    mockedGetMovers.mockRejectedValue(new Error('Network error'))
    mockedGetNews.mockResolvedValue([])
    mockedGetPredictions.mockResolvedValue(emptyPredictions)

    renderPage()

    await waitFor(() =>
      expect(screen.getByRole('alert')).toBeInTheDocument()
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Failed to load market movers.')
  })

  it('shows a Retry button when getMovers fails', async () => {
    mockedGetMovers.mockRejectedValue(new Error('Network error'))
    mockedGetNews.mockResolvedValue([])
    mockedGetPredictions.mockResolvedValue(emptyPredictions)

    renderPage()

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    )
  })
})

describe('DailyBriefPage — breaking news pill', () => {
  it('renders a "BREAKING" pill for articles with is_breaking === true', async () => {
    mockedGetMovers.mockResolvedValue(emptyMovers)
    mockedGetNews.mockResolvedValue([
      buildArticle({ is_breaking: true, title: 'Major market event' }),
    ])
    mockedGetPredictions.mockResolvedValue(emptyPredictions)

    renderPage()

    await waitFor(() =>
      expect(screen.getByLabelText('Breaking news')).toBeInTheDocument()
    )

    const pill = screen.getByLabelText('Breaking news')
    expect(pill).toHaveTextContent('BREAKING')
  })

  it('does not render a "BREAKING" pill for articles with is_breaking === false', async () => {
    mockedGetMovers.mockResolvedValue(emptyMovers)
    mockedGetNews.mockResolvedValue([
      buildArticle({ is_breaking: false, title: 'Regular article' }),
    ])
    mockedGetPredictions.mockResolvedValue(emptyPredictions)

    renderPage()

    await waitFor(() =>
      expect(screen.getByText('Regular article')).toBeInTheDocument()
    )

    expect(screen.queryByLabelText('Breaking news')).not.toBeInTheDocument()
  })
})
