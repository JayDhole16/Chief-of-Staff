/**
 * Home-page AI key card: lets each user connect their own AI provider without
 * leaving the Overview. The server never supplies a key of its own.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { ApiKeysResponse, TestResult, User } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { KeyIcon } from './Icons'
import { Spinner } from './ui'

export function QuickKeySetup({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [keys, setKeys] = useState<ApiKeysResponse | null>(null)
  const [provider, setProvider] = useState('anthropic')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [busy, setBusy] = useState<'save' | 'test' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TestResult | null>(null)

  const load = useCallback(() => {
    apiCall<ApiKeysResponse>('/settings/api-keys')
      .then(setKeys)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  useEffect(load, [load])

  const syncUser = async () => {
    try {
      ctx.onUserChange(await apiCall<User>('/profile'))
    } catch {
      // the card already shows the saved state; the rail badge refreshes on next load
    }
  }

  const test = async (name: string) => {
    setBusy('test')
    setError(null)
    try {
      const res = await apiCall<TestResult>(`/settings/api-keys/${name}/test`, { method: 'POST' })
      setResult(res)
      ctx.notify(res.ok ? 'AI provider connected' : 'The provider rejected this key', res.ok ? 'ok' : 'error')
      load()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy('save')
    setError(null)
    setResult(null)
    try {
      const next = await apiCall<ApiKeysResponse>(`/settings/api-keys/${provider}`, {
        method: 'PUT',
        body: { api_key: apiKey.trim() || null, model: model.trim() || null, base_url: baseUrl.trim() || null, make_active: true },
      })
      setKeys(next)
      setApiKey('')
      await syncUser()
      setBusy(null)
      await test(provider)
    } catch (err) {
      setError(errorMessage(err))
      setBusy(null)
    }
  }

  if (!keys) {
    return <div className="cos-card-elevated" style={{ marginBottom: '1.25rem' }}>{error ? <div className="cos-alert cos-alert-error">{error}</div> : <Spinner />}</div>
  }

  const active = keys.providers.find((p) => p.provider === keys.active_provider && p.configured)
  const selected = keys.providers.find((p) => p.provider === provider)

  if (active) {
    const lastOk = result?.ok ?? active.last_test_ok
    const lastMessage = result?.message ?? active.last_test_message
    return (
      <div className="cos-card" style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ width: '36px', height: '36px', borderRadius: '10px', backgroundColor: 'var(--emerald-tint)', border: '1px solid var(--border-emerald)', color: 'var(--emerald-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <KeyIcon size={18} />
        </div>
        <div style={{ flex: 1, minWidth: '220px' }}>
          <div style={{ fontWeight: 700, color: '#FFFFFF', fontSize: '0.88rem' }}>
            AI provider: {active.label}{' '}
            {lastOk === true && <span className="cos-badge cos-badge-green">connected</span>}
            {lastOk === false && <span className="cos-badge cos-badge-red">key rejected</span>}
            {lastOk == null && <span className="cos-badge">not tested</span>}
          </div>
          <div className="cos-muted" style={{ fontSize: '0.76rem', marginTop: '0.15rem' }}>
            <span className="cos-mono">{active.masked_key ?? 'no key'}</span> · {active.model || active.default_model} · billed to your own account
            {lastOk === false && lastMessage ? ` · ${lastMessage}` : ''}
          </div>
          {error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.5rem', fontSize: '0.76rem' }}>{error}</div>}
        </div>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => test(active.provider)} disabled={busy !== null}>
            {busy === 'test' ? 'Testing...' : 'Test'}
          </button>
          <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => ctx.navigate('keys')}>
            Manage keys
          </button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={save} className="cos-card-elevated" style={{ marginBottom: '1.25rem', borderColor: 'var(--border-emerald)' }} aria-label="Connect your AI provider">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.35rem' }}>
        <span style={{ color: 'var(--emerald-glow)' }}>
          <KeyIcon size={18} />
        </span>
        <span style={{ fontWeight: 800, color: '#FFFFFF' }}>Connect your AI provider</span>
      </div>
      <p className="cos-muted" style={{ fontSize: '0.82rem', lineHeight: 1.55, marginBottom: '0.9rem' }}>
        Chief of Staff runs on <strong style={{ color: '#FFFFFF' }}>your own API key</strong>, so usage is billed to your provider account and you can see every token in API Keys. The key is encrypted and only the last 4 characters are ever shown.
      </p>
      <div className="cos-grid" style={{ gridTemplateColumns: 'minmax(160px, 1fr) minmax(220px, 2fr) minmax(160px, 1fr)', gap: '0.75rem' }}>
        <div>
          <label className="cos-label" htmlFor="quick-provider">Provider</label>
          <select
            id="quick-provider"
            className="cos-select"
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value)
              setModel('')
              setBaseUrl('')
            }}
          >
            {keys.providers.map((p) => (
              <option key={p.provider} value={p.provider}>
                {p.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="cos-label" htmlFor="quick-key">API key</label>
          <input
            id="quick-key"
            className="cos-input cos-mono"
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={selected?.key_hint}
            required={provider !== 'custom'}
          />
        </div>
        <div>
          <label className="cos-label" htmlFor="quick-model">
            Model <span className="cos-dim" style={{ fontWeight: 400 }}>(optional)</span>
          </label>
          <input id="quick-model" className="cos-input cos-mono" value={model} onChange={(e) => setModel(e.target.value)} placeholder={selected?.default_model || 'model name'} required={provider === 'custom'} />
        </div>
      </div>
      {provider === 'custom' && (
        <div style={{ marginTop: '0.75rem' }}>
          <label className="cos-label" htmlFor="quick-url">Base URL</label>
          <input id="quick-url" className="cos-input cos-mono" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:11434/v1" required />
        </div>
      )}
      {result && !result.ok && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.75rem' }}>{result.message}</div>}
      {error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.75rem' }}>{error}</div>}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.9rem', gap: '0.5rem', flexWrap: 'wrap' }}>
        {selected?.docs_url ? (
          <a href={selected.docs_url} target="_blank" rel="noreferrer" style={{ color: 'var(--emerald-glow)', fontSize: '0.78rem' }}>
            Get a {selected.label} key ↗
          </a>
        ) : (
          <span />
        )}
        <button type="submit" className="cos-btn cos-btn-primary" disabled={busy !== null || (provider !== 'custom' && !apiKey.trim())}>
          {busy === 'save' ? 'Saving...' : busy === 'test' ? 'Testing...' : 'Save & test key'}
        </button>
      </div>
    </form>
  )
}
