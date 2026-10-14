/**
 * Loading skeleton UI components.
 */

export function SkeletonLine(): JSX.Element {
  return (
    <div
      style={{
        height: '1rem',
        backgroundColor: '#e5e7eb',
        borderRadius: '0.25rem',
        animation: 'pulse 2s infinite',
      }}
    />
  )
}

export function SkeletonCard(): JSX.Element {
  return (
    <div
      style={{
        padding: '1rem',
        border: '1px solid #e5e7eb',
        borderRadius: '0.5rem',
        backgroundColor: '#f9fafb',
      }}
    >
      <SkeletonLine />
      <div style={{ marginTop: '0.5rem' }}>
        <SkeletonLine />
      </div>
      <div style={{ marginTop: '0.5rem' }}>
        <SkeletonLine />
      </div>
    </div>
  )
}

export function LoadingSpinner(): JSX.Element {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        padding: '2rem',
      }}
    >
      <div
        style={{
          width: '2rem',
          height: '2rem',
          border: '3px solid #e5e7eb',
          borderTop: '3px solid #3b82f6',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }}
      />
    </div>
  )
}
