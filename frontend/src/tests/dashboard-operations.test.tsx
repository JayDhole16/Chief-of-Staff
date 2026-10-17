import { describe, expect, it, vi } from 'vitest'
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

describe('Operations dashboard (T13) & Chatbot UX Bug Fixes', () => {
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

  it('Bug #1: clicking on chat icon collapses and expands the chat sidebar', () => {
    render(<DashboardPage session={session} onLogout={() => undefined} />)

    const chatSidebar = screen.getByTestId('chat-history-sidebar')
    const chatRailBtn = screen.getByTestId('rail-chat-button')

    // Initially open on chat view
    expect(chatSidebar).toHaveAttribute('aria-hidden', 'false')

    // Click chat icon while already on chat -> collapses sidebar
    fireEvent.click(chatRailBtn)
    expect(chatSidebar).toHaveAttribute('aria-hidden', 'true')

    // Click chat icon again -> expands sidebar
    fireEvent.click(chatRailBtn)
    expect(chatSidebar).toHaveAttribute('aria-hidden', 'false')
  })

  it('Bug #2: moving to another tab on sidebar hides the secondary chat sidebar', () => {
    render(<DashboardPage session={session} onLogout={() => undefined} />)

    const chatSidebar = screen.getByTestId('chat-history-sidebar')
    expect(chatSidebar).toHaveAttribute('aria-hidden', 'false')

    // Navigate to Deals tab
    fireEvent.click(screen.getByTestId('rail-deals-button'))
    expect(chatSidebar).toHaveAttribute('aria-hidden', 'true')

    // Navigate to Settings tab
    fireEvent.click(screen.getByTestId('rail-settings-button'))
    expect(chatSidebar).toHaveAttribute('aria-hidden', 'true')

    // Return to Chat tab -> restores chat sidebar
    fireEvent.click(screen.getByTestId('rail-chat-button'))
    expect(chatSidebar).toHaveAttribute('aria-hidden', 'false')
  })

  it('Bug #3: after sending texts, the chat autoscrolls to latest message', async () => {
    render(<DashboardPage session={session} onLogout={() => undefined} />)

    const container = screen.getByTestId('chat-messages-container')
    const scrollToSpy = vi.fn()
    container.scrollTo = scrollToSpy

    const input = screen.getByPlaceholderText(/Type a message/i)
    fireEvent.change(input, { target: { value: 'Check Q4 revenue target' } })
    fireEvent.submit(input.closest('form')!)

    expect(screen.getByText('Check Q4 revenue target')).toBeInTheDocument()
    expect(scrollToSpy).toHaveBeenCalled()
  })

  it('Bug #4: clicking on profile icon opens profile settings and does not immediately logout', () => {
    const onLogout = vi.fn()
    render(<DashboardPage session={session} onLogout={onLogout} />)

    const profileBtn = screen.getByTestId('profile-avatar-button')
    fireEvent.click(profileBtn)

    // Must NOT have logged out
    expect(onLogout).not.toHaveBeenCalled()

    // Profile settings view should be open
    expect(screen.getByTestId('profile-settings-view')).toBeInTheDocument()
    expect(screen.getByText(/Founder Profile & Account Settings/i)).toBeInTheDocument()

    // Clicking the explicit Sign out button inside Profile Settings triggers logout
    fireEvent.click(screen.getByTestId('profile-logout-button'))
    expect(onLogout).toHaveBeenCalledTimes(1)
  })
})
