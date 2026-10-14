import React, { useState } from 'react'
import type { ProposedAction } from '../api/types'
import { HighlightedText } from './HighlightedText'

export interface ApprovalCardProps {
  proposal: ProposedAction
  onApprove: (proposal: ProposedAction) => Promise<void>
  onReject: (proposal: ProposedAction, reason?: string) => Promise<void>
  onReload?: () => void
  isActing?: boolean
}

export function ApprovalCard({
  proposal,
  onApprove,
  onReject,
  onReload,
  isActing = false,
}: ApprovalCardProps): JSX.Element {
  const [showRejectInput, setShowRejectInput] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [showFacts, setShowFacts] = useState(false)
  const [conflictError, setConflictError] = useState<string | null>(null)
  const [localStatus, setLocalStatus] = useState<string>(proposal.status)

  const isPending = localStatus === 'pending'
  const isApproved = localStatus === 'approved' || localStatus === 'scheduled'
  const isRejected = localStatus === 'rejected'
  const isExpired = localStatus === 'expired'

  const handleApprove = async () => {
    setConflictError(null)
    try {
      await onApprove(proposal)
      setLocalStatus('approved')
    } catch (err: unknown) {
      const errorMsg = (err as Error)?.message || 'Failed to approve'
      if (errorMsg.includes('409') || errorMsg.toLowerCase().includes('conflict') || errorMsg.toLowerCase().includes('hash')) {
        setConflictError('Proposal conflict: The content hash changed or this proposal has expired. Please reload the latest proposal.')
      } else {
        setConflictError(errorMsg)
      }
    }
  }

  const handleConfirmReject = async () => {
    setConflictError(null)
    try {
      await onReject(proposal, rejectReason.trim() || undefined)
      setLocalStatus('rejected')
      setShowRejectInput(false)
    } catch (err: unknown) {
      const errorMsg = (err as Error)?.message || 'Failed to reject'
      if (errorMsg.includes('409') || errorMsg.toLowerCase().includes('conflict')) {
        setConflictError('Proposal conflict: The proposal is no longer active. Please reload.')
      } else {
        setConflictError(errorMsg)
      }
    }
  }

  return (
    <div
      data-testid="approval-card"
      style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '0.75rem',
        padding: '1.25rem',
        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
        marginBottom: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.875rem',
      }}
    >
      {/* Header: Ref, Kind badge & Policy Verdict */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            data-testid="action-ref"
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              fontFamily: 'monospace',
              color: '#374151',
              backgroundColor: '#f3f4f6',
              padding: '0.2rem 0.5rem',
              borderRadius: '0.25rem',
            }}
          >
            {proposal.ref}
          </span>
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              color: '#4f46e5',
              backgroundColor: '#eef2ff',
              padding: '0.2rem 0.5rem',
              borderRadius: '0.25rem',
            }}
          >
            {proposal.kind}
          </span>
        </div>

        {/* Status Pill */}
        <span
          data-testid="proposal-status"
          style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            padding: '0.2rem 0.6rem',
            borderRadius: '9999px',
            backgroundColor: isPending
              ? '#fef3c7'
              : isApproved
              ? '#d1fae5'
              : isRejected
              ? '#fee2e2'
              : '#f3f4f6',
            color: isPending
              ? '#92400e'
              : isApproved
              ? '#065f46'
              : isRejected
              ? '#991b1b'
              : '#6b7280',
          }}
        >
          {isPending
            ? 'REQUIRES FOUNDER APPROVAL'
            : isApproved
            ? 'APPROVED (SCHEDULED)'
            : isRejected
            ? 'REJECTED'
            : 'EXPIRED'}
        </span>
      </div>

      {/* Recipient & Deal Info */}
      <div style={{ fontSize: '0.875rem', color: '#4b5563' }}>
        <div>
          <strong style={{ color: '#111827' }}>To: </strong>
          <span>
            {proposal.contact_name} &lt;{proposal.contact_email}&gt;
          </span>
        </div>
        <div>
          <strong style={{ color: '#111827' }}>Deal: </strong>
          <span>{proposal.deal_title}</span>
        </div>
        <div>
          <strong style={{ color: '#111827' }}>Subject: </strong>
          <span style={{ fontWeight: 600, color: '#1f2937' }}>{proposal.subject}</span>
        </div>
      </div>

      {/* Risk Flags Banner */}
      {proposal.risk_flags && proposal.risk_flags.length > 0 && (
        <div
          data-testid="risk-flags-banner"
          style={{
            backgroundColor: '#fffbeb',
            borderLeft: '4px solid #f59e0b',
            padding: '0.75rem',
            borderRadius: '0.375rem',
            fontSize: '0.8125rem',
            color: '#92400e',
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>
            ⚠️ Guard Flag / Verification Required:
          </div>
          {proposal.risk_flags.map((flag, idx) => (
            <div key={idx} style={{ marginTop: idx > 0 ? '0.25rem' : '0' }}>
              • <strong>[{flag.code}]</strong> {flag.reason}
              {flag.customer_claim && (
                <div style={{ fontStyle: 'italic', marginTop: '0.125rem', color: '#b45309' }}>
                  Customer claim: &ldquo;{flag.customer_claim}&rdquo;
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Rendered Email Body with Grounded Highlights */}
      <div
        data-testid="rendered-body-container"
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: '0.5rem',
          padding: '0.875rem',
          backgroundColor: '#fafafa',
        }}
      >
        <div
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: '#6b7280',
            marginBottom: '0.5rem',
            textTransform: 'uppercase',
            letterSpacing: '0.025em',
          }}
        >
          Draft Message (Server Rendered)
        </div>
        <HighlightedText
          text={proposal.rendered_body}
          facts={proposal.facts_used || []}
          flags={proposal.risk_flags || []}
        />
      </div>

      {/* Verified Facts Evidence Drawer */}
      <div>
        <button
          type="button"
          onClick={() => setShowFacts(!showFacts)}
          style={{
            background: 'none',
            border: 'none',
            color: '#4f46e5',
            fontSize: '0.8125rem',
            fontWeight: 600,
            cursor: 'pointer',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
          }}
        >
          <span>{showFacts ? '▼ Hide' : '▶ Show'} Verified Facts ({proposal.facts_used?.length || 0})</span>
        </button>

        {showFacts && (
          <div
            data-testid="verified-facts-list"
            style={{
              marginTop: '0.5rem',
              padding: '0.625rem',
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '0.375rem',
              fontSize: '0.75rem',
            }}
          >
            {proposal.facts_used?.map((fact, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '0.25rem 0',
                  borderBottom: idx < proposal.facts_used.length - 1 ? '1px dashed #e2e8f0' : 'none',
                }}
              >
                <span>
                  <strong>{fact.label || fact.key}: </strong>
                  <span style={{ color: '#0f766e' }}>{fact.value}</span>
                </span>
                <span style={{ color: '#64748b', fontStyle: 'italic' }}>
                  src: {fact.source}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Cryptographic Content Hash Binding */}
      <div
        data-testid="hash-binding-info"
        style={{
          fontSize: '0.75rem',
          fontFamily: 'monospace',
          color: '#6b7280',
          backgroundColor: '#f9fafb',
          padding: '0.375rem 0.5rem',
          borderRadius: '0.25rem',
          border: '1px solid #e5e7eb',
          wordBreak: 'break-all',
        }}
      >
        <div style={{ fontWeight: 600, color: '#374151', marginBottom: '0.125rem' }}>
          Exact Content Hash (Hash-bound Approval):
        </div>
        <span>{proposal.rendered_hash}</span>
      </div>

      {/* Conflict or Stale Error Alert */}
      {conflictError && (
        <div
          data-testid="conflict-error"
          style={{
            backgroundColor: '#fee2e2',
            border: '1px solid #ef4444',
            borderRadius: '0.375rem',
            padding: '0.75rem',
            color: '#991b1b',
            fontSize: '0.8125rem',
          }}
        >
          <div>{conflictError}</div>
          {onReload && (
            <button
              type="button"
              onClick={() => {
                setConflictError(null)
                onReload()
              }}
              style={{
                marginTop: '0.5rem',
                backgroundColor: '#dc2626',
                color: '#ffffff',
                border: 'none',
                padding: '0.375rem 0.75rem',
                borderRadius: '0.25rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Reload Proposal
            </button>
          )}
        </div>
      )}

      {/* Reject Reason Form */}
      {showRejectInput && isPending && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label
            htmlFor={`reject-reason-${proposal.ref}`}
            style={{ fontSize: '0.75rem', fontWeight: 600, color: '#374151' }}
          >
            Rejection reason (optional):
          </label>
          <input
            id={`reject-reason-${proposal.ref}`}
            type="text"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="e.g. Price too low, wait until next week"
            style={{
              padding: '0.5rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.8125rem',
            }}
          />
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              type="button"
              disabled={isActing}
              onClick={handleConfirmReject}
              style={{
                flex: 1,
                minHeight: '44px',
                backgroundColor: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                fontWeight: 600,
                fontSize: '0.875rem',
                cursor: 'pointer',
              }}
            >
              Confirm Rejection
            </button>
            <button
              type="button"
              disabled={isActing}
              onClick={() => setShowRejectInput(false)}
              style={{
                minHeight: '44px',
                padding: '0 1rem',
                backgroundColor: '#f3f4f6',
                color: '#4b5563',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Action Buttons: Min 48px touch targets for mobile */}
      {isPending && !showRejectInput && (
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.25rem' }}>
          <button
            type="button"
            data-testid="approve-button"
            disabled={isActing}
            onClick={handleApprove}
            style={{
              flex: 2,
              minHeight: '48px',
              backgroundColor: isActing ? '#9ca3af' : '#059669',
              color: '#ffffff',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '0.9375rem',
              fontWeight: 700,
              cursor: isActing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)',
            }}
          >
            {isActing ? 'Processing...' : '✓ Approve (Bind to Hash)'}
          </button>

          <button
            type="button"
            data-testid="reject-button"
            disabled={isActing}
            onClick={() => setShowRejectInput(true)}
            style={{
              flex: 1,
              minHeight: '48px',
              backgroundColor: '#ffffff',
              color: '#dc2626',
              border: '1px solid #f87171',
              borderRadius: '0.5rem',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: isActing ? 'not-allowed' : 'pointer',
            }}
          >
            ✕ Reject
          </button>
        </div>
      )}

      {/* Terminal / In-Flight Status Feedback */}
      {isApproved && (
        <div
          data-testid="approval-success-notice"
          style={{
            backgroundColor: '#ecfdf5',
            border: '1px solid #a7f3d0',
            borderRadius: '0.375rem',
            padding: '0.75rem',
            fontSize: '0.8125rem',
            color: '#065f46',
          }}
        >
          ✓ Proposal approved. Action scheduled with undo window. Handing off to sealed worker executor.
        </div>
      )}

      {isRejected && (
        <div
          data-testid="rejection-notice"
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '0.375rem',
            padding: '0.75rem',
            fontSize: '0.8125rem',
            color: '#991b1b',
          }}
        >
          ✕ Proposal rejected. No external action will be taken.
        </div>
      )}

      {isExpired && (
        <div
          style={{
            backgroundColor: '#f3f4f6',
            borderRadius: '0.375rem',
            padding: '0.75rem',
            fontSize: '0.8125rem',
            color: '#6b7280',
          }}
        >
          ⏱ This proposal expired. Please generate a new proposal with fresh calendar & deal context.
        </div>
      )}
    </div>
  )
}
