import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import type { Quote } from '@/api/market'

// Feature: react-ui-upgrade, Property 7: Quote JSON round-trip preserves numeric precision

/**
 * Validates: Requirements 14.7
 */
describe('Quote JSON round-trip — Property 7: numeric precision preserved', () => {
  const finiteFloat = fc.float({ noNaN: true, noDefaultInfinity: true })
  const optionalFloat = fc.option(finiteFloat, { nil: null })

  const quoteArb = fc.record<Quote>({
    ticker: fc.string(),
    price: finiteFloat,
    change: finiteFloat,
    change_pct: finiteFloat,
    volume: finiteFloat,
    day_high: finiteFloat,
    day_low: finiteFloat,
    company_name: fc.string(),
    week_52_high: optionalFloat,
    week_52_low: optionalFloat,
    market_cap: optionalFloat,
    pe_ratio: optionalFloat,
  })

  const numericFields: Array<keyof Quote> = [
    'price',
    'change',
    'change_pct',
    'volume',
    'day_high',
    'day_low',
  ]

  const optionalNumericFields: Array<keyof Quote> = [
    'week_52_high',
    'week_52_low',
    'market_cap',
    'pe_ratio',
  ]

  it('required numeric fields survive JSON round-trip within 0.001 tolerance', () => {
    fc.assert(
      fc.property(quoteArb, (quote) => {
        const parsed: Quote = JSON.parse(JSON.stringify(quote))
        for (const field of numericFields) {
          const original = quote[field] as number
          const roundTripped = parsed[field] as number
          expect(Math.abs(roundTripped - original)).toBeLessThanOrEqual(0.001)
        }
      }),
      { numRuns: 100 }
    )
  })

  it('optional numeric fields survive JSON round-trip within 0.001 tolerance when not null', () => {
    fc.assert(
      fc.property(quoteArb, (quote) => {
        const parsed: Quote = JSON.parse(JSON.stringify(quote))
        for (const field of optionalNumericFields) {
          const original = quote[field] as number | null | undefined
          if (original != null) {
            const roundTripped = parsed[field] as number
            expect(Math.abs(roundTripped - original)).toBeLessThanOrEqual(0.001)
          }
        }
      }),
      { numRuns: 100 }
    )
  })

  it('null optional fields remain null after JSON round-trip', () => {
    fc.assert(
      fc.property(quoteArb, (quote) => {
        const parsed: Quote = JSON.parse(JSON.stringify(quote))
        for (const field of optionalNumericFields) {
          if (quote[field] === null) {
            expect(parsed[field]).toBeNull()
          }
        }
      }),
      { numRuns: 100 }
    )
  })
})
