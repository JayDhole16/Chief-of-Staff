import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import React from 'react'
import { DashboardPage } from '../pages/DashboardPage'
import type { LoginResponse } from '../api/types'

const session: LoginResponse = {
  session_id: 'test_session_123',
  user: {
    id: 'user_123',
    email: 'meera@agency.in',
    name: 'Meera Nair',
  },
}

describe('Operations dashboard (T13)', () => {
  it('shows provisional status and only linked brief activity', async () => {
    sessionStorage.setItem('session_id', session.session_id)
    render(<DashboardPage session={session} onLogout={() => undefined} />)

    fireEvent.click(screen.getByRole('button', { name: /Ops/ }))

    expect(await screen.findByTestId('operations-status')).toBeInTheDocument()
    expect(screen.getByText(/not evidence of live G4/i)).toBeInTheDocument()
    expect(screen.getByText(/worker: degraded/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByTestId('daily-brief')).toHaveTextContent('View approval')
    })
    expect(screen.getByRole('link', { name: /View approval: PA-2026-10-15-001/ })).toHaveAttribute(
      'href',
      expect.stringContaining('/api/approvals/pending')
    )
  })
})
