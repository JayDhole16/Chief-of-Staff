/**
 * Main app: router between login and dashboard, session management.
 */

import React, { useEffect, useState } from 'react'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { OfflineBanner } from './components/ErrorBoundary'
import { clearSession, hasSession } from './api/client'
import type { LoginResponse } from './api/types'

export function App(): JSX.Element {
  const [session, setSession] = useState<LoginResponse | null>(null)
  const [isChecking, setIsChecking] = useState(true)

  // Restore session from sessionStorage on mount
  useEffect(() => {
    if (hasSession()) {
      const stored = sessionStorage.getItem('session_data')
      if (stored) {
        try {
          setSession(JSON.parse(stored))
        } catch {
          clearSession()
        }
      }
    }
    setIsChecking(false)
  }, [])

  const handleLoginSuccess = (response: LoginResponse) => {
    sessionStorage.setItem('session_data', JSON.stringify(response))
    setSession(response)
  }

  const handleUpdateSession = (updated: LoginResponse) => {
    sessionStorage.setItem('session_data', JSON.stringify(updated))
    setSession(updated)
  }

  const handleLogout = () => {
    sessionStorage.removeItem('session_data')
    clearSession()
    setSession(null)
  }

  if (isChecking) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          backgroundColor: 'var(--bg-void, #07090C)',
        }}
      >
        <div style={{ fontSize: '0.875rem', color: 'var(--text-muted, #94A3B8)' }}>
          Initializing Chief of Staff...
        </div>
      </div>
    )
  }

  return (
    <>
      <OfflineBanner />
      {!session ? (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      ) : (
        <DashboardPage
          session={session}
          onLogout={handleLogout}
          onUpdateSession={handleUpdateSession}
        />
      )}
    </>
  )
}
