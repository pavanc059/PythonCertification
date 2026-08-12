import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import type { NewsArticle } from '@/api/market'
import { filterBreakingNews } from '../newsUtils'

// Feature: react-ui-upgrade, Property 5: Breaking news filter produces a subset where all items are breaking

/**
 * Validates: Requirements 14.5
 */
describe('filterBreakingNews — Property 5: subset invariant', () => {
  const articleArb = fc.record<NewsArticle>({
    id: fc.uuid(),
    title: fc.string(),
    source: fc.string(),
    published_at: fc.string(),
    sentiment_score: fc.float({ min: -1, max: 1, noNaN: true }),
    category: fc.string(),
    is_breaking: fc.boolean(),
    summary: fc.string(),
    tickers: fc.array(fc.string()),
    url: fc.string(),
  })

  it('all returned articles have is_breaking === true', () => {
    fc.assert(
      fc.property(fc.array(articleArb), (articles) => {
        const result = filterBreakingNews(articles)
        expect(result.every((a) => a.is_breaking === true)).toBe(true)
      }),
      { numRuns: 100 }
    )
  })

  it('all returned article ids exist in the original array', () => {
    fc.assert(
      fc.property(fc.array(articleArb), (articles) => {
        const result = filterBreakingNews(articles)
        const originalIds = new Set(articles.map((a) => a.id))
        expect(result.every((a) => originalIds.has(a.id))).toBe(true)
      }),
      { numRuns: 100 }
    )
  })

  it('result is a subset: no extra articles beyond what is_breaking in the input', () => {
    fc.assert(
      fc.property(fc.array(articleArb), (articles) => {
        const result = filterBreakingNews(articles)
        const breakingCount = articles.filter((a) => a.is_breaking === true).length
        expect(result.length).toBe(breakingCount)
      }),
      { numRuns: 100 }
    )
  })
})
