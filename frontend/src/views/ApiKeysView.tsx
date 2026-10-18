/**
 * API Keys & Integrations: each founder brings their own AI provider key and SMTP
 * account. Keys are encrypted server-side and only ever shown masked. Token usage is
 * tracked per provider/model so founders see exactly what they spend.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { ApiKeysResponse, EmailSettingsResponse, ProviderKey, TestResult, UsageResponse, User } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { KeyIcon, MailIcon, TrashIcon } from '../components/Icons'
import { PageHeader, Spinner } from '../components/ui'
import { GoogleConnect } from '../components/GoogleConnect'
import { WhatsAppSettings } from '../components/WhatsAppSettings'
import { formatDateTime, formatTokens, timeAgo } from '../utils/formatters'

export function ApiKeysView({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [keys, setKeys] = useState<ApiKeysResponse | null>(null)
  const [usage, setUsage] = useState<UsageResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const syncUser = useCallback(() => {
    apiCall<User>('/profile')
      .then(ctx.onUserChange)
      .catch(() => undefined)
  }, [ctx.onUserChange])

  const load = useCallback(() => {
    Promise.all([apiCall<ApiKeysResponse>('/settings/api-keys'), apiCall<UsageResponse>('/settings/usage')])
      .then(([k, u]) => {
        setKeys(k)
        setUsage(u)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  useEffect(load, [load])

  const onKeysChanged = (next: ApiKeysResponse) => {
    setKeys(next)
    syncUser()
  }

  const setActive = async (provider: string) => {
    try {
      onKeysChanged(await apiCall<ApiKeysResponse>('/settings/active-provider', { method: 'PUT', body: { provider } }))
      ctx.notify(`${provider} is now your active AI provider`)
    } catch (err) {
      ctx.notify(errorMessage(err), 'error')
    }
  }

  return (
    <div className="cos-page">
      <div className="cos-page-inner" style={{ maxWidth: '960px' }}>
        <PageHeader
          title="API Keys & Integrations"
          subtitle="Use your own provider accounts. You pay your provider directly, see every token used, and can revoke a key at any time."
        />

        <div className="cos-alert cos-alert-info" style={{ marginBottom: '1.25rem' }}>
          Keys are encrypted at rest (Fernet/AES) and never sent back to the browser. Only the last 4 characters are shown. They are used only for your own chats and drafts.
        </div>

        {error && <div className="cos-alert cos-alert-error">{error}</div>}
        {!keys && !error && <Spinner />}

        {keys && (
          <>
            <h2 style={{ fontSize: '1rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <KeyIcon size={17} /> AI providers
              <span className="cos-dim" style={{ fontSize: '0.78rem', fontWeight: 500 }}>
                · active: {keys.active_provider ?? 'none'}
              </span>
            </h2>
            <div className="cos-grid cos-grid-2" style={{ marginBottom: '2rem' }}>
              {keys.providers.map((p) => (
                <ProviderCard key={p.provider} provider={p} active={keys.active_provider === p.provider} onChanged={onKeysChanged} onSetActive={setActive} ctx={ctx} />
              ))}
            </div>

            <h2 style={{ fontSize: '1rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '0.75rem' }}>Usage & cost transparency</h2>
            <div className="cos-card" style={{ marginBottom: '2rem' }}>
              {!usage || usage.total_requests === 0 ? (
                <div className="cos-muted" style={{ fontSize: '0.84rem' }}>No AI requests yet. Token usage from chats, drafts and key tests appears here.</div>
              ) : (
                <>
                  <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                    <Metric label="Requests" value={String(usage.total_requests)} />
                    <Metric label="Input tokens" value={formatTokens(usage.total_input_tokens)} />
                    <Metric label="Output tokens" value={formatTokens(usage.total_output_tokens)} />
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table className="cos-table">
                      <thead>
                        <tr>
                          <th>Provider</th>
                          <th>Model</th>
                          <th>Requests</th>
                          <th>Input</th>
                          <th>Output</th>
                          <th>Last used</th>
                        </tr>
                      </thead>
                      <tbody>
                        {usage.by_model.map((r) => (
                          <tr key={`${r.provider}-${r.model}`}>
                            <td>{r.provider}</td>
                            <td className="cos-mono">{r.model}</td>
                            <td>{r.requests}</td>
                            <td>{formatTokens(r.input_tokens)}</td>
                            <td>{formatTokens(r.output_tokens)}</td>
                            <td className="cos-dim">{timeAgo(r.last_used_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="cos-dim" style={{ fontSize: '0.72rem', marginTop: '0.6rem' }}>
                    Multiply by your provider's per-token price to get the cost. Token counts come straight from each provider's response.
                  </div>
                </>
              )}
            </div>

            <GoogleConnect ctx={ctx} />
            <WhatsAppSettings ctx={ctx} />
            <EmailSection ctx={ctx} />
          </>
        )}
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div>
      <div className="cos-dim" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>{label}</div>
      <div className="cos-mono" style={{ fontSize: '1.3rem', fontWeight: 800, color: '#FFFFFF' }}>{value}</div>
    </div>
  )
}

function ProviderCard({
  provider,
  active,
  onChanged,
  onSetActive,
  ctx,
}: {
  provider: ProviderKey
  active: boolean
  onChanged: (next: ApiKeysResponse) => void
  onSetActive: (provider: string) => void
  ctx: DashboardContext
}): JSX.Element {
  const [open, setOpen] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState(provider.model ?? '')
  const [baseUrl, setBaseUrl] = useState(provider.base_url ?? '')
  const [busy, setBusy] = useState<'save' | 'test' | 'delete' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [test, setTest] = useState<TestResult | null>(null)
  const isCustom = provider.provider === 'custom'

  useEffect(() => {
    setModel(provider.model ?? '')
    setBaseUrl(provider.base_url ?? '')
  }, [provider.model, provider.base_url])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy('save')
    setError(null)
    try {
      const next = await apiCall<ApiKeysResponse>(`/settings/api-keys/${provider.provider}`, {
        method: 'PUT',
        body: { api_key: apiKey || null, model: model || null, base_url: baseUrl || null, make_active: true },
      })
      setApiKey('')
      setOpen(false)
      setTest(null)
      onChanged(next)
      ctx.notify(`${provider.label} saved and set as active`)
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
      const res = await apiCall<TestResult>(`/settings/api-keys/${provider.provider}/test`, { method: 'POST' })
      setTest(res)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const remove = async () => {
    if (!window.confirm(`Remove your ${provider.label} key?`)) return
    setBusy('delete')
    try {
      onChanged(await apiCall<ApiKeysResponse>(`/settings/api-keys/${provider.provider}`, { method: 'DELETE' }))
      setTest(null)
      ctx.notify(`${provider.label} key removed`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const lastTest = test ?? (provider.last_tested_at ? { ok: Boolean(provider.last_test_ok), message: provider.last_test_message ?? '', tested_at: provider.last_tested_at } : null)

  return (
    <div className="cos-card" style={{ borderColor: active ? 'var(--border-emerald)' : undefined }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
        <div>
          <div style={{ fontWeight: 800, color: '#FFFFFF', fontSize: '0.92rem' }}>{provider.label}</div>
          <div className="cos-dim" style={{ fontSize: '0.74rem', marginTop: '0.15rem' }}>
            {provider.configured ? (
              <>
                <span className="cos-mono">{provider.masked_key ?? 'no key'}</span> · {provider.model || provider.default_model}
              </>
            ) : (
              `Default model: ${provider.default_model || 'set your own'}`
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
          {active && <span className="cos-badge cos-badge-green">Active</span>}
          {provider.configured && !active && (
            <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => onSetActive(provider.provider)}>
              Use
            </button>
          )}
        </div>
      </div>

      {lastTest && (
        <div className={`cos-alert ${lastTest.ok ? 'cos-alert-info' : 'cos-alert-error'}`} style={{ marginTop: '0.7rem', fontSize: '0.75rem' }}>
          {lastTest.ok ? '✓ ' : '✗ '}
          {lastTest.message} <span className="cos-dim">· {formatDateTime(lastTest.tested_at)}</span>
        </div>
      )}
      {error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.7rem', fontSize: '0.75rem' }}>{error}</div>}

      {open ? (
        <form onSubmit={save} style={{ marginTop: '0.85rem', display: 'grid', gap: '0.6rem' }}>
          <div>
            <label className="cos-label" htmlFor={`key-${provider.provider}`}>
              API key {provider.configured && <span className="cos-dim" style={{ fontWeight: 400 }}>(leave blank to keep current)</span>}
            </label>
            <input
              id={`key-${provider.provider}`}
              className="cos-input cos-mono"
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={provider.key_hint}
            />
          </div>
          <div>
            <label className="cos-label" htmlFor={`model-${provider.provider}`}>Model</label>
            <input id={`model-${provider.provider}`} className="cos-input cos-mono" value={model} onChange={(e) => setModel(e.target.value)} placeholder={provider.default_model || 'model name'} />
          </div>
          {(isCustom || provider.default_base_url !== null) && (
            <div>
              <label className="cos-label" htmlFor={`url-${provider.provider}`}>
                Base URL {!isCustom && <span className="cos-dim" style={{ fontWeight: 400 }}>(optional override)</span>}
              </label>
              <input id={`url-${provider.provider}`} className="cos-input cos-mono" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder={provider.default_base_url || 'http://localhost:11434/v1'} />
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
            {provider.docs_url ? (
              <a href={provider.docs_url} target="_blank" rel="noreferrer" style={{ color: 'var(--emerald-glow)', fontSize: '0.75rem' }}>
                Get a key ↗
              </a>
            ) : (
              <span />
            )}
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => setOpen(false)}>
                Cancel
              </button>
              <button type="submit" className="cos-btn cos-btn-primary cos-btn-sm" disabled={busy !== null}>
                {busy === 'save' ? 'Saving...' : 'Save key'}
              </button>
            </div>
          </div>
        </form>
      ) : (
        <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.85rem', flexWrap: 'wrap' }}>
          <button type="button" className={`cos-btn cos-btn-sm ${provider.configured ? 'cos-btn-ghost' : 'cos-btn-primary'}`} onClick={() => setOpen(true)}>
            {provider.configured ? 'Update' : 'Add key'}
          </button>
          {provider.configured && (
            <>
              <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={runTest} disabled={busy !== null}>
                {busy === 'test' ? 'Testing...' : 'Test connection'}
              </button>
              <button type="button" className="cos-btn cos-btn-danger cos-btn-sm" onClick={remove} disabled={busy !== null} aria-label={`Remove ${provider.label} key`}>
                <TrashIcon size={13} />
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

const SMTP_PRESETS: Record<string, { host: string; port: number; use_ssl: boolean }> = {
  Gmail: { host: 'smtp.gmail.com', port: 587, use_ssl: false },
  Outlook: { host: 'smtp.office365.com', port: 587, use_ssl: false },
  Zoho: { host: 'smtp.zoho.in', port: 465, use_ssl: true },
}

function EmailSection({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [data, setData] = useState<EmailSettingsResponse | null>(null)
  const [form, setForm] = useState({ host: '', port: 587, username: '', password: '', from_email: '', use_ssl: false })
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState<'save' | 'test' | 'delete' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [test, setTest] = useState<TestResult | null>(null)

  const load = useCallback(() => {
    apiCall<EmailSettingsResponse>('/settings/email')
      .then((res) => {
        setData(res)
        if (res.settings) {
          const s = res.settings
          setForm({ host: s.host, port: s.port, username: s.username, password: '', from_email: s.from_email, use_ssl: s.use_ssl })
        } else {
          setForm((f) => ({ ...f, username: ctx.user.email, from_email: ctx.user.email }))
        }
      })
      .catch((err) => setError(errorMessage(err)))
  }, [ctx.user.email])

  useEffect(load, [load])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy('save')
    setError(null)
    try {
      const res = await apiCall<EmailSettingsResponse>('/settings/email', { method: 'PUT', body: { ...form, port: Number(form.port), password: form.password || null } })
      setData(res)
      setEditing(false)
      setTest(null)
      setForm((f) => ({ ...f, password: '' }))
      ctx.notify('Email account saved')
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
      setTest(await apiCall<TestResult>('/settings/email/test', { method: 'POST' }))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const remove = async () => {
    if (!window.confirm('Disconnect your email account?')) return
    setBusy('delete')
    try {
      setData(await apiCall<EmailSettingsResponse>('/settings/email', { method: 'DELETE' }))
      setTest(null)
      ctx.notify('Email account disconnected')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const s = data?.settings
  const lastTest = test ?? (s?.last_tested_at ? { ok: Boolean(s.last_test_ok), message: s.last_test_message ?? '', tested_at: s.last_tested_at } : null)

  return (
    <>
      <h2 style={{ fontSize: '1rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <MailIcon size={17} /> Email sending (SMTP)
      </h2>
      <div className="cos-card">
        <p className="cos-muted" style={{ fontSize: '0.82rem', lineHeight: 1.55, marginBottom: '0.85rem' }}>
          Approved follow-ups are sent from your own mailbox. For Gmail, turn on 2-step verification and create an{' '}
          <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" style={{ color: 'var(--emerald-glow)' }}>
            app password
          </a>
          . Without SMTP, approved drafts are recorded for you to send manually.
        </p>
        {!data && <Spinner />}
        {data && !editing && (
          <>
            {s ? (
              <div style={{ fontSize: '0.84rem' }}>
                <span className="cos-badge cos-badge-green">Connected</span>{' '}
                <strong style={{ color: '#FFFFFF' }}>{s.from_email}</strong>
                <span className="cos-muted"> via {s.host}:{s.port} · password <span className="cos-mono">{s.masked_password}</span></span>
              </div>
            ) : (
              <div className="cos-muted" style={{ fontSize: '0.84rem' }}>No email account connected.</div>
            )}
            {lastTest && (
              <div className={`cos-alert ${lastTest.ok ? 'cos-alert-info' : 'cos-alert-error'}`} style={{ marginTop: '0.7rem', fontSize: '0.75rem' }}>
                {lastTest.ok ? '✓ ' : '✗ '}
                {lastTest.message}
              </div>
            )}
            <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.85rem' }}>
              <button type="button" className={`cos-btn cos-btn-sm ${s ? 'cos-btn-ghost' : 'cos-btn-primary'}`} onClick={() => setEditing(true)}>
                {s ? 'Update' : 'Connect email'}
              </button>
              {s && (
                <>
                  <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={runTest} disabled={busy !== null}>
                    {busy === 'test' ? 'Testing...' : 'Test login'}
                  </button>
                  <button type="button" className="cos-btn cos-btn-danger cos-btn-sm" onClick={remove} disabled={busy !== null}>
                    Disconnect
                  </button>
                </>
              )}
            </div>
          </>
        )}
        {editing && (
          <form onSubmit={save}>
            <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.85rem', flexWrap: 'wrap' }}>
              {Object.entries(SMTP_PRESETS).map(([name, preset]) => (
                <button key={name} type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => setForm((f) => ({ ...f, ...preset }))}>
                  {name}
                </button>
              ))}
            </div>
            <div className="cos-grid" style={{ gridTemplateColumns: '2fr 1fr', gap: '0.75rem' }}>
              <div>
                <label className="cos-label" htmlFor="smtp-host">SMTP host</label>
                <input id="smtp-host" className="cos-input" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} required />
              </div>
              <div>
                <label className="cos-label" htmlFor="smtp-port">Port</label>
                <input id="smtp-port" className="cos-input" type="number" value={form.port} onChange={(e) => setForm({ ...form, port: Number(e.target.value) })} required />
              </div>
              <div>
                <label className="cos-label" htmlFor="smtp-user">Username</label>
                <input id="smtp-user" className="cos-input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
              </div>
              <div>
                <label className="cos-label" htmlFor="smtp-ssl">Security</label>
                <select id="smtp-ssl" className="cos-select" value={form.use_ssl ? 'ssl' : 'starttls'} onChange={(e) => setForm({ ...form, use_ssl: e.target.value === 'ssl' })}>
                  <option value="starttls">STARTTLS</option>
                  <option value="ssl">SSL/TLS</option>
                </select>
              </div>
              <div>
                <label className="cos-label" htmlFor="smtp-pass">
                  Password / app password {s?.has_password && <span className="cos-dim" style={{ fontWeight: 400 }}>(blank keeps current)</span>}
                </label>
                <input id="smtp-pass" className="cos-input" type="password" autoComplete="off" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </div>
              <div>
                <label className="cos-label" htmlFor="smtp-from">From address</label>
                <input id="smtp-from" className="cos-input" type="email" value={form.from_email} onChange={(e) => setForm({ ...form, from_email: e.target.value })} required />
              </div>
            </div>
            {error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.75rem' }}>{error}</div>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.4rem', marginTop: '0.9rem' }}>
              <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => setEditing(false)}>
                Cancel
              </button>
              <button type="submit" className="cos-btn cos-btn-primary cos-btn-sm" disabled={busy !== null}>
                {busy === 'save' ? 'Saving...' : 'Save'}
              </button>
            </div>
          </form>
        )}
        {!editing && error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.75rem' }}>{error}</div>}
      </div>
    </>
  )
}
