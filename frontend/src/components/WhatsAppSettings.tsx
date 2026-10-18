/**
 * WhatsApp credentials card (API Keys page): Twilio or Meta WhatsApp Cloud API,
 * using the user's own provider account. Secrets are stored encrypted and shown masked.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { TestResult, WhatsAppSettingsResponse } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { Spinner } from './ui'

type Provider = 'twilio' | 'meta'

const HELP: Record<Provider, { account: string; accountHint: string; token: string; link: string; linkLabel: string }> = {
  twilio: {
    account: 'Account SID',
    accountHint: 'AC…',
    token: 'Auth Token',
    link: 'https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn',
    linkLabel: 'Twilio WhatsApp Sandbox',
  },
  meta: {
    account: 'Phone Number ID',
    accountHint: 'numeric id from WhatsApp Manager → API Setup',
    token: 'Access token',
    link: 'https://developers.facebook.com/docs/whatsapp/cloud-api/get-started',
    linkLabel: 'Meta Cloud API setup',
  },
}

export function WhatsAppSettings({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [data, setData] = useState<WhatsAppSettingsResponse | null>(null)
  const [editing, setEditing] = useState(false)
  const [provider, setProvider] = useState<Provider>('twilio')
  const [accountId, setAccountId] = useState('')
  const [token, setToken] = useState('')
  const [fromNumber, setFromNumber] = useState('')
  const [busy, setBusy] = useState<'save' | 'test' | 'delete' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [test, setTest] = useState<TestResult | null>(null)

  const load = useCallback(() => {
    apiCall<WhatsAppSettingsResponse>('/settings/whatsapp')
      .then((res) => {
        setData(res)
        if (res.settings) {
          setProvider(res.settings.provider)
          setAccountId(res.settings.account_id)
          setFromNumber(res.settings.from_number)
        }
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  useEffect(load, [load])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy('save')
    setError(null)
    try {
      const res = await apiCall<WhatsAppSettingsResponse>('/settings/whatsapp', {
        method: 'PUT',
        body: { provider, account_id: accountId, token: token || null, from_number: fromNumber },
      })
      setData(res)
      setToken('')
      setEditing(false)
      setTest(null)
      ctx.notify('WhatsApp credentials saved')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const runTest = async () => {
    setBusy('test')
    setError(null)
    try {
      setTest(await apiCall<TestResult>('/settings/whatsapp/test', { method: 'POST' }))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const remove = async () => {
    if (!window.confirm('Remove your WhatsApp credentials?')) return
    setBusy('delete')
    try {
      setData(await apiCall<WhatsAppSettingsResponse>('/settings/whatsapp', { method: 'DELETE' }))
      setTest(null)
      ctx.notify('WhatsApp credentials removed')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const s = data?.settings
  const help = HELP[provider]
  const lastTest = test ?? (s?.last_tested_at ? { ok: Boolean(s.last_test_ok), message: s.last_test_message ?? '', tested_at: s.last_tested_at } : null)

  return (
    <>
      <h2 style={{ fontSize: '1rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ color: '#25D366' }} aria-hidden="true">●</span> WhatsApp messaging
      </h2>
      <div className="cos-card" style={{ marginBottom: '2rem', borderColor: s ? 'var(--border-emerald)' : undefined }}>
        <p className="cos-muted" style={{ fontSize: '0.82rem', lineHeight: 1.55, marginBottom: '0.85rem' }}>
          Lets your chief of staff prepare WhatsApp messages (you confirm each one). Use your own <strong style={{ color: '#FFFFFF' }}>Twilio</strong> or <strong style={{ color: '#FFFFFF' }}>Meta WhatsApp Cloud API</strong> account. Free-form messages reach contacts who messaged your number in the last 24 hours (or who joined your Twilio sandbox).
        </p>
        {!data && !error && <Spinner />}
        {data && !editing && (
          <>
            {s ? (
              <div style={{ fontSize: '0.84rem' }}>
                <span className="cos-badge cos-badge-green">Connected</span>{' '}
                <strong style={{ color: '#FFFFFF' }}>{data.providers[s.provider]}</strong>
                <span className="cos-muted">
                  {' '}
                  · {s.provider === 'twilio' ? `sender ${s.from_number}` : `number id ${s.account_id}`} · token <span className="cos-mono">{s.masked_token}</span>
                </span>
              </div>
            ) : (
              <div className="cos-muted" style={{ fontSize: '0.84rem' }}>No WhatsApp account connected.</div>
            )}
            {lastTest && (
              <div className={`cos-alert ${lastTest.ok ? 'cos-alert-info' : 'cos-alert-error'}`} style={{ marginTop: '0.7rem', fontSize: '0.75rem' }}>
                {lastTest.ok ? '✓ ' : '✗ '}
                {lastTest.message}
              </div>
            )}
            <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.85rem' }}>
              <button type="button" className={`cos-btn cos-btn-sm ${s ? 'cos-btn-ghost' : 'cos-btn-primary'}`} onClick={() => setEditing(true)}>
                {s ? 'Update' : 'Connect WhatsApp'}
              </button>
              {s && (
                <>
                  <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={runTest} disabled={busy !== null}>
                    {busy === 'test' ? 'Testing...' : 'Test credentials'}
                  </button>
                  <button type="button" className="cos-btn cos-btn-danger cos-btn-sm" onClick={remove} disabled={busy !== null}>
                    Remove
                  </button>
                </>
              )}
            </div>
          </>
        )}
        {editing && (
          <form onSubmit={save} style={{ display: 'grid', gap: '0.7rem' }}>
            <div>
              <label className="cos-label" htmlFor="wa-provider">Provider</label>
              <select id="wa-provider" className="cos-select" value={provider} onChange={(e) => setProvider(e.target.value as Provider)}>
                <option value="twilio">Twilio (easiest for testing: sandbox)</option>
                <option value="meta">Meta WhatsApp Cloud API</option>
              </select>
            </div>
            <div className="cos-grid cos-grid-2" style={{ gap: '0.7rem' }}>
              <div>
                <label className="cos-label" htmlFor="wa-account">{help.account}</label>
                <input id="wa-account" className="cos-input cos-mono" value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder={help.accountHint} required />
              </div>
              <div>
                <label className="cos-label" htmlFor="wa-token">
                  {help.token} {s?.has_token && s.provider === provider && <span className="cos-dim" style={{ fontWeight: 400 }}>(blank keeps current)</span>}
                </label>
                <input id="wa-token" className="cos-input cos-mono" type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} />
              </div>
            </div>
            {provider === 'twilio' && (
              <div>
                <label className="cos-label" htmlFor="wa-from">WhatsApp sender number</label>
                <input id="wa-from" className="cos-input cos-mono" value={fromNumber} onChange={(e) => setFromNumber(e.target.value)} placeholder="+14155238886 (Twilio sandbox)" required />
              </div>
            )}
            {error && <div className="cos-alert cos-alert-error">{error}</div>}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <a href={help.link} target="_blank" rel="noreferrer" style={{ color: 'var(--emerald-glow)', fontSize: '0.75rem' }}>
                {help.linkLabel} ↗
              </a>
              <div style={{ display: 'flex', gap: '0.4rem' }}>
                <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => setEditing(false)}>
                  Cancel
                </button>
                <button type="submit" className="cos-btn cos-btn-primary cos-btn-sm" disabled={busy !== null}>
                  {busy === 'save' ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </form>
        )}
        {!editing && error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.75rem' }}>{error}</div>}
      </div>
    </>
  )
}
