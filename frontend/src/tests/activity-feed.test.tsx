import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { ActivityFeed } from '../components/ActivityFeed'
import { UndoCountdown } from '../components/UndoCountdown'
import { ReceiptView } from '../components/ReceiptView'
import type { ActivityEvent, ActionReceipt } from '../api/types'

const MOCK_EVENTS: ActivityEvent[] = [
  {
    id: 'evt_1',
    timestamp: new Date().toISOString(),
    type: 'proposed',
    title: 'Proposed follow-up to Raju Patel',
    description: 'Counter-offer ₹4,56,000 drafted. Pending founder approval.',
    user_id: 'agent_cos',
    action_ref: 'PA-2026-10-15-001',
  },
  {
    id: 'evt_2',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    type: 'execution',
    title: 'D-1 Follow-up Sent',
    description: 'Follow-up email autonomously sent to Acme Warehousing.',
    user_id: 'worker_executor',
    action_ref: 'act_d1_01',
    receipt_id: 'rcpt_20261015_001',
  },
]

const MOCK_RECEIPT: ActionReceipt = {
  receipt_id: 'rcpt_20261015_001',
  action_ref: 'act_d1_01',
  action_kind: 'email',
  status: 'executed',
  authority_clause: 'Mandate M-2026-10-15 Clause C2: Follow-up quiet deals with <=5% discount',
  recipient_email: 'raju@patel-warehousing.in',
  external_id: 'gmail_msg_18b93f8e71c29a04',
  rendered_hash: '9a7e6b54c3d2e1f089123456789abcdef0123456789abcdef0123456789abcde',
  checks_passed: ['G01', 'G04', 'G05', 'G07', 'G09', 'G10', 'G11'],
  facts_used: [
    { key: 'deal_value', label: 'Deal Value', value: '₹12,50,000', source: 'crm:deal_d1' },
    { key: 'contact_name', label: 'Contact', value: 'Raju Patel', source: 'crm:contact_raju' },
  ],
  executed_at: new Date().toISOString(),
  timeline: [
    { timestamp: new Date().toISOString(), event: 'Autonomous send dispatched by Google worker' },
  ],
}

describe('ActivityFeed & Receipts (T09.5)', () => {
  it('renders list of activity events', () => {
    render(<ActivityFeed events={MOCK_EVENTS} />)

    expect(screen.getByText('Proposed follow-up to Raju Patel')).toBeInTheDocument()
    expect(screen.getByText('D-1 Follow-up Sent')).toBeInTheDocument()
    expect(screen.getByText('View Execution Receipt (rcpt_20261015_001)')).toBeInTheDocument()
  })

  it('renders empty state when no events exist', () => {
    render(<ActivityFeed events={[]} />)
    expect(screen.getByTestId('activity-empty-state')).toHaveTextContent(
      'No activity events recorded yet.'
    )
  })

  it('renders error message when error is provided', () => {
    render(<ActivityFeed events={[]} error={new Error('Network failure')} />)
    expect(screen.getByTestId('activity-error')).toHaveTextContent('Network failure')
  })
})

describe('UndoCountdown (T09.5)', () => {
  it('renders countdown seconds and allows action cancellation', async () => {
    const onCancel = vi.fn().mockResolvedValue(undefined)
    const futureTime = new Date(Date.now() + 15000).toISOString()

    render(
      <UndoCountdown
        actionRef="act_test_001"
        executeAfter={futureTime}
        onCancel={onCancel}
      />
    )

    expect(screen.getByTestId('undo-countdown-banner')).toBeInTheDocument()
    expect(screen.getByText(/Undo window active/)).toBeInTheDocument()

    const cancelBtn = screen.getByTestId('undo-cancel-button')
    fireEvent.click(cancelBtn)

    await waitFor(() => {
      expect(onCancel).toHaveBeenCalledWith('act_test_001')
      expect(screen.getByTestId('undo-cancelled-state')).toBeInTheDocument()
    })
  })

  it('handles 409 conflict when window has elapsed', async () => {
    const onCancel = vi.fn().mockRejectedValue(new Error('HTTP 409: Worker already dispatched'))

    render(
      <UndoCountdown
        actionRef="act_test_002"
        initialSeconds={10}
        onCancel={onCancel}
      />
    )

    const cancelBtn = screen.getByTestId('undo-cancel-button')
    fireEvent.click(cancelBtn)

    await waitFor(() => {
      expect(screen.getByTestId('undo-error')).toHaveTextContent(
        'Action already dispatched to worker. Undo window closed.'
      )
    })
  })
})

describe('ReceiptView (T09.5)', () => {
  it('renders receipt ID, authority clause, external Google ID, and checks passed', () => {
    const onClose = vi.fn()
    render(<ReceiptView receipt={MOCK_RECEIPT} onClose={onClose} />)

    expect(screen.getByTestId('receipt-id')).toHaveTextContent('rcpt_20261015_001')
    expect(screen.getByTestId('receipt-status')).toHaveTextContent('executed')
    expect(screen.getByTestId('receipt-authority')).toHaveTextContent('Mandate M-2026-10-15 Clause C2')
    expect(screen.getByTestId('external-id')).toHaveTextContent('gmail_msg_18b93f8e71c29a04')

    // Guard badges
    const guardBadges = screen.getAllByTestId('guard-badge')
    expect(guardBadges.length).toBe(7)
    expect(guardBadges[0]).toHaveTextContent('G01')

    // Close button
    fireEvent.click(screen.getByTestId('receipt-close-button'))
    expect(onClose).toHaveBeenCalled()
  })
})

