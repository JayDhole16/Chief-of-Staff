/**
 * Dashboard shell: icon rail navigation, toast notifications and view routing.
 * All data comes from the signed-in user's workspace on the backend.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { apiCall } from '../api/client'
import type { ApprovalsResponse, User } from '../api/types'
import {
  ActivityIcon,
  ApprovalIcon,
  ChatIcon,
  DealsIcon,
  HomeIcon,
  KeyIcon,
  LogoStar,
  LogoutIcon,
  SettingsIcon,
} from '../components/Icons'
import { HomeView } from '../views/HomeView'
import { ChatView } from '../views/ChatView'
import { DealsView } from '../views/DealsView'
import { ApprovalsView } from '../views/ApprovalsView'
import { ActivityView } from '../views/ActivityView'
import { ApiKeysView } from '../views/ApiKeysView'
import { SettingsView } from '../views/SettingsView'

export type ViewId = 'home' | 'chat' | 'deals' | 'approvals' | 'activity' | 'keys' | 'settings'

export interface DashboardContext {
  user: User
  onUserChange: (user: User) => void
  navigate: (view: ViewId) => void
  notify: (message: string, tone?: 'ok' | 'error') => void
  refreshApprovals: () => void
}

export interface DashboardPageProps {
  user: User
  onUserChange: (user: User) => void
  onLogout: () => void
}

const NAV: Array<{ id: ViewId; label: string; icon: (p: { size?: number }) => JSX.Element }> = [
  { id: 'home', label: 'Overview', icon: HomeIcon },
  { id: 'chat', label: 'Chat', icon: ChatIcon },
  { id: 'deals', label: 'Deals', icon: DealsIcon },
  { id: 'approvals', label: 'Approvals', icon: ApprovalIcon },
  { id: 'activity', label: 'Activity', icon: ActivityIcon },
  { id: 'keys', label: 'API Keys', icon: KeyIcon },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
]

export function DashboardPage({ user, onUserChange, onLogout }: DashboardPageProps): JSX.Element {
  const [view, setView] = useState<ViewId>('home')
  const [pendingCount, setPendingCount] = useState(0)
  const [toast, setToast] = useState<{ message: string; tone: 'ok' | 'error' } | null>(null)
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const notify = useCallback((message: string, tone: 'ok' | 'error' = 'ok') => {
    setToast({ message, tone })
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 4000)
  }, [])

  const refreshApprovals = useCallback(() => {
    apiCall<ApprovalsResponse>('/approvals?status=pending')
      .then((res) => setPendingCount(res.count))
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    refreshApprovals()
    const id = setInterval(refreshApprovals, 30000)
    return () => clearInterval(id)
  }, [refreshApprovals])

  useEffect(() => () => {
    if (toastTimer.current) clearTimeout(toastTimer.current)
  }, [])

  // Returning from Google's consent screen: /?google=connected|partial|error&message=...
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const result = params.get('google')
    if (!result) return
    const message = params.get('message')
    if (result === 'connected') notify(`Google connected${message ? `: ${message}` : ''}`)
    else notify(message || 'Google connection failed', 'error')
    setView('keys')
    window.history.replaceState(null, '', window.location.pathname)
  }, [notify])

  const ctx: DashboardContext = { user, onUserChange, navigate: setView, notify, refreshApprovals }
  const initials = user.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%', overflow: 'hidden', backgroundColor: 'var(--bg-void)' }}>
      {toast && (
        <div
          role="status"
          style={{
            position: 'fixed',
            top: '1rem',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 300,
            backgroundColor: 'var(--bg-elevated)',
            border: `1px solid ${toast.tone === 'ok' ? 'var(--border-emerald)' : 'rgba(244, 63, 94, 0.45)'}`,
            color: 'var(--text-main)',
            padding: '0.65rem 1rem',
            borderRadius: '12px',
            fontSize: '0.8rem',
            fontWeight: 600,
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.55)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            maxWidth: '90vw',
          }}
          className="chat-msg-animate"
        >
          <span style={{ color: toast.tone === 'ok' ? 'var(--emerald-glow)' : '#FB7185' }}>●</span>
          <span>{toast.message}</span>
        </div>
      )}

      <aside
        style={{
          width: '64px',
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '1rem 0',
          borderRight: '1px solid var(--border-hairline)',
          backgroundColor: 'var(--bg-rail)',
          zIndex: 40,
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.25rem' }}>
          <button
            type="button"
            data-testid="top-left-logo-button"
            onClick={() => setView('home')}
            title="Chief of Staff — Overview"
            aria-label="Chief of Staff — Overview"
            className="glow-emerald-sm"
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '16px',
              backgroundColor: '#091510',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: 'var(--emerald-glow)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
          >
            <LogoStar size={24} />
          </button>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', alignItems: 'center' }} aria-label="Main">
            {NAV.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                data-testid={`rail-${id}-button`}
                className={`cos-rail-btn${view === id ? ' active' : ''}`}
                onClick={() => setView(id)}
                title={label}
                aria-label={label}
                aria-current={view === id ? 'page' : undefined}
              >
                <Icon size={20} />
                {id === 'approvals' && pendingCount > 0 && <span className="cos-rail-badge">{pendingCount}</span>}
              </button>
            ))}
          </nav>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.6rem' }}>
          <button type="button" className="cos-rail-btn" onClick={onLogout} title="Sign out" aria-label="Sign out">
            <LogoutIcon size={18} />
          </button>
          <button
            type="button"
            onClick={() => setView('settings')}
            title={`${user.name} · ${user.email}`}
            aria-label="Profile and settings"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: '#18212D',
              border: view === 'settings' ? '2px solid var(--emerald-glow)' : '1px solid var(--border-subtle)',
              color: '#FFFFFF',
              fontSize: '0.75rem',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {initials || '?'}
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        {user.kill_switch_active && (
          <div className="cos-alert cos-alert-warn" style={{ borderRadius: 0, borderLeft: 'none', borderRight: 'none', borderTop: 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
            <span>
              <strong>Kill switch engaged.</strong> Drafting and sending are paused{user.kill_switch_reason ? ` · ${user.kill_switch_reason}` : ''}.
            </span>
            <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => setView('settings')}>
              Manage
            </button>
          </div>
        )}
        {view === 'home' && <HomeView ctx={ctx} />}
        {view === 'chat' && <ChatView ctx={ctx} />}
        {view === 'deals' && <DealsView ctx={ctx} />}
        {view === 'approvals' && <ApprovalsView ctx={ctx} />}
        {view === 'activity' && <ActivityView ctx={ctx} />}
        {view === 'keys' && <ApiKeysView ctx={ctx} />}
        {view === 'settings' && <SettingsView ctx={ctx} onLogout={onLogout} />}
      </main>
    </div>
  )
}
