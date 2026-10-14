import React, { useState, useEffect } from 'react'

export interface UndoCountdownProps {
  actionRef: string
  executeAfter?: string // ISO timestamp
  initialSeconds?: number // default 15s for mandate, 5s for approved
  onCancel: (actionRef: string) => Promise<void>
  onComplete?: () => void
}

export function UndoCountdown({
  actionRef,
  executeAfter,
  initialSeconds = 15,
  onCancel,
  onComplete,
}: UndoCountdownProps): JSX.Element {
  const calculateSecondsRemaining = (): number => {
    if (executeAfter) {
      const remainingMs = new Date(executeAfter).getTime() - Date.now()
      return Math.max(0, Math.ceil(remainingMs / 1000))
    }
    return initialSeconds
  }

  const [secondsLeft, setSecondsLeft] = useState<number>(calculateSecondsRemaining())
  const [isCancelling, setIsCancelling] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)
  const [isCancelled, setIsCancelled] = useState(false)

  useEffect(() => {
    if (secondsLeft <= 0) {
      onComplete?.()
      return
    }

    const timer = setInterval(() => {
      const remaining = calculateSecondsRemaining()
      setSecondsLeft(remaining)
      if (remaining <= 0) {
        clearInterval(timer)
        onComplete?.()
      }
    }, 1000)

    return () => clearInterval(timer)
  }, [executeAfter, secondsLeft])

  const handleCancelClick = async () => {
    setIsCancelling(true)
    setCancelError(null)
    try {
      await onCancel(actionRef)
      setIsCancelled(true)
    } catch (err: unknown) {
      const msg = (err as Error)?.message || 'Failed to cancel action'
      if (msg.includes('409') || msg.toLowerCase().includes('closed') || msg.toLowerCase().includes('worker')) {
        setCancelError('Action already dispatched to worker. Undo window closed.')
      } else {
        setCancelError(msg)
      }
    } finally {
      setIsCancelling(false)
    }
  }

  if (isCancelled) {
    return (
      <div
        data-testid="undo-cancelled-state"
        style={{
          padding: '0.625rem',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '0.375rem',
          color: '#991b1b',
          fontSize: '0.8125rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <span>🛑</span>
        <span>Action <strong>{actionRef}</strong> cancelled. Worker execution aborted.</span>
      </div>
    )
  }

  if (secondsLeft <= 0) {
    return (
      <div
        data-testid="undo-expired-state"
        style={{
          padding: '0.625rem',
          backgroundColor: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: '0.375rem',
          color: '#1e40af',
          fontSize: '0.8125rem',
        }}
      >
        <span>✓ Undo window ended. Dispatched to Google worker executor.</span>
      </div>
    )
  }

  return (
    <div
      data-testid="undo-countdown-banner"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        padding: '0.75rem',
        backgroundColor: '#fffbeb',
        border: '1px solid #fde68a',
        borderRadius: '0.5rem',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.1rem' }}>⏳</span>
          <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#92400e' }}>
            Undo window active: sending in <span data-testid="countdown-seconds">{secondsLeft}</span>s
          </span>
        </div>
        <span
          style={{
            fontSize: '0.7rem',
            fontFamily: 'monospace',
            color: '#b45309',
            backgroundColor: '#fef3c7',
            padding: '0.1rem 0.35rem',
            borderRadius: '0.2rem',
          }}
        >
          {actionRef}
        </span>
      </div>

      {cancelError && (
        <div
          data-testid="undo-error"
          style={{
            color: '#b91c1c',
            fontSize: '0.75rem',
            fontWeight: 600,
          }}
        >
          ⚠️ {cancelError}
        </div>
      )}

      <button
        type="button"
        data-testid="undo-cancel-button"
        disabled={isCancelling}
        onClick={handleCancelClick}
        style={{
          minHeight: '44px',
          width: '100%',
          backgroundColor: '#dc2626',
          color: 'white',
          border: 'none',
          borderRadius: '0.375rem',
          fontSize: '0.875rem',
          fontWeight: 700,
          cursor: isCancelling ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
        }}
      >
        {isCancelling ? 'Cancelling...' : '🛑 Undo Sending (Cancel Action)'}
      </button>
    </div>
  )
}

