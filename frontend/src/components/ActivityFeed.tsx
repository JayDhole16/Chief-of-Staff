import React, { useState } from 'react'
import type { ActivityEvent, ActionReceipt } from '../api/types'
import { UndoCountdown } from './UndoCountdown'
import { ReceiptView } from './ReceiptView'
import { formatDateTime } from '../utils/formatters'
import { apiCall } from '../api/client'

export interface ActivityFeedProps {
  events: ActivityEvent[]
  isLoading?: boolean
  error?: Error | null
  onRefresh?: () => void
  onCancelAction?: (ref: string) => Promise<void>
}

export function ActivityFeed({
  events,
  isLoading = false,
  error = null,
  onRefresh,
  onCancelAction,
}: ActivityFeedProps): JSX.Element {
  const [selectedReceipt, setSelectedReceipt] = useState<ActionReceipt | null>(null)
  const [receiptLoading, setReceiptLoading] = useState(false)
  const [receiptError, setReceiptError] = useState<string | null>(null)

  const handleViewReceipt = async (receiptId: string) => {
    setReceiptLoading(true)
    setReceiptError(null)
    try {
      const receipt = await apiCall<ActionReceipt>(`/receipts/${receiptId}`)
      setSelectedReceipt(receipt)
    } catch (err) {
      setReceiptError((err as Error).message || 'Failed to load receipt')
    } finally {
      setReceiptLoading(false)
    }
  }

  const handleCancel = async (actionRef: string) => {
    if (onCancelAction) {
      await onCancelAction(actionRef)
    } else {
      await apiCall(`/actions/${actionRef}/cancel`, { method: 'POST' })
    }
    onRefresh?.()
  }

  return (
    <div
      data-testid="activity-feed"
      style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#111827' }}>
          Activity & Audit Log
        </h2>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isLoading}
            style={{
              padding: '0.25rem 0.6rem',
              fontSize: '0.75rem',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              cursor: 'pointer',
            }}
          >
            {isLoading ? '...' : '↻ Refresh'}
          </button>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div
          data-testid="activity-error"
          style={{
            padding: '0.75rem',
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            borderRadius: '0.375rem',
            fontSize: '0.8125rem',
          }}
        >
          Error loading activity: {error.message}
        </div>
      )}

      {/* Receipt View Modal / Drawer */}
      {selectedReceipt && (
        <ReceiptView
          receipt={selectedReceipt}
          onClose={() => setSelectedReceipt(null)}
        />
      )}

      {receiptError && (
        <div
          style={{
            padding: '0.5rem',
            backgroundColor: '#fee2e2',
            color: '#b91c1c',
            borderRadius: '0.25rem',
            fontSize: '0.75rem',
          }}
        >
          {receiptError}
        </div>
      )}

      {/* Empty State */}
      {events.length === 0 && !isLoading && (
        <div
          data-testid="activity-empty-state"
          style={{
            textAlign: 'center',
            padding: '2rem 1rem',
            backgroundColor: '#ffffff',
            borderRadius: '0.5rem',
            border: '1px dashed #d1d5db',
            color: '#6b7280',
            fontSize: '0.875rem',
          }}
        >
          No activity events recorded yet.
        </div>
      )}

      {/* Event Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {events.map((evt) => {
          const isUndoActive =
            Boolean(evt.can_undo && evt.action_ref) ||
            Boolean(evt.execute_after && new Date(evt.execute_after).getTime() > Date.now())

          return (
            <div
              key={evt.id}
              data-testid="activity-card"
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
                padding: '0.875rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    padding: '0.15rem 0.45rem',
                    borderRadius: '0.25rem',
                    backgroundColor:
                      evt.type === 'execution'
                        ? '#d1fae5'
                        : evt.type === 'approval'
                        ? '#eff6ff'
                        : evt.type === 'cancelled'
                        ? '#fee2e2'
                        : '#f3f4f6',
                    color:
                      evt.type === 'execution'
                        ? '#065f46'
                        : evt.type === 'approval'
                        ? '#1d4ed8'
                        : evt.type === 'cancelled'
                        ? '#991b1b'
                        : '#374151',
                  }}
                >
                  {evt.type}
                </span>
                <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>
                  {formatDateTime(evt.timestamp)}
                </span>
              </div>

              <div>
                <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#111827' }}>
                  {evt.title}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#4b5563', marginTop: '0.125rem' }}>
                  {evt.description}
                </div>
              </div>

              {/* Undo countdown banner if active */}
              {isUndoActive && evt.action_ref && (
                <UndoCountdown
                  actionRef={evt.action_ref}
                  executeAfter={evt.execute_after}
                  onCancel={handleCancel}
                  onComplete={onRefresh}
                />
              )}

              {/* Receipt link */}
              {evt.receipt_id && (
                <div style={{ marginTop: '0.25rem' }}>
                  <button
                    type="button"
                    data-testid="view-receipt-button"
                    onClick={() => handleViewReceipt(evt.receipt_id!)}
                    disabled={receiptLoading}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#2563eb',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: 0,
                      textDecoration: 'underline',
                    }}
                  >
                    View Execution Receipt ({evt.receipt_id})
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
