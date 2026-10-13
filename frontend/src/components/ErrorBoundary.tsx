/**
 * Error states with retry capability.
 */

import React from 'react'

export interface ErrorStateProps {
  error: Error | null
  onRetry?: () => void
}

export function ErrorState({ error, onRetry }: ErrorStateProps): JSX.Element {
  return (
    <div
      style={{
        padding: '1.5rem',
        backgroundColor: '#fee2e2',
        border: '1px solid #fca5a5',
        borderRadius: '0.5rem',
        color: '#991b1b',
      }}
    >
      <h3 style={{ margin: '0 0 0.5rem 0' }}>Error</h3>
      <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem' }}>
        {error?.message || 'An unknown error occurred'}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#991b1b',
            color: 'white',
            border: 'none',
            borderRadius: '0.25rem',
            cursor: 'pointer',
            fontSize: '0.875rem',
          }}
        >
          Retry
        </button>
      )}
    </div>
  )
}

export interface EmptyStateProps {
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export function EmptyState({ title, description, action }: EmptyStateProps): JSX.Element {
  return (
    <div
      style={{
        padding: '2rem',
        textAlign: 'center',
        color: '#6b7280',
      }}
    >
      <h3 style={{ margin: '0 0 0.5rem 0', color: '#374151' }}>{title}</h3>
      {description && (
        <p style={{ margin: '0 0 1.5rem 0', fontSize: '0.875rem' }}>{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '0.25rem',
            cursor: 'pointer',
            fontSize: '0.875rem',
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

export function OfflineBanner(): JSX.Element {
  const [isOnline, setIsOnline] = React.useState(navigator.onLine)

  React.useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  if (isOnline) return <></>

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        backgroundColor: '#fbbf24',
        color: '#78350f',
        padding: '0.75rem',
        textAlign: 'center',
        fontSize: '0.875rem',
        zIndex: 1000,
      }}
    >
      You are offline
    </div>
  )
}
