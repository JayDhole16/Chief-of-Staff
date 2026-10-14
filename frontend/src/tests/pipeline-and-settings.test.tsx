import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { PipelineView } from '../components/PipelineView'
import { SettingsView } from '../components/SettingsView'
import type { Deal, LoginResponse, SystemSettings } from '../api/types'

const MOCK_DEALS: Deal[] = [
  {
    id: 'D-1',
    title: 'Acme Warehousing Automation',
    contact_name: 'Raju Patel',
    stage: 'negotiation',
    value_paise: 125000000, // ₹12,50,000
    created_at: new Date().toISOString(),
    days_quiet: 3,
    is_quiet: true,
  },
  {
    id: 'D-2',
    title: 'Apex Logistics Cloud Connector',
    contact_name: 'Sunil Mehta',
    stage: 'lead',
    value_paise: 250000000, // ₹25,00,000
    created_at: new Date().toISOString(),
    days_quiet: 0,
    is_quiet: false,
  },
]

const MOCK_SESSION: LoginResponse = {
  session_id: 'test_session_123',
  user: {
    id: 'user_123',
    email: 'meera@agency.in',
    name: 'Meera Nair',
  },
}

const MOCK_SETTINGS: SystemSettings = {
  founder: {
    name: 'Meera Nair',
    email: 'meera@agency.in',
    business_name: 'Nair Automation Labs',
    timezone: 'Asia/Kolkata',
  },
  google_account: {
    connected: true,
    email: 'meera@agency.in',
    token_status: 'valid',
    expires_at: new Date(Date.now() + 3600000).toISOString(),
    scopes: ['gmail.send', 'calendar.events'],
  },
  kill_switch: {
    active: false,
  },
}

describe('PipelineView (T09.5)', () => {
  it('renders deal titles, Indian currency formatting, and quiet chips', () => {
    render(<PipelineView deals={MOCK_DEALS} />)

    expect(screen.getByText('Acme Warehousing Automation')).toBeInTheDocument()
    expect(screen.getByText('Apex Logistics Cloud Connector')).toBeInTheDocument()

    // Formatted INR values
    expect(screen.getByText('₹12,50,000')).toBeInTheDocument()
    expect(screen.getByText('₹25,00,000')).toBeInTheDocument()

    // Total pipeline: ₹37,50,000
    expect(screen.getByTestId('total-pipeline-value')).toHaveTextContent('₹37,50,000')

    // Quiet chip for D-1
    expect(screen.getByTestId('quiet-chip')).toHaveTextContent('Quiet 3d')
  })

  it('filters quiet sweeps when quiet tab clicked', () => {
    render(<PipelineView deals={MOCK_DEALS} />)

    const quietFilterBtn = screen.getByTestId('filter-quiet')
    fireEvent.click(quietFilterBtn)

    expect(screen.getByText('Acme Warehousing Automation')).toBeInTheDocument()
    expect(screen.queryByText('Apex Logistics Cloud Connector')).not.toBeInTheDocument()
  })
})

describe('SettingsView (T09.5)', () => {
  it('renders founder profile and Google account status', () => {
    render(
      <SettingsView
        session={MOCK_SESSION}
        settings={MOCK_SETTINGS}
        onLogout={vi.fn()}
      />
    )

    expect(screen.getByText('Meera Nair')).toBeInTheDocument()
    expect(screen.getAllByText('meera@agency.in').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByTestId('google-conn-pill')).toHaveTextContent('Connected')
  })

  it('triggers 2-tap emergency kill switch confirmation', async () => {
    const onToggleKillSwitch = vi.fn().mockResolvedValue(undefined)

    render(
      <SettingsView
        session={MOCK_SESSION}
        settings={MOCK_SETTINGS}
        onLogout={vi.fn()}
        onToggleKillSwitch={onToggleKillSwitch}
      />
    )

    expect(screen.getByTestId('kill-switch-status')).toHaveTextContent('STANDBY')

    // Tap 1: Open modal
    const killBtn = screen.getByTestId('kill-switch-button')
    fireEvent.click(killBtn)

    expect(screen.getByTestId('kill-switch-modal')).toBeInTheDocument()
    expect(screen.getByText('Activate Kill Switch?')).toBeInTheDocument()

    // Tap 2: Confirm
    const confirmBtn = screen.getByTestId('confirm-kill-switch-button')
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(onToggleKillSwitch).toHaveBeenCalledWith(true)
      expect(screen.getByTestId('kill-switch-status')).toHaveTextContent('ACTIVE - AUTONOMY HALTED')
    })
  })
})
