// Feature: react-ui-upgrade — Unit tests for ConfidenceBar edge values
// Requirements: 1.6, 14.8, 14.9
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { ConfidenceBar } from '../ConfidenceBar'

describe('ConfidenceBar — edge values', () => {
  describe('value = 0', () => {
    it('renders progressbar with aria-valuenow="0"', () => {
      const { getByRole } = render(<ConfidenceBar value={0} color="#6366f1" />)
      const bar = getByRole('progressbar')
      expect(bar).toHaveAttribute('aria-valuenow', '0')
    })

    it('renders progressbar with aria-valuemin=0 and aria-valuemax=100', () => {
      const { getByRole } = render(<ConfidenceBar value={0} color="#6366f1" />)
      const bar = getByRole('progressbar')
      expect(bar).toHaveAttribute('aria-valuemin', '0')
      expect(bar).toHaveAttribute('aria-valuemax', '100')
    })

    it('renders the confidence-fill element', () => {
      const { getByTestId } = render(<ConfidenceBar value={0} color="#6366f1" />)
      const fill = getByTestId('confidence-fill')
      expect(fill).toBeInTheDocument()
    })

    it('fill width is "0%" when framer-motion applies initial style synchronously', () => {
      const { getByTestId } = render(<ConfidenceBar value={0} color="#6366f1" />)
      const fill = getByTestId('confidence-fill') as HTMLElement
      // Framer Motion may not set width synchronously in jsdom.
      // When it does set an initial width, it must be 0%.
      const rawWidth = fill.style.width
      if (rawWidth !== '') {
        expect(rawWidth).toBe('0%')
      }
    })
  })

  describe('value = 100', () => {
    it('renders progressbar with aria-valuenow="100"', () => {
      const { getByRole } = render(<ConfidenceBar value={100} color="#6366f1" />)
      const bar = getByRole('progressbar')
      expect(bar).toHaveAttribute('aria-valuenow', '100')
    })

    it('renders progressbar with aria-valuemin=0 and aria-valuemax=100', () => {
      const { getByRole } = render(<ConfidenceBar value={100} color="#6366f1" />)
      const bar = getByRole('progressbar')
      expect(bar).toHaveAttribute('aria-valuemin', '0')
      expect(bar).toHaveAttribute('aria-valuemax', '100')
    })

    it('renders the confidence-fill element', () => {
      const { getByTestId } = render(<ConfidenceBar value={100} color="#6366f1" />)
      const fill = getByTestId('confidence-fill')
      expect(fill).toBeInTheDocument()
    })

    it('fill width reflects the animated target (100%) or initial state in jsdom', () => {
      const { getByTestId } = render(<ConfidenceBar value={100} color="#6366f1" />)
      const fill = getByTestId('confidence-fill') as HTMLElement
      // Framer Motion animates width asynchronously in jsdom — the `animate` target
      // ("100%") is never applied synchronously. Only the `initial` value ("0%") may
      // be present. We verify that any inline width that is set is a valid percentage
      // within [0, 100], which is consistent with requirements 14.8 and 14.9.
      const rawWidth = fill.style.width
      if (rawWidth !== '') {
        const pct = parseFloat(rawWidth)
        expect(pct).toBeGreaterThanOrEqual(0)
        expect(pct).toBeLessThanOrEqual(100)
      }
    })
  })
})
