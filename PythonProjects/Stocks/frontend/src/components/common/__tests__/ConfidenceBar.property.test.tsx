// Feature: react-ui-upgrade, Property 2: ConfidenceBar width and aria-valuenow are bounded and consistent
import { describe, it } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import * as fc from 'fast-check'
import { ConfidenceBar } from '../ConfidenceBar'

/**
 * **Validates: Requirements 14.2, 14.8, 14.9**
 *
 * Property 2: ConfidenceBar width and aria-valuenow are bounded and consistent.
 *
 * For any confidence value in [0, 100], rendering ConfidenceBar shall produce a
 * progressbar whose aria-valuenow equals that integer value, aria-valuemin equals 0,
 * and aria-valuemax equals 100. The fill element's inline width (when set) is
 * bounded within [0, 100].
 */
describe('ConfidenceBar — Property 2: bounded and consistent aria attributes', () => {
  it('renders bar with consistent aria-valuenow and bounded width for any value 0–100', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 100 }),
        (value) => {
          const { getByRole } = render(<ConfidenceBar value={value} color="#6366f1" />)

          const bar = getByRole('progressbar')

          // aria-valuenow must equal the input value exactly
          expect(Number(bar.getAttribute('aria-valuenow'))).toBe(value)
          // aria-valuemin must be 0
          expect(Number(bar.getAttribute('aria-valuemin'))).toBe(0)
          // aria-valuemax must be 100
          expect(Number(bar.getAttribute('aria-valuemax'))).toBe(100)

          // The fill div is rendered with data-testid="confidence-fill"
          const inner = bar.querySelector('[data-testid="confidence-fill"]') as HTMLElement
          expect(inner).not.toBeNull()

          // Framer Motion animates width asynchronously in jsdom, so inline style.width
          // may not be set at render time. When it is set (e.g. initial state "0%" is
          // applied), we assert it is within [0, 100].
          const rawWidth = inner.style.width
          if (rawWidth !== '') {
            const width = parseFloat(rawWidth)
            expect(width).toBeGreaterThanOrEqual(0)
            expect(width).toBeLessThanOrEqual(100)
          }

          cleanup()
        }
      ),
      { numRuns: 100 }
    )
  })
})
