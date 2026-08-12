// Feature: react-ui-upgrade, Property 1: SentimentBadge renders exactly one coloured badge for any valid score

import { render, cleanup } from '@testing-library/react'
import * as fc from 'fast-check'
import { afterEach, describe, expect, it } from 'vitest'
import { SentimentBadge } from '../SentimentBadge'

afterEach(() => {
  cleanup()
})

describe('SentimentBadge — Property 1', () => {
  /**
   * Validates: Requirements 14.1, 14.10
   *
   * For any valid sentiment score in [-1, 1], rendering SentimentBadge shall
   * produce exactly one badge element whose className is non-empty.
   */
  it('renders exactly one coloured badge for any score in [-1, 1]', () => {
    fc.assert(
      fc.property(
        fc.float({ min: -1, max: 1, noNaN: true }),
        (score) => {
          const { container } = render(<SentimentBadge score={score} />)
          const badges = container.querySelectorAll('[data-testid="sentiment-badge"]')
          expect(badges).toHaveLength(1)
          expect(badges[0].className).not.toBe('')
          cleanup()
        }
      ),
      { numRuns: 100 }
    )
  })
})
