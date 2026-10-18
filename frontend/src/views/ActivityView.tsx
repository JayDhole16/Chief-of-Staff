/**
 * Activity log with receipt drill-down.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { ActivityResponse, Receipt } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { EmptyPanel, Modal, PageHeader, Spinner, StatusBadge } from '../components/ui'
import { formatDateTime } from '../utils/formatters'

const TYPE_COLORS: Record<string, string> = {
  sent: 'var(--emerald-glow)',
  approved: 'var(--emerald-primary)',
  proposed: '#FCD34D',
  blocked: '#FB7185',
  failed: '#FB7185',
  rejected: '#94A3B8',
  kill_switch: '#FCD34D',
}

export function ActivityView({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [data, setData] = useState<ActivityResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [receipt, setReceipt] = useState<Receipt | null>(null)

  const load = useCallback(() => {
    apiCall<ActivityResponse>('/activity?limit=200')
      .then(setData)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  useEffect(load, [load])

  const openReceipt = async (id: string) => {
    try {
      setReceipt(await apiCall<Receipt>(`/receipts/${id}`))
    } catch (err) {
      ctx.notify(errorMessage(err), 'error')
    }
  }

  return (
    <div className="cos-page">
      <div className="cos-page-inner" style={{ maxWidth: '860px' }}>
        <PageHeader
          title="Activity"
          subtitle="Everything that happened in your workspace, newest first."
          actions={
            <button type="button" className="cos-btn cos-btn-ghost" onClick={load}>
              Refresh
            </button>
          }
        />
        {error && <div className="cos-alert cos-alert-error">{error}</div>}
        {!data && !error && <Spinner />}
        {data && data.events.length === 0 && <EmptyPanel title="No activity yet" text="Deals, drafts, approvals and sends will appear here." />}
        {data && data.events.length > 0 && (
          <div className="cos-card" style={{ padding: '0.5rem 1.25rem' }}>
            {data.events.map((e, i) => (
              <div key={e.id} style={{ display: 'flex', gap: '0.9rem', padding: '0.85rem 0', borderBottom: i === data.events.length - 1 ? 'none' : '1px solid var(--border-hairline)' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', marginTop: '0.4rem', flexShrink: 0, backgroundColor: TYPE_COLORS[e.type] ?? 'var(--text-dim)' }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
                    <span style={{ fontSize: '0.86rem', fontWeight: 600, color: '#FFFFFF' }}>{e.title}</span>
                    <span className="cos-dim" style={{ fontSize: '0.72rem', flexShrink: 0 }}>{formatDateTime(e.created_at)}</span>
                  </div>
                  {e.description && <div className="cos-muted" style={{ fontSize: '0.8rem', marginTop: '0.15rem' }}>{e.description}</div>}
                  {e.receipt_id && (
                    <button type="button" onClick={() => openReceipt(e.receipt_id!)} style={{ background: 'none', border: 'none', color: 'var(--emerald-glow)', padding: 0, marginTop: '0.3rem', fontSize: '0.75rem', cursor: 'pointer' }}>
                      View receipt →
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {receipt && (
        <Modal title={`Receipt ${receipt.receipt_id}`} onClose={() => setReceipt(null)}>
          <div style={{ display: 'grid', gap: '0.55rem', fontSize: '0.84rem' }}>
            <div>
              Status: <StatusBadge status={receipt.status} />
            </div>
            <div>To: <strong style={{ color: '#FFFFFF' }}>{receipt.recipient_email}</strong></div>
            <div>Subject: {receipt.subject}</div>
            <div className="cos-muted">{receipt.detail}</div>
            {receipt.external_id && <div className="cos-mono cos-dim" style={{ fontSize: '0.75rem' }}>Message-ID {receipt.external_id}</div>}
            <div className="cos-mono cos-dim" style={{ fontSize: '0.72rem', wordBreak: 'break-all' }}>sha256 {receipt.rendered_hash}</div>
            <div style={{ marginTop: '0.4rem' }}>
              <div className="cos-label">Timeline</div>
              {receipt.timeline.map((t, i) => (
                <div key={i} style={{ fontSize: '0.8rem', display: 'flex', gap: '0.6rem' }}>
                  <span className="cos-dim" style={{ flexShrink: 0 }}>{formatDateTime(t.timestamp)}</span>
                  <span>{t.event}</span>
                </div>
              ))}
            </div>
            <div className="cos-dim" style={{ fontSize: '0.72rem' }}>Guards checked: {receipt.guards_checked.join(', ') || 'none'}</div>
          </div>
        </Modal>
      )}
    </div>
  )
}
