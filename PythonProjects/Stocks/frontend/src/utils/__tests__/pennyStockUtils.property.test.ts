import * as fc from 'fast-check'
import { sortPennyStocks, selectTopPennyStocks } from '../pennyStockUtils'
import type { PennyStock } from '@/api/market'

// Arbitrary for a full PennyStock record with all required fields.
// fc.float constraints must be 32-bit floats, so values are wrapped with Math.fround.
const pennyStockArb: fc.Arbitrary<PennyStock> = fc.record({
  ticker: fc.string({ minLength: 1, maxLength: 5 }),
  price: fc.float({ min: Math.fround(0.01), max: Math.fround(4.99), noNaN: true }),
  price_change_pct: fc.float({ min: Math.fround(-1), max: Math.fround(1), noNaN: true }),
  volume: fc.nat({ max: 100_000_000 }),
  avg_volume: fc.nat({ max: 100_000_000 }),
  volume_ratio: fc.float({ min: Math.fround(0), max: Math.fround(100), noNaN: true }),
  momentum_score: fc.float({ min: Math.fround(0), max: Math.fround(100), noNaN: true }),
  risk_level: fc.constantFrom<PennyStock['risk_level']>('low', 'medium', 'high', 'extreme'),
  sector: fc.string({ minLength: 1, maxLength: 20 }),
  catalyst: fc.string({ minLength: 0, maxLength: 50 }),
  suspicion_score: fc.float({ min: Math.fround(0), max: Math.fround(1), noNaN: true }),
  recommendation: fc.string({ minLength: 0, maxLength: 50 }),
  insider_net: fc.float({ min: Math.fround(-1_000_000), max: Math.fround(1_000_000), noNaN: true }),
  insider_buys: fc.nat({ max: 1000 }),
  insider_sells: fc.nat({ max: 1000 }),
})

// Feature: react-ui-upgrade, Property 3: MomentumTable descending sort is a total order invariant
describe('sortPennyStocks — Property 3', () => {
  it('descending sort produces a non-increasing momentum_score sequence for any non-empty array', () => {
    // Validates: Requirements 14.3
    fc.assert(
      fc.property(
        fc.array(pennyStockArb, { minLength: 1, maxLength: 50 }),
        (rows) => {
          const sorted = sortPennyStocks(rows, 'momentum_score', 'desc')
          for (let i = 0; i < sorted.length - 1; i++) {
            expect(sorted[i].momentum_score).toBeGreaterThanOrEqual(sorted[i + 1].momentum_score)
          }
        }
      ),
      { numRuns: 100 }
    )
  })
})

// Feature: react-ui-upgrade, Property 4: selectTopPennyStocks length is min(rows.length, limit)
describe('selectTopPennyStocks — Property 4', () => {
  it('result length equals Math.min(rows.length, limit) for any rows array and non-negative limit', () => {
    // Validates: Requirements 14.4
    fc.assert(
      fc.property(
        fc.array(pennyStockArb),
        fc.nat(),
        (rows, limit) => {
          const result = selectTopPennyStocks(rows, limit)
          expect(result.length).toBe(Math.min(rows.length, limit))
        }
      ),
      { numRuns: 100 }
    )
  })
})
