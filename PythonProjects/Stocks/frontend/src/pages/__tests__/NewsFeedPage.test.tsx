// Feature: react-ui-upgrade, Task 16.8 — NewsFeedPage filter and pagination behaviour
// Validates: Requirements 6.6, 6.9

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import NewsFeedPage from '../NewsFeedPage'
import * as marketApi from '@/api/market'
import type { NewsArticle } from '@/api/market'

// ---------------------------------------------------------------------------
// Mock the entire @/api/market module, then control getNews per-test
// ---------------------------------------------------------------------------
vi.mock('@/api/market', async (importOriginal) => {
  const original = await importOriginal<typeof marketApi>()
  return {
    ...original,
    getNews: vi.fn(),
  }
})

const mockedGetNews = vi.mocked(marketApi.getNews)

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

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        // Disable retries so failed/pending queries surface immediately in tests
        retry: false,
        // No stale time so queries always fire in tests
        staleTime: 0,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <NewsFeedPage />
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

describe('NewsFeedPage — filter change resets offset to 0', () => {
  it('calls getNews with offset=0 when the sentiment filter changes', async () => {
    // Arrange: return one article so the page is not in the empty state
    const articles = [buildArticle({ title: 'Initial article' })]
    mockedGetNews.mockResolvedValue(articles)

    renderPage()

    // Wait for the initial query (offset=0, sentimentFilter='all') to complete
    await waitFor(() => expect(screen.getByText('Initial article')).toBeInTheDocument())

    // Verify initial call params
    expect(mockedGetNews).toHaveBeenCalledWith(
      expect.objectContaining({ offset: 0 })
    )

    // Clear mock call history so we can inspect the next call cleanly
    mockedGetNews.mockClear()

    // Return fresh articles for the filtered query
    const filteredArticle = buildArticle({ title: 'Positive article' })
    mockedGetNews.mockResolvedValue([filteredArticle])

    // Act: click the "Positive" sentiment filter button
    const positiveButton = screen.getByRole('button', { name: /positive/i })
    fireEvent.click(positiveButton)

    // Assert: getNews must be called with offset=0 and sentiment='positive'
    await waitFor(() =>
      expect(mockedGetNews).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 0, sentiment: 'positive' })
      )
    )
  })

  it('calls getNews with offset=0 when the category filter changes', async () => {
    const articles = [buildArticle({ title: 'Initial article' })]
    mockedGetNews.mockResolvedValue(articles)

    renderPage()

    await waitFor(() => expect(screen.getByText('Initial article')).toBeInTheDocument())

    mockedGetNews.mockClear()
    mockedGetNews.mockResolvedValue([buildArticle({ title: 'Earnings article' })])

    // Act: click the "Earnings" category filter button.
    // Use aria-pressed to distinguish it from any "Earnings" text in article cards.
    const allCategoryButtons = screen.getAllByRole('button', { name: /earnings/i })
    const earningsButton = allCategoryButtons.find(
      (btn) => btn.hasAttribute('aria-pressed')
    )!
    fireEvent.click(earningsButton)

    await waitFor(() =>
      expect(mockedGetNews).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 0, category: 'Earnings' })
      )
    )
  })
})

describe('NewsFeedPage — empty state', () => {
  it('shows "No news matching your filters." when getNews returns an empty array', async () => {
    // Arrange: getNews resolves with no articles
    mockedGetNews.mockResolvedValue([])

    renderPage()

    // Wait for loading to complete and the empty state to appear
    await waitFor(() =>
      expect(
        screen.getByText('No news matching your filters.')
      ).toBeInTheDocument()
    )
  })

  it('does not show the empty state message while loading', () => {
    // Keep the promise pending to simulate loading
    mockedGetNews.mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(
      screen.queryByText('No news matching your filters.')
    ).not.toBeInTheDocument()
  })
})
