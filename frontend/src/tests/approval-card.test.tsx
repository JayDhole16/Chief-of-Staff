import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { ApprovalCard } from '../components/ApprovalCard'
import type { ProposedAction } from '../api/types'

const MOCK_PROPOSAL: ProposedAction = {
  ref: 'PA-2026-10-15-001',
  kind: 'email',
  deal_id: 'deal_raju_01',
  deal_title: 'Acme Warehouse Automation',
  contact_name: 'Raju Patel',
  contact_email: 'raju@patel-warehousing.in',
  subject: 'Re: Automation Project Proposal & Scope',
  rendered_body: 'Dear Raju, we can offer 5% discount bringing setup to ₹4,56,000.',
  rendered_hash: '8f9b7c62d4e13589a12c8b74619d08e5c3e06182a93746c59b2184d8f1e6b392',
  facts_used: [
    { key: 'setup_cost', label: 'Setup Cost', value: '₹4,56,000', source: 'mandate_c2:rate_card' },
    { key: 'discount_pct', label: 'Discount', value: '5%', source: 'mandate_c2:max_discount' },
  ],
  risk_flags: [
    {
      code: 'G08',
      severity: 'warning',
      reason: 'Customer referenced verbal 20% discount on call. Exceeds mandate limit.',
      customer_claim: 'promised 20% on a call',
    },
  ],
  policy_verdict: 'ASK',
  policy_reasons: ['Unverified 20% discount claim in customer reply'],
  created_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 3600000).toISOString(),
  status: 'pending',
}

describe('ApprovalCard Component (T09.4)', () => {
  it('renders proposal details, recipient, subject, and hash-binding', () => {
    render(
      <ApprovalCard
        proposal={MOCK_PROPOSAL}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )

    expect(screen.getByTestId('action-ref')).toHaveTextContent('PA-2026-10-15-001')
    expect(screen.getByText(/Raju Patel/)).toBeInTheDocument()
    expect(screen.getByText(/Acme Warehouse Automation/)).toBeInTheDocument()
    expect(screen.getByText('Re: Automation Project Proposal & Scope')).toBeInTheDocument()
    expect(screen.getByTestId('hash-binding-info')).toHaveTextContent(
      '8f9b7c62d4e13589a12c8b74619d08e5c3e06182a93746c59b2184d8f1e6b392'
    )
  })

  it('highlights verified facts and displays risk flags', () => {
    render(
      <ApprovalCard
        proposal={MOCK_PROPOSAL}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )

    // Fact highlights
    const factHighlights = screen.getAllByTestId('fact-highlight')
    expect(factHighlights.length).toBeGreaterThanOrEqual(1)
    expect(factHighlights[0]).toHaveTextContent('5%')

    // Risk flag banner
    expect(screen.getByTestId('risk-flags-banner')).toHaveTextContent('G08')
    expect(screen.getByTestId('risk-flags-banner')).toHaveTextContent('promised 20% on a call')
  })

  it('toggles verified facts drawer', () => {
    render(
      <ApprovalCard
        proposal={MOCK_PROPOSAL}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )

    const factsButton = screen.getByText(/Show Verified Facts/)
    fireEvent.click(factsButton)

    expect(screen.getByTestId('verified-facts-list')).toBeInTheDocument()
    expect(screen.getAllByText(/mandate_c2:rate_card/).length).toBeGreaterThanOrEqual(1)
  })

  it('triggers onApprove with exact proposal when approve button clicked', async () => {
    const onApprove = vi.fn().mockResolvedValue(undefined)
    render(
      <ApprovalCard
        proposal={MOCK_PROPOSAL}
        onApprove={onApprove}
        onReject={vi.fn()}
      />
    )

    const approveBtn = screen.getByTestId('approve-button')
    fireEvent.click(approveBtn)

    await waitFor(() => {
      expect(onApprove).toHaveBeenCalledWith(MOCK_PROPOSAL)
      expect(screen.getByTestId('approval-success-notice')).toBeInTheDocument()
    })
  })

  it('handles 409 conflict error when hash mismatch occurs', async () => {
    const onApprove = vi.fn().mockRejectedValue(new Error('HTTP 409: Hash mismatch or expired'))
    const onReload = vi.fn()

    render(
      <ApprovalCard
        proposal={MOCK_PROPOSAL}
        onApprove={onApprove}
        onReject={vi.fn()}
        onReload={onReload}
      />
    )

    const approveBtn = screen.getByTestId('approve-button')
    fireEvent.click(approveBtn)

    await waitFor(() => {
      expect(screen.getByTestId('conflict-error')).toBeInTheDocument()
      expect(screen.getByText(/Proposal conflict/)).toBeInTheDocument()
    })

    const reloadBtn = screen.getByText('Reload Proposal')
    fireEvent.click(reloadBtn)
    expect(onReload).toHaveBeenCalled()
  })

  it('supports rejecting proposal with optional reason', async () => {
    const onReject = vi.fn().mockResolvedValue(undefined)

    render(
      <ApprovalCard
        proposal={MOCK_PROPOSAL}
        onApprove={vi.fn()}
        onReject={onReject}
      />
    )

    const rejectBtn = screen.getByTestId('reject-button')
    fireEvent.click(rejectBtn)

    const reasonInput = screen.getByPlaceholderText(/Price too low/)
    fireEvent.change(reasonInput, { target: { value: 'Price too aggressive' } })

    const confirmRejectBtn = screen.getByText('Confirm Rejection')
    fireEvent.click(confirmRejectBtn)

    await waitFor(() => {
      expect(onReject).toHaveBeenCalledWith(MOCK_PROPOSAL, 'Price too aggressive')
      expect(screen.getByTestId('rejection-notice')).toBeInTheDocument()
    })
  })
})
