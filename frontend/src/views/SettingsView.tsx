/**
 * Settings: founder profile, autonomy guardrails, kill switch and system status.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { OpsStatus, ProfileUpdate, User } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { ShieldIcon } from '../components/Icons'
import { PageHeader, Spinner, StatusBadge } from '../components/ui'
import { formatDateTime } from '../utils/formatters'

export function SettingsView({ ctx, onLogout }: { ctx: DashboardContext; onLogout: () => void }): JSX.Element {
  const { user } = ctx
  const [form, setForm] = useState<Required<ProfileUpdate>>({
    name: user.name,
    role: user.role,
    business_name: user.business_name,
    timezone: user.timezone,
    signature: user.signature,
    working_hours: user.working_hours,
    max_discount_pct: user.max_discount_pct,
    quiet_days_threshold: user.quiet_days_threshold,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ops, setOps] = useState<OpsStatus | null>(null)
  const [killBusy, setKillBusy] = useState(false)

  const loadOps = useCallback(() => {
    apiCall<OpsStatus>('/v1/ops/status')
      .then(setOps)
      .catch(() => undefined)
  }, [])

  useEffect(loadOps, [loadOps])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const updated = await apiCall<User>('/profile', {
        method: 'PUT',
        body: { ...form, max_discount_pct: Number(form.max_discount_pct), quiet_days_threshold: Number(form.quiet_days_threshold) },
      })
      ctx.onUserChange(updated)
      ctx.notify('Settings saved')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const toggleKill = async () => {
    const activating = !user.kill_switch_active
    let reason: string | undefined
    if (activating) {
      const r = window.prompt('Why are you pausing all drafting and sending? (optional)', '')
      if (r === null) return
      reason = r || undefined
    }
    setKillBusy(true)
    try {
      await apiCall('/settings/kill-switch', { method: 'POST', body: { active: activating, reason } })
      ctx.onUserChange(await apiCall<User>('/profile'))
      ctx.notify(activating ? 'Kill switch engaged. All drafting and sending paused.' : 'Kill switch released')
      loadOps()
    } catch (err) {
      ctx.notify(errorMessage(err), 'error')
    } finally {
      setKillBusy(false)
    }
  }

  const field = (key: keyof ProfileUpdate, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <div>
      <label className="cos-label" htmlFor={`profile-${key}`}>{label}</label>
      <input
        id={`profile-${key}`}
        className="cos-input"
        value={form[key] as string | number}
        onChange={(e) => setForm({ ...form, [key]: props.type === 'number' ? Number(e.target.value) : e.target.value })}
        {...props}
      />
    </div>
  )

  return (
    <div className="cos-page">
      <div className="cos-page-inner" style={{ maxWidth: '900px' }}>
        <PageHeader
          title="Settings"
          subtitle={`Signed in as ${user.email}`}
          actions={
            <button type="button" className="cos-btn cos-btn-ghost" onClick={onLogout}>
              Sign out
            </button>
          }
        />

        <form onSubmit={save}>
          <div className="cos-card" style={{ marginBottom: '1.25rem' }}>
            <div style={{ fontWeight: 800, color: '#FFFFFF', marginBottom: '0.9rem' }}>Profile</div>
            <div className="cos-grid cos-grid-2" style={{ gap: '0.85rem' }}>
              {field('name', 'Full name', { required: true })}
              {field('role', 'Role')}
              {field('business_name', 'Company')}
              {field('timezone', 'Timezone', { placeholder: 'Asia/Kolkata' })}
              {field('working_hours', 'Working hours')}
              {field('signature', 'Email signature', { placeholder: 'Name · Title · Company' })}
            </div>
          </div>

          <div className="cos-card" style={{ marginBottom: '1.25rem' }}>
            <div style={{ fontWeight: 800, color: '#FFFFFF', marginBottom: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldIcon size={17} /> Guardrails
            </div>
            <div className="cos-muted" style={{ fontSize: '0.8rem', marginBottom: '0.9rem' }}>
              Drafts that offer a bigger discount than this are flagged for review (guard G10). Deals with no contact for the threshold are treated as quiet.
            </div>
            <div className="cos-grid cos-grid-2" style={{ gap: '0.85rem' }}>
              {field('max_discount_pct', 'Max discount without review (%)', { type: 'number', min: 0, max: 100 })}
              {field('quiet_days_threshold', 'Quiet-deal threshold (days)', { type: 'number', min: 1, max: 90 })}
            </div>
          </div>

          {error && <div className="cos-alert cos-alert-error" style={{ marginBottom: '1rem' }}>{error}</div>}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1.5rem' }}>
            <button type="submit" className="cos-btn cos-btn-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save settings'}
            </button>
          </div>
        </form>

        <div className="cos-card" style={{ marginBottom: '1.25rem', borderColor: user.kill_switch_active ? 'rgba(252, 211, 77, 0.4)' : undefined }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontWeight: 800, color: '#FFFFFF' }}>Emergency kill switch</div>
              <div className="cos-muted" style={{ fontSize: '0.8rem', marginTop: '0.2rem' }}>
                {user.kill_switch_active
                  ? `Engaged${user.kill_switch_reason ? `: ${user.kill_switch_reason}` : ''}. No drafts or emails can be created or sent.`
                  : 'Instantly pause all AI drafting, sweeps and sending.'}
              </div>
            </div>
            <button type="button" className={`cos-btn ${user.kill_switch_active ? 'cos-btn-primary' : 'cos-btn-danger'}`} onClick={toggleKill} disabled={killBusy}>
              {killBusy ? 'Working...' : user.kill_switch_active ? 'Release kill switch' : 'Engage kill switch'}
            </button>
          </div>
        </div>

        <div className="cos-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
            <div style={{ fontWeight: 800, color: '#FFFFFF' }}>System status</div>
            <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={loadOps}>
              Refresh
            </button>
          </div>
          {!ops ? (
            <Spinner />
          ) : (
            <>
              <div style={{ display: 'grid', gap: '0.6rem' }}>
                {Object.entries(ops.components).map(([name, c]) => (
                  <div key={name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', fontSize: '0.82rem' }}>
                    <div>
                      <div style={{ color: '#FFFFFF', fontWeight: 600, textTransform: 'capitalize' }}>{name.replace(/_/g, ' ')}</div>
                      <div className="cos-muted" style={{ fontSize: '0.76rem' }}>{c.detail}</div>
                    </div>
                    <StatusBadge status={c.status} />
                  </div>
                ))}
              </div>
              <div className="cos-dim" style={{ fontSize: '0.7rem', marginTop: '0.8rem' }}>Checked {formatDateTime(ops.checked_at)}</div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
