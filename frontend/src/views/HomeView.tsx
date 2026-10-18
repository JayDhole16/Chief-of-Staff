/**
 * Overview: onboarding checklist, live pipeline metrics, quiet deals and recent activity.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { Brief, EmailSettingsResponse, SweepResponse } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { EmptyPanel, PageHeader, Spinner, StatCard } from '../components/ui'
import { QuickKeySetup } from '../components/QuickKeySetup'
import { formatRupees, STAGE_LABELS, timeAgo } from '../utils/formatters'

export function HomeView({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [brief, setBrief] = useState<Brief | null>(null)
  const [emailConfigured, setEmailConfigured] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sweeping, setSweeping] = useState(false)

  const load = useCallback(() => {
    setError(null)
    Promise.all([apiCall<Brief>('/brief'), apiCall<EmailSettingsResponse>('/settings/email')])
      .then(([b, email]) => {
        setBrief(b)
        setEmailConfigured(email.configured)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  useEffect(load, [load])

  const runSweep = async () => {
    setSweeping(true)
    try {
      const res = await apiCall<SweepResponse>('/sweep', { method: 'POST' })
      ctx.notify(
        res.drafted.length
          ? `Drafted ${res.drafted.length} follow-up(s). Review them in Approvals.`
          : `No drafts needed: ${res.skipped.length} skipped, nothing quiet for ${res.threshold_days}+ days.`
      )
      ctx.refreshApprovals()
      load()
    } catch (err) {
      ctx.notify(errorMessage(err), 'error')
    } finally {
      setSweeping(false)
    }
  }

  const firstName = ctx.user.name.split(' ')[0]
  const steps = brief
    ? [
        { done: brief.deal_count > 0, label: 'Add your first deal', action: () => ctx.navigate('deals') },
        { done: emailConfigured, label: 'Connect your email (SMTP) to send approved follow-ups', action: () => ctx.navigate('keys') },
      ]
    : []
  const setupDone = steps.every((s) => s.done)

  return (
    <div className="cos-page">
      <div className="cos-page-inner">
        <PageHeader
          title={`Hello, ${firstName}`}
          subtitle={ctx.user.business_name ? `${ctx.user.business_name} · founder workspace` : 'Your founder workspace'}
          actions={
            <>
              <button type="button" className="cos-btn cos-btn-ghost" onClick={() => ctx.navigate('chat')}>
                Ask Chief of Staff
              </button>
              <button type="button" className="cos-btn cos-btn-primary" onClick={runSweep} disabled={sweeping || !brief?.deal_count}>
                {sweeping ? 'Sweeping...' : 'Run quiet-deal sweep'}
              </button>
            </>
          }
        />

        {error && <div className="cos-alert cos-alert-error" style={{ marginBottom: '1rem' }}>{error}</div>}
        {!brief && !error && <Spinner />}

        {brief && (
          <>
            <QuickKeySetup ctx={ctx} />

            {!setupDone && (
              <div className="cos-card-elevated" style={{ marginBottom: '1.25rem' }}>
                <div style={{ fontWeight: 700, color: '#FFFFFF', marginBottom: '0.75rem' }}>Get set up</div>
                <div style={{ display: 'grid', gap: '0.5rem' }}>
                  {steps.map((s) => (
                    <button
                      key={s.label}
                      type="button"
                      onClick={s.action}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.7rem',
                        background: 'none',
                        border: 'none',
                        padding: '0.35rem 0',
                        color: s.done ? 'var(--text-dim)' : 'var(--text-main)',
                        textDecoration: s.done ? 'line-through' : 'none',
                        cursor: 'pointer',
                        fontSize: '0.86rem',
                        textAlign: 'left',
                        fontFamily: 'inherit',
                      }}
                    >
                      <span
                        style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          border: `1px solid ${s.done ? 'var(--emerald-glow)' : 'var(--border-subtle)'}`,
                          backgroundColor: s.done ? 'var(--emerald-tint)' : 'transparent',
                          color: 'var(--emerald-glow)',
                          fontSize: '0.7rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        {s.done ? '✓' : ''}
                      </span>
                      {s.label}
                      {!s.done && <span style={{ color: 'var(--emerald-glow)', marginLeft: 'auto', fontSize: '0.78rem' }}>Set up →</span>}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="cos-grid cos-grid-4" style={{ marginBottom: '1.25rem' }}>
              <StatCard label="Open pipeline" value={formatRupees(brief.open_pipeline_inr)} hint={`${brief.deal_count} deal(s) total`} />
              <StatCard label="Won" value={formatRupees(brief.won_inr)} hint={`${brief.stage_counts.won ?? 0} deal(s)`} />
              <StatCard label="Pending approvals" value={brief.pending_approvals} hint={<button type="button" onClick={() => ctx.navigate('approvals')} style={{ background: 'none', border: 'none', color: 'var(--emerald-glow)', padding: 0, cursor: 'pointer', fontSize: 'inherit' }}>Review →</button>} />
              <StatCard label="Emails sent" value={brief.emails_sent} hint="via your SMTP account" />
            </div>

            <div className="cos-grid cos-grid-2">
              <div className="cos-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
                  <div style={{ fontWeight: 700, color: '#FFFFFF' }}>Going quiet</div>
                  <span className="cos-dim" style={{ fontSize: '0.75rem' }}>no contact for {ctx.user.quiet_days_threshold}+ days</span>
                </div>
                {brief.quiet_deals.length === 0 ? (
                  <div className="cos-muted" style={{ fontSize: '0.84rem' }}>
                    {brief.deal_count === 0 ? 'Add deals to start tracking follow-ups.' : 'Nothing is going quiet. Nice work.'}
                  </div>
                ) : (
                  <div style={{ display: 'grid', gap: '0.5rem' }}>
                    {brief.quiet_deals.map((d) => (
                      <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.84rem' }}>
                        <span>
                          <strong style={{ color: '#FFFFFF' }}>{d.company}</strong> <span className="cos-muted">· {d.contact_name}</span>
                        </span>
                        <span className="cos-badge cos-badge-amber">{d.days_quiet}d quiet</span>
                      </div>
                    ))}
                  </div>
                )}
                {Object.keys(brief.stage_counts).length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '1rem', paddingTop: '0.8rem', borderTop: '1px solid var(--border-hairline)' }}>
                    {Object.entries(brief.stage_counts).map(([stage, count]) => (
                      <span key={stage} className="cos-badge">
                        {STAGE_LABELS[stage] ?? stage}: {count}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="cos-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
                  <div style={{ fontWeight: 700, color: '#FFFFFF' }}>Recent activity</div>
                  <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => ctx.navigate('activity')}>
                    View all
                  </button>
                </div>
                {brief.recent_activity.length === 0 ? (
                  <div className="cos-muted" style={{ fontSize: '0.84rem' }}>No activity yet.</div>
                ) : (
                  <div style={{ display: 'grid', gap: '0.65rem' }}>
                    {brief.recent_activity.map((e) => (
                      <div key={e.id} style={{ fontSize: '0.82rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
                          <span style={{ color: '#FFFFFF', fontWeight: 600 }}>{e.title}</span>
                          <span className="cos-dim" style={{ flexShrink: 0 }}>{timeAgo(e.created_at)}</span>
                        </div>
                        {e.description && <div className="cos-muted">{e.description}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {brief.deal_count === 0 && (
              <div style={{ marginTop: '1.25rem' }}>
                <EmptyPanel
                  title="Your workspace is empty"
                  text="Add the deals you're working on. Chief of Staff tracks when each contact last heard from you and drafts grounded follow-ups for you to approve."
                  action={
                    <button type="button" className="cos-btn cos-btn-primary" onClick={() => ctx.navigate('deals')}>
                      Add a deal
                    </button>
                  }
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
