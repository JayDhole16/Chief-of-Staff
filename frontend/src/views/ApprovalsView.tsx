/**
 * Approvals: review hash-bound drafts, edit them (re-hashed and re-checked), approve or reject.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { ApprovalsResponse, DecisionResponse, Proposal } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { CopyIcon } from '../components/Icons'
import { EmptyPanel, PageHeader, Spinner, StatusBadge, VerdictBadge } from '../components/ui'
import { formatDateTime, timeAgo } from '../utils/formatters'

type Tab = 'pending' | 'blocked' | 'all'

export function ApprovalsView({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [tab, setTab] = useState<Tab>('pending')
  const [items, setItems] = useState<Proposal[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setError(null)
    apiCall<ApprovalsResponse>(`/approvals?status=${tab}`)
      .then((res) => setItems(res.approvals))
      .catch((err) => setError(errorMessage(err)))
  }, [tab])

  useEffect(() => {
    setItems(null)
    load()
  }, [load])

  return (
    <div className="cos-page">
      <div className="cos-page-inner" style={{ maxWidth: '900px' }}>
        <PageHeader
          title="Approvals"
          subtitle="Each draft is bound to a SHA-256 hash of its exact text. Approving sends that exact text and nothing else."
        />
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          {(['pending', 'blocked', 'all'] as Tab[]).map((t) => (
            <button key={t} type="button" className={`cos-btn cos-btn-sm ${tab === t ? 'cos-btn-primary' : 'cos-btn-ghost'}`} onClick={() => setTab(t)}>
              {t === 'pending' ? 'Pending' : t === 'blocked' ? 'Blocked by guards' : 'History'}
            </button>
          ))}
        </div>

        {error && <div className="cos-alert cos-alert-error">{error}</div>}
        {!items && !error && <Spinner />}
        {items && items.length === 0 && (
          <EmptyPanel
            title={tab === 'pending' ? 'Nothing waiting for you' : tab === 'blocked' ? 'No blocked drafts' : 'No drafts yet'}
            text="Use “Draft follow-up” on a deal, or run the quiet-deal sweep, to create drafts for review."
            action={
              <button type="button" className="cos-btn cos-btn-primary" onClick={() => ctx.navigate('deals')}>
                Go to deals
              </button>
            }
          />
        )}
        <div style={{ display: 'grid', gap: '1rem' }}>
          {items?.map((p) => <ProposalCard key={p.ref} proposal={p} ctx={ctx} />)}
        </div>
      </div>
    </div>
  )
}

function formatMeetingTime(startIso: string, endIso: string): string {
  const start = new Date(startIso)
  const end = new Date(endIso)
  const day = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).format(start)
  const time = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' })
  return `${day}, ${time.format(start)} – ${time.format(end)}`
}

function ProposalCard({ proposal, ctx }: { proposal: Proposal; ctx: DashboardContext }): JSX.Element {
  const [current, setCurrent] = useState(proposal)
  const [editing, setEditing] = useState(false)
  const [subject, setSubject] = useState(proposal.subject)
  const [body, setBody] = useState(proposal.rendered_body)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<DecisionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const actionable = current.status === 'pending' || current.status === 'blocked'
  const isMeeting = current.kind === 'calendar'
  const meeting = isMeeting ? current.payload : null

  useEffect(() => {
    setCurrent(proposal)
    setSubject(proposal.subject)
    setBody(proposal.rendered_body)
  }, [proposal])

  const saveEdit = async () => {
    setBusy(true)
    setError(null)
    try {
      const updated = await apiCall<Proposal>(`/approvals/${current.ref}`, { method: 'PUT', body: { subject, body } })
      setCurrent(updated)
      setEditing(false)
      ctx.notify(updated.status === 'blocked' ? 'Saved, but the guards still block this draft' : 'Draft updated and re-checked', updated.status === 'blocked' ? 'error' : 'ok')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const decide = async (decision: 'approve' | 'reject') => {
    let rejection_reason: string | undefined
    if (decision === 'reject') {
      const reason = window.prompt('Reason for rejecting (optional):', '')
      if (reason === null) return
      rejection_reason = reason || undefined
    }
    setBusy(true)
    setError(null)
    try {
      const res = await apiCall<DecisionResponse>(`/approvals/${current.ref}/decision`, {
        method: 'POST',
        body: { decision, rendered_hash: current.rendered_hash, rejection_reason },
      })
      setResult(res)
      setCurrent({ ...current, status: res.status })
      const messages: Record<string, string> = {
        sent: `Email sent to ${current.contact_name}`,
        booked: `Meeting booked with ${current.contact_name}. Invite sent.`,
        approved: 'Approved. Copy the draft and send it yourself.',
        rejected: isMeeting ? 'Meeting proposal rejected' : 'Draft rejected',
      }
      ctx.notify(messages[res.status] ?? res.message)
      ctx.refreshApprovals()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const copyDraft = async () => {
    try {
      await navigator.clipboard.writeText(`Subject: ${current.subject}\n\n${current.rendered_body}`)
      ctx.notify('Draft copied to clipboard')
    } catch {
      ctx.notify('Could not access the clipboard', 'error')
    }
  }

  return (
    <div className="cos-card" style={{ borderColor: current.status === 'blocked' ? 'rgba(244, 63, 94, 0.35)' : undefined }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            {isMeeting && <span className="cos-badge cos-badge-green">Meeting</span>}
            <span style={{ fontWeight: 800, color: '#FFFFFF' }}>{isMeeting ? 'With' : 'To'} {current.contact_name}</span>
            <span className="cos-muted" style={{ fontSize: '0.8rem' }}>&lt;{current.contact_email}&gt;</span>
            <VerdictBadge verdict={current.policy_verdict} />
            <StatusBadge status={current.status} />
          </div>
          <div className="cos-dim" style={{ fontSize: '0.75rem', marginTop: '0.2rem' }}>
            {current.deal_title} · <span className="cos-mono">{current.ref}</span> · drafted {timeAgo(current.created_at)}
            {actionable && ` · expires ${formatDateTime(current.expires_at)}`}
          </div>
        </div>
      </div>

      {editing ? (
        <div style={{ display: 'grid', gap: '0.6rem' }}>
          <input className="cos-input" value={subject} onChange={(e) => setSubject(e.target.value)} aria-label="Subject" />
          <textarea className="cos-textarea" value={body} onChange={(e) => setBody(e.target.value)} rows={12} aria-label="Email body" />
        </div>
      ) : (
        <div style={{ backgroundColor: 'var(--bg-console)', border: '1px solid var(--border-hairline)', borderRadius: '10px', padding: '0.9rem 1rem' }}>
          <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '0.6rem' }}>
            {isMeeting ? current.subject : `Subject: ${current.subject}`}
          </div>
          {meeting && (
            <div style={{ fontSize: '0.82rem', color: 'var(--emerald-glow)', marginBottom: '0.6rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <span>📅 {formatMeetingTime(meeting.start_utc, meeting.end_utc)}</span>
              <span className="cos-muted">{meeting.duration_minutes} min · {meeting.with_meet ? 'Google Meet' : 'no video link'} · organizer {meeting.organizer}</span>
            </div>
          )}
          <div style={{ fontSize: '0.84rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', color: 'var(--text-main)' }}>{current.rendered_body}</div>
        </div>
      )}

      {current.policy_reasons.length > 0 && (
        <div className={`cos-alert ${current.policy_verdict === 'BLOCK' ? 'cos-alert-error' : 'cos-alert-warn'}`} style={{ marginTop: '0.75rem' }}>
          <strong>Guard findings:</strong>
          <ul style={{ margin: '0.3rem 0 0 1.1rem' }}>
            {current.policy_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.75rem' }}>
        {current.facts_used.map((f) => (
          <span key={f.label} className="cos-badge" title={f.source}>
            {f.label}: {f.value}
          </span>
        ))}
        <span className="cos-badge cos-mono" title={current.rendered_hash}>
          sha256 {current.rendered_hash.slice(0, 12)}…
        </span>
      </div>

      {result?.receipt && (
        <div className={`cos-alert ${result.receipt.status === 'sent' ? 'cos-alert-info' : 'cos-alert-warn'}`} style={{ marginTop: '0.75rem' }}>
          <strong>Receipt {result.receipt.receipt_id}:</strong> {result.message}
        </div>
      )}
      {error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.75rem' }}>{error}</div>}

      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '0.9rem', flexWrap: 'wrap' }}>
        <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={copyDraft}>
          <CopyIcon size={13} /> Copy
        </button>
        {actionable && !editing && (
          <>
            <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => setEditing(true)} disabled={busy}>
              Edit
            </button>
            <button type="button" className="cos-btn cos-btn-danger cos-btn-sm" onClick={() => decide('reject')} disabled={busy}>
              Reject
            </button>
            <button type="button" className="cos-btn cos-btn-primary cos-btn-sm" onClick={() => decide('approve')} disabled={busy || current.status === 'blocked'} title={current.status === 'blocked' ? 'Edit the draft to clear the blocking guards' : isMeeting ? 'Create the event and send the invite' : 'Approve and send this exact text'}>
              {busy ? 'Working...' : isMeeting ? 'Approve & book' : 'Approve & send'}
            </button>
          </>
        )}
        {editing && (
          <>
            <button
              type="button"
              className="cos-btn cos-btn-ghost cos-btn-sm"
              onClick={() => {
                setEditing(false)
                setSubject(current.subject)
                setBody(current.rendered_body)
              }}
              disabled={busy}
            >
              Cancel
            </button>
            <button type="button" className="cos-btn cos-btn-primary cos-btn-sm" onClick={saveEdit} disabled={busy || !subject.trim() || !body.trim()}>
              {busy ? 'Saving...' : 'Save & re-check'}
            </button>
          </>
        )}
        {!actionable && result === null && current.status !== 'pending' && (
          <span className="cos-dim" style={{ fontSize: '0.75rem', alignSelf: 'center' }}>
            {current.decided_at ? `Decided ${timeAgo(current.decided_at)}` : ''}
          </span>
        )}
      </div>
    </div>
  )
}
