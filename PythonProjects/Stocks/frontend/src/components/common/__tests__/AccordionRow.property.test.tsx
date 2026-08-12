// Feature: react-ui-upgrade, Property 6: AccordionRow even-toggle idempotence

import { render, cleanup, fireEvent, within } from '@testing-library/react'
import * as fc from 'fast-check'
import { afterEach, describe, expect, it } from 'vitest'
import { AccordionRow } from '../AccordionRow'

afterEach(() => {
  cleanup()
})

describe('AccordionRow — Property 6: even-toggle idempotence', () => {
  /**
   * **Validates: Requirements 14.6**
   *
   * Property 6: AccordionRow even-toggle idempotence.
   *
   * For any positive integer n in [1, 10], firing exactly 2n click events on the
   * toggle button of a collapsed AccordionRow must leave the component in the
   * same collapsed state as the initial render — i.e. aria-expanded is "false".
   *
   * Note: framer-motion's AnimatePresence may keep the exit element briefly in
   * the DOM in jsdom (without animations running). We therefore assert on the
   * authoritative collapsed state indicator: aria-expanded="false".
   */
  it('component returns to collapsed state (aria-expanded=false) after 2n toggles for any n in [1, 10]', { timeout: 30000 }, () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }),
        (n) => {
          // Render into an isolated container so cleanup() within the loop
          // doesn't leave stale DOM nodes visible to getByRole.
          const { container } = render(
            <AccordionRow header="Test Header">
              <p>Content</p>
            </AccordionRow>
          )

          const utils = within(container)
          const button = utils.getByRole('button')

          // Verify we start collapsed
          expect(button.getAttribute('aria-expanded')).toBe('false')

          // Fire 2n clicks — an even count always returns to the initial state
          const totalClicks = 2 * n
          for (let i = 0; i < totalClicks; i++) {
            fireEvent.click(button)
          }

          // After an even number of toggles the button must report collapsed
          expect(button.getAttribute('aria-expanded')).toBe('false')

          cleanup()
        }
      ),
      { numRuns: 100 }
    )
  })
})
