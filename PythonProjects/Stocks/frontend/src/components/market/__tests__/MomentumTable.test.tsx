import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import { MomentumTable } from '../MomentumTable'
import type { PennyStock } from '@/api/market'

// Three test rows with distinct momentum_score values
const makeStock = (overrides: Partial<PennyStock> & { ticker: string; momentum_score: number }): PennyStock => ({
  price: 1.0,
  price_change_pct: 0,
  volume: 100_000,
  avg_volume: 50_000,
  volume_ratio: 2.0,
  risk_level: 'low',
  sector: 'Technology',
  catalyst: 'earnings',
  suspicion_score: 0.1,
  recommendation: 'Buy',
  insider_net: 0,
  insider_buys: 1,
  insider_sells: 0,
  ...overrides,
})

const ROW_LOW: PennyStock = makeStock({ ticker: 'AAA', momentum_score: 30 })
const ROW_MID: PennyStock = makeStock({ ticker: 'BBB', momentum_score: 60 })
const ROW_HIGH: PennyStock = makeStock({ ticker: 'CCC', momentum_score: 90 })

const TEST_ROWS = [ROW_MID, ROW_LOW, ROW_HIGH] // deliberately unordered

function getHeaders() {
  return screen.getAllByRole('columnheader')
}

function getScoreHeader() {
  return screen.getByRole('columnheader', { name: /score/i })
}

function getTickerHeader() {
  return screen.getByRole('columnheader', { name: /ticker/i })
}

function getRenderedTickers(): string[] {
  const rows = screen.getAllByRole('row').slice(1) // skip header row
  return rows.map((row) => within(row).getByText(/^[A-Z]{3}$/).textContent ?? '')
}

describe('MomentumTable – sort interactions', () => {
  it('initially renders sorted by momentum_score descending', () => {
    render(<MomentumTable rows={TEST_ROWS} isLoading={false} />)

    // Score column header must have aria-sort="descending"
    expect(getScoreHeader()).toHaveAttribute('aria-sort', 'descending')

    // Rows ordered high → low: CCC (90), BBB (60), AAA (30)
    const tickers = getRenderedTickers()
    expect(tickers).toEqual(['CCC', 'BBB', 'AAA'])
  })

  it('clicking Score header once toggles sort to ascending', async () => {
    const user = userEvent.setup()
    render(<MomentumTable rows={TEST_ROWS} isLoading={false} />)

    await user.click(getScoreHeader())

    expect(getScoreHeader()).toHaveAttribute('aria-sort', 'ascending')

    // Rows ordered low → high: AAA (30), BBB (60), CCC (90)
    const tickers = getRenderedTickers()
    expect(tickers).toEqual(['AAA', 'BBB', 'CCC'])
  })

  it('clicking Score header twice returns to descending', async () => {
    const user = userEvent.setup()
    render(<MomentumTable rows={TEST_ROWS} isLoading={false} />)

    await user.click(getScoreHeader()) // → ascending
    await user.click(getScoreHeader()) // → descending again

    expect(getScoreHeader()).toHaveAttribute('aria-sort', 'descending')

    const tickers = getRenderedTickers()
    expect(tickers).toEqual(['CCC', 'BBB', 'AAA'])
  })

  it('clicking a different column resets sort to descending on that column', async () => {
    const user = userEvent.setup()
    render(<MomentumTable rows={TEST_ROWS} isLoading={false} />)

    // Click Ticker header (different column)
    await user.click(getTickerHeader())

    // Ticker column should now be descending, Score should be none
    expect(getTickerHeader()).toHaveAttribute('aria-sort', 'descending')
    expect(getScoreHeader()).toHaveAttribute('aria-sort', 'none')
  })

  it('all non-active column headers have aria-sort="none" on initial render', () => {
    render(<MomentumTable rows={TEST_ROWS} isLoading={false} />)

    const headers = getHeaders()
    headers.forEach((th) => {
      const ariaSort = th.getAttribute('aria-sort')
      if (th === getScoreHeader()) {
        expect(ariaSort).toBe('descending')
      } else {
        expect(ariaSort).toBe('none')
      }
    })
  })
})
