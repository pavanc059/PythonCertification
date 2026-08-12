import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { TopHeader } from '../TopHeader'
import { useAlertStore } from '@/store/alertStore'

function renderTopHeader() {
  return render(
    <MemoryRouter>
      <TopHeader title="Test" />
    </MemoryRouter>
  )
}

describe('TopHeader badge logic', () => {
  beforeEach(() => {
    // Reset store to zero before each test
    useAlertStore.setState({ unreadCount: 0 })
  })

  it('renders no badge when unreadCount is 0', () => {
    useAlertStore.setState({ unreadCount: 0 })
    renderTopHeader()
    expect(screen.queryByTestId('alert-badge')).toBeNull()
  })

  it('renders badge with text "5" when unreadCount is 5', () => {
    useAlertStore.setState({ unreadCount: 5 })
    renderTopHeader()
    const badge = screen.getByTestId('alert-badge')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent('5')
  })

  it('renders badge with text "99+" when unreadCount is 100', () => {
    useAlertStore.setState({ unreadCount: 100 })
    renderTopHeader()
    const badge = screen.getByTestId('alert-badge')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent('99+')
  })

  it('renders badge with text "99+" when unreadCount is exactly 100', () => {
    useAlertStore.setState({ unreadCount: 100 })
    renderTopHeader()
    expect(screen.getByTestId('alert-badge')).toHaveTextContent('99+')
  })

  it('renders badge with exact count for unreadCount between 1 and 99', () => {
    useAlertStore.setState({ unreadCount: 99 })
    renderTopHeader()
    expect(screen.getByTestId('alert-badge')).toHaveTextContent('99')
  })
})
