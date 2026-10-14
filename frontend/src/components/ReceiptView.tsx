import React from 'react'
import type { ActionReceipt } from '../api/types'
import { formatDateTime } from '../utils/formatters'

export interface ReceiptViewProps {
  receipt: ActionReceipt
  onClose?: () => void
}

export function ReceiptView({ receipt, onClose }: ReceiptViewProps): JSX.Element {
  const isExecuted = receipt.status === 'executed'
  const isCancelled = receipt.status === 'cancelled'
  const isBlocked = receipt.status === 'blocked'

  return (
    <div
      data-testid="receipt-view"
      style={{
        backgroundColor: '#ffffff',
        border: '1px solid #d1d5db',
        borderRadius: '0.75rem',
        padding: '1.25rem',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
      }}
    >
      {/* Header with status badge and close */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase' }}>
            Terminal Action Receipt
          </div>
          <h3
            data-testid="receipt-id"
            style={{
              margin: '0.125rem 0 0 0',
              fontSize: '1rem',
              fontWeight: 700,
              fontFamily: 'monospace',
              color: '#111827',
            }}
          >
            {receipt.receipt_id}
          </h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            data-testid="receipt-status"
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              padding: '0.25rem 0.6rem',
              borderRadius: '9999px',
              textTransform: 'uppercase',
              backgroundColor: isExecuted
                ? '#d1fae5'
                : isCancelled
                ? '#fee2e2'
                : '#fef3c7',
              color: isExecuted
                ? '#065f46'
                : isCancelled
                ? '#991b1b'
                : '#92400e',
            }}
          >
            {receipt.status}
          </span>
          {onClose && (
            <button
              type="button"
              data-testid="receipt-close-button"
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '1.25rem',
                cursor: 'pointer',
                color: '#9ca3af',
                padding: '0.25rem',
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Authority Clause */}
      <div
        data-testid="receipt-authority"
        style={{
          backgroundColor: '#f8fafc',
          borderLeft: '4px solid #3b82f6',
          padding: '0.75rem',
          borderRadius: '0.25rem',
          fontSize: '0.8125rem',
        }}
      >
        <div style={{ fontWeight: 600, color: '#1e3a8a', marginBottom: '0.25rem' }}>
          Authority Clause:
        </div>
        <div style={{ color: '#1e293b' }}>{receipt.authority_clause}</div>
      </div>

      {/* External IDs & Target Info */}
      <div style={{ fontSize: '0.8125rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        <div>
          <strong style={{ color: '#374151' }}>Action Ref: </strong>
          <span style={{ fontFamily: 'monospace' }}>{receipt.action_ref}</span> ({receipt.action_kind})
        </div>
        {receipt.recipient_email && (
          <div>
            <strong style={{ color: '#374151' }}>Recipient: </strong>
            <span>{receipt.recipient_email}</span>
          </div>
        )}
        {receipt.meeting_time && (
          <div>
            <strong style={{ color: '#374151' }}>Meeting Time: </strong>
            <span>{receipt.meeting_time}</span>
          </div>
        )}
        {receipt.external_id && (
          <div data-testid="external-id">
            <strong style={{ color: '#374151' }}>Google External ID: </strong>
            <span style={{ fontFamily: 'monospace', color: '#0369a1' }}>{receipt.external_id}</span>
          </div>
        )}
      </div>

      {/* Checks Passed Badges */}
      {receipt.checks_passed && receipt.checks_passed.length > 0 && (
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#4b5563', marginBottom: '0.375rem' }}>
            Deterministic Guards Passed ({receipt.checks_passed.length}):
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
            {receipt.checks_passed.map((guardId) => (
              <span
                key={guardId}
                data-testid="guard-badge"
                style={{
                  fontSize: '0.7rem',
                  fontFamily: 'monospace',
                  fontWeight: 600,
                  backgroundColor: '#ecfdf5',
                  color: '#065f46',
                  border: '1px solid #a7f3d0',
                  padding: '0.15rem 0.4rem',
                  borderRadius: '0.25rem',
                }}
              >
                ✓ {guardId}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Facts Used Table */}
      {receipt.facts_used && receipt.facts_used.length > 0 && (
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#4b5563', marginBottom: '0.375rem' }}>
            Verified Grounding Facts ({receipt.facts_used.length}):
          </div>
          <div
            style={{
              backgroundColor: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: '0.375rem',
              padding: '0.5rem',
              fontSize: '0.75rem',
            }}
          >
            {receipt.facts_used.map((f, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '0.2rem 0',
                  borderBottom: idx < receipt.facts_used.length - 1 ? '1px dashed #e5e7eb' : 'none',
                }}
              >
                <span>
                  <strong>{f.label || f.key}: </strong>
                  <span style={{ color: '#047857' }}>{f.value}</span>
                </span>
                <span style={{ color: '#6b7280', fontStyle: 'italic' }}>src: {f.source}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rendered Hash */}
      <div
        style={{
          fontSize: '0.7rem',
          fontFamily: 'monospace',
          color: '#6b7280',
          backgroundColor: '#f3f4f6',
          padding: '0.375rem',
          borderRadius: '0.25rem',
          wordBreak: 'break-all',
        }}
      >
        <span style={{ fontWeight: 600 }}>Artifact Hash: </span>
        <span>{receipt.rendered_hash}</span>
      </div>

      {/* Timeline Audit Trail */}
      {receipt.timeline && receipt.timeline.length > 0 && (
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#4b5563', marginBottom: '0.375rem' }}>
            Timeline Audit Trail:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.75rem' }}>
            {receipt.timeline.map((step, idx) => (
              <div key={idx} style={{ display: 'flex', gap: '0.5rem', color: '#4b5563' }}>
                <span style={{ color: '#9ca3af', fontFamily: 'monospace' }}>
                  {formatDateTime(step.timestamp)}
                </span>
                <span>• {step.event}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

