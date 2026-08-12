// Feature: react-ui-upgrade, Task 16.1 — SentimentBadge boundary unit tests
// Validates: Requirements 1.5, 14.10

import { render, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { SentimentBadge } from '../SentimentBadge'

afterEach(() => {
  cleanup()
})

describe('SentimentBadge — boundary examples', () => {
  // score = 0 → yellow (neutral)
  it('renders yellow badge for score = 0', () => {
    const { getByTestId } = render(<SentimentBadge score={0} />)
    const badge = getByTestId('sentiment-badge')
    expect(badge.className).toMatch(/text-yellow-400/)
    expect(badge.className).not.toMatch(/text-green-400/)
    expect(badge.className).not.toMatch(/text-red-400/)
  })

  // score = 0.15 → yellow (neutral, at upper boundary, not strictly > 0.15)
  it('renders yellow badge for score = 0.15', () => {
    const { getByTestId } = render(<SentimentBadge score={0.15} />)
    const badge = getByTestId('sentiment-badge')
    expect(badge.className).toMatch(/text-yellow-400/)
    expect(badge.className).not.toMatch(/text-green-400/)
    expect(badge.className).not.toMatch(/text-red-400/)
  })

  // score = 0.16 → green (positive, strictly > 0.15)
  it('renders green badge for score = 0.16', () => {
    const { getByTestId } = render(<SentimentBadge score={0.16} />)
    const badge = getByTestId('sentiment-badge')
    expect(badge.className).toMatch(/text-green-400/)
    expect(badge.className).not.toMatch(/text-yellow-400/)
    expect(badge.className).not.toMatch(/text-red-400/)
  })

  // score = -0.15 → yellow (neutral, at lower boundary, not strictly < -0.15)
  it('renders yellow badge for score = -0.15', () => {
    const { getByTestId } = render(<SentimentBadge score={-0.15} />)
    const badge = getByTestId('sentiment-badge')
    expect(badge.className).toMatch(/text-yellow-400/)
    expect(badge.className).not.toMatch(/text-green-400/)
    expect(badge.className).not.toMatch(/text-red-400/)
  })

  // score = -0.16 → red (negative, strictly < -0.15)
  it('renders red badge for score = -0.16', () => {
    const { getByTestId } = render(<SentimentBadge score={-0.16} />)
    const badge = getByTestId('sentiment-badge')
    expect(badge.className).toMatch(/text-red-400/)
    expect(badge.className).not.toMatch(/text-green-400/)
    expect(badge.className).not.toMatch(/text-yellow-400/)
  })
})
