/**
 * In-chat confirmation card for an action the agent prepared (email, WhatsApp,
 * calendar event/reminder, event change or deletion). Confirming calls the same
 * hash-bound approval endpoint as the Approvals page.
 */

import React, { useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { DecisionResponse, Proposal, ProposalStatus } from '../api/types'
import { StatusBadge, VerdictBadge } from './ui'

const KIND_LABELS: Record<string, { icon: string; label: string; confirm: string }> = {
  email: { icon: '✉️', label: 'Email', confirm: 'Confirm & send' },
  whatsapp: { icon: '💬', label: 'WhatsApp', confirm: 'Confirm & send' },
  calendar: { icon: '📅', label: 'Calendar event', confirm: 'Confirm & add' },
  calendar_update: { icon: '✏️', label: 'Change event', confirm: 'Confirm change' },
  calendar_delete: { icon: '🗑️', label: 'Delete event', confirm: 'Confirm delete' },
}

export function formatEventTime(startIso: string, endIso?: string): string {
  const start = new Date(startIso)
  const day = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).format(start)
  const time = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' })
  return endIso ? `${day}, ${time.format(start)} – ${time.format(new Date(endIso))}` : `${day}, ${time.format(start)}`
}

export function kindLabel(kind: string): string {
  return KIND_LABELS[kind]?.label ?? kind
}

export function ActionCard({
  proposal,
  onDecided,
  onOpenApprovals,
}: {
  proposal: Proposal
  onDecided?: (message: string, ok: boolean) => void
  onOpenApprovals?: () => void
}): JSX.Element {
  const [status, setStatus] = useState<ProposalStatus>(proposal.status)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const meta = KIND_LABELS[proposal.kind] ?? { icon: '⚙️', label: proposal.kind, confirm: 'Confirm' }
  const payload = proposal.payload
  const actionable = status === 'pending'
  const longBody = proposal.rendered_body.length > 220

  const decide = async (decision: 'approve' | 'reject') => {
    setBusy(true)
    setError(null)
    try {
      const res = await apiCall<DecisionResponse>(`/approvals/${proposal.ref}/decision`, {
        method: 'POST',
        body: { decision, rendered_hash: proposal.rendered_hash, rejection_reason: decision === 'reject' ? 'Cancelled in chat' : undefined },
      })
      setStatus(res.status)
      setResult(res.message)
      onDecided?.(decision === 'reject' ? 'Cancelled' : res.message, true)
    } catch (err) {
      const message = errorMessage(err)
      setError(message)
      onDecided?.(message, false)
    } finally {
      setBusy(false)
    }
  }

  const recipient =
    proposal.kind === 'calendar'
      ? payload?.attendees && payload.attendees.length > 0
        ? `Invites ${payload.attendees.join(', ')}`
        : 'Only on your calendar'
      : proposal.kind.startsWith('calendar_')
        ? proposal.contact_name
        : `To ${proposal.contact_name}${proposal.contact_email && proposal.contact_email !== proposal.contact_name ? ` · ${proposal.contact_email}` : ''}`

  return (
    <div
      className="cos-card-elevated"
      style={{ marginTop: '0.6rem', padding: '0.85rem 1rem', borderColor: status === 'blocked' ? 'rgba(244, 63, 94, 0.4)' : actionable ? 'var(--border-emerald)' : undefined }}
      data-testid={`action-card-${proposal.ref}`}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
        <span aria-hidden="true">{meta.icon}</span>
        <strong style={{ color: '#FFFFFF', fontSize: '0.84rem' }}>{meta.label}</strong>
        <VerdictBadge verdict={proposal.policy_verdict} />
        <StatusBadge status={status} />
        <span className="cos-dim cos-mono" style={{ fontSize: '0.66rem', marginLeft: 'auto' }}>{proposal.ref}</span>
      </div>
      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{recipient}</div>
      <div style={{ fontSize: '0.86rem', color: '#FFFFFF', fontWeight: 700, marginTop: '0.35rem' }}>{proposal.subject}</div>
      {proposal.kind === 'calendar' && payload?.start_utc && (
        <div style={{ fontSize: '0.8rem', color: 'var(--emerald-glow)', marginTop: '0.2rem' }}>
          📅 {formatEventTime(payload.start_utc, payload.end_utc)}
          {payload.reminder_minutes != null && ` · reminder ${payload.reminder_minutes} min before`}
          {payload.with_meet && ' · Google Meet'}
        </div>
      )}
      <div style={{ fontSize: '0.8rem', lineHeight: 1.55, whiteSpace: 'pre-wrap', color: 'var(--text-main)', marginTop: '0.35rem' }}>
        {longBody && !expanded ? `${proposal.rendered_body.slice(0, 220)}…` : proposal.rendered_body}
      </div>
      {longBody && (
        <button type="button" onClick={() => setExpanded((v) => !v)} style={{ background: 'none', border: 'none', color: 'var(--emerald-glow)', padding: 0, fontSize: '0.74rem', cursor: 'pointer' }}>
          {expanded ? 'Show less' : 'Show full text'}
        </button>
      )}
      {proposal.policy_reasons.length > 0 && (
        <div className={`cos-alert ${proposal.policy_verdict === 'BLOCK' ? 'cos-alert-error' : 'cos-alert-warn'}`} style={{ marginTop: '0.5rem', fontSize: '0.74rem' }}>
          {proposal.policy_reasons.join(' · ')}
        </div>
      )}
      {result && <div className="cos-alert cos-alert-info" style={{ marginTop: '0.5rem', fontSize: '0.75rem' }}>{result}</div>}
      {error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.5rem', fontSize: '0.75rem' }}>{error}</div>}
      <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.6rem', flexWrap: 'wrap' }}>
        {actionable && (
          <>
            <button type="button" className="cos-btn cos-btn-primary cos-btn-sm" onClick={() => decide('approve')} disabled={busy}>
              {busy ? 'Working...' : meta.confirm}
            </button>
            <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => decide('reject')} disabled={busy}>
              Cancel
            </button>
          </>
        )}
        {(actionable || status === 'blocked') && onOpenApprovals && (
          <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={onOpenApprovals}>
            {status === 'blocked' ? 'Edit in Approvals' : 'Edit first'}
          </button>
        )}
      </div>
    </div>
  )
}
