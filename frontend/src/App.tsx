/**
 * Main app: validates the stored session with the backend, then routes between
 * the auth page and the dashboard.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { OfflineBanner } from './components/ErrorBoundary'
import { apiCall, clearSession, hasSession, SESSION_EXPIRED_EVENT, setSession } from './api/client'
import type { LoginResponse, User } from './api/types'

export function App(): JSX.Element {
  const [user, setUser] = useState<User | null>(null)
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    let cancelled = false
    if (!hasSession()) {
      setIsChecking(false)
      return
    }
    apiCall<LoginResponse>('/session')
      .then((res) => {
        if (!cancelled) setUser(res.user)
      })
      .catch(() => {
        clearSession()
      })
      .finally(() => {
        if (!cancelled) setIsChecking(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const onExpired = () => setUser(null)
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [])

  const handleAuthSuccess = useCallback((response: LoginResponse) => {
    setSession(response.session_id)
    setUser(response.user)
  }, [])

  const handleLogout = useCallback(async () => {
    try {
      await apiCall('/auth/logout', { method: 'POST' })
    } catch {
      // session may already be gone; sign out locally regardless
    }
    clearSession()
    setUser(null)
  }, [])

  if (isChecking) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          backgroundColor: 'var(--bg-void)',
        }}
      >
        <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Loading Chief of Staff...</div>
      </div>
    )
  }

  return (
    <>
      <OfflineBanner />
      {!user ? (
        <LoginPage onLoginSuccess={handleAuthSuccess} />
      ) : (
        <DashboardPage user={user} onUserChange={setUser} onLogout={handleLogout} />
      )}
    </>
  )
}
