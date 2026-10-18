/**
 * Google (Gmail + Calendar) connection card: each user signs in with their own
 * Google account via OAuth. Tokens stay encrypted on the server.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { GoogleStatus, TestResult } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { Spinner } from './ui'
import { formatDateTime } from '../utils/formatters'

function GoogleLogo({ size = 18 }: { size?: number }): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.6-.4-3.9z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.6-.4-3.9z" />
    </svg>
  )
}

export function GoogleConnect({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [status, setStatus] = useState<GoogleStatus | null>(null)
  const [busy, setBusy] = useState<'connect' | 'test' | 'disconnect' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [test, setTest] = useState<TestResult | null>(null)

  const load = useCallback(() => {
    apiCall<GoogleStatus>('/integrations/google')
      .then(setStatus)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  useEffect(load, [load])

  const connect = async () => {
    setBusy('connect')
    setError(null)
    try {
      const { auth_url } = await apiCall<{ auth_url: string }>('/integrations/google/connect', { method: 'POST' })
      window.location.assign(auth_url)
    } catch (err) {
      setError(errorMessage(err))
      setBusy(null)
    }
  }

  const runTest = async () => {
    setBusy('test')
    setError(null)
    try {
      setTest(await apiCall<TestResult>('/integrations/google/test', { method: 'POST' }))
      load()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const disconnect = async () => {
    if (!window.confirm('Disconnect Google? Chief of Staff will stop sending from Gmail and booking meetings.')) return
    setBusy('disconnect')
    try {
      setStatus(await apiCall<GoogleStatus>('/integrations/google', { method: 'DELETE' }))
      setTest(null)
      ctx.notify('Google disconnected and access revoked')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  return (
    <>
      <h2 style={{ fontSize: '1rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <GoogleLogo /> Google: Gmail &amp; Calendar
      </h2>
      <div className="cos-card" style={{ marginBottom: '2rem', borderColor: status?.connected ? 'var(--border-emerald)' : undefined }}>
        <p className="cos-muted" style={{ fontSize: '0.82rem', lineHeight: 1.55, marginBottom: '0.85rem' }}>
          Sign in with your Google account to send approved follow-ups from your Gmail and book meetings (with Google Meet links) on your calendar. Chief of Staff only asks for permission to <strong style={{ color: '#FFFFFF' }}>send email</strong> and <strong style={{ color: '#FFFFFF' }}>manage calendar events</strong>. It never reads your inbox.
        </p>
        {!status && !error && <Spinner />}
        {status && !status.configured && (
          <div className="cos-alert cos-alert-warn">
            Google sign-in isn&apos;t enabled on this server yet. The app owner needs to add <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> to the server&apos;s <code>.env</code> and restart the API.
          </div>
        )}
        {status?.configured && !status.connected && (
          <button type="button" className="cos-btn cos-btn-primary" onClick={connect} disabled={busy !== null}>
            <GoogleLogo size={16} /> {busy === 'connect' ? 'Opening Google...' : 'Connect Google account'}
          </button>
        )}
        {status?.connected && (
          <>
            <div style={{ fontSize: '0.84rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span className={`cos-badge ${status.last_error ? 'cos-badge-red' : 'cos-badge-green'}`}>{status.last_error ? 'needs attention' : 'connected'}</span>
              <strong style={{ color: '#FFFFFF' }}>{status.email}</strong>
              {status.connected_at && <span className="cos-dim">since {formatDateTime(status.connected_at)}</span>}
            </div>
            <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.6rem', flexWrap: 'wrap' }}>
              <span className={`cos-badge ${status.can_send_email ? 'cos-badge-green' : 'cos-badge-red'}`}>Gmail send {status.can_send_email ? '✓' : '✗'}</span>
              <span className={`cos-badge ${status.can_manage_calendar ? 'cos-badge-green' : 'cos-badge-red'}`}>Calendar events {status.can_manage_calendar ? '✓' : '✗'}</span>
            </div>
            {status.last_error && (
              <div className="cos-alert cos-alert-error" style={{ marginTop: '0.7rem', fontSize: '0.78rem' }}>
                {status.last_error}
              </div>
            )}
            {(!status.can_send_email || !status.can_manage_calendar) && (
              <div className="cos-alert cos-alert-warn" style={{ marginTop: '0.7rem', fontSize: '0.78rem' }}>
                Some permissions weren&apos;t granted. Reconnect and tick both boxes on Google&apos;s consent screen.
              </div>
            )}
            {test && (
              <div className={`cos-alert ${test.ok ? 'cos-alert-info' : 'cos-alert-error'}`} style={{ marginTop: '0.7rem', fontSize: '0.75rem' }}>
                {test.ok ? '✓ ' : '✗ '}
                {test.message}
              </div>
            )}
            <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.85rem', flexWrap: 'wrap' }}>
              <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={runTest} disabled={busy !== null}>
                {busy === 'test' ? 'Testing...' : 'Test connection'}
              </button>
              <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={connect} disabled={busy !== null}>
                Reconnect
              </button>
              <button type="button" className="cos-btn cos-btn-danger cos-btn-sm" onClick={disconnect} disabled={busy !== null}>
                Disconnect
              </button>
            </div>
          </>
        )}
        {error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.75rem' }}>{error}</div>}
      </div>
    </>
  )
}
