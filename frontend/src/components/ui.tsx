/**
 * Small shared UI building blocks for dashboard views.
 */

import React, { useEffect } from 'react'

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: React.ReactNode
  actions?: React.ReactNode
}): JSX.Element {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
      <div>
        <h1 className="cos-page-title">{title}</h1>
        {subtitle && <div className="cos-page-subtitle">{subtitle}</div>}
      </div>
      {actions && <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>{actions}</div>}
    </div>
  )
}

export function StatCard({ label, value, hint }: { label: string; value: React.ReactNode; hint?: React.ReactNode }): JSX.Element {
  return (
    <div className="cos-card">
      <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div className="cos-mono" style={{ fontSize: '1.45rem', fontWeight: 800, color: '#FFFFFF', marginTop: '0.35rem' }}>
        {value}
      </div>
      {hint && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>{hint}</div>}
    </div>
  )
}

export function Modal({
  title,
  onClose,
  children,
  width = 560,
}: {
  title: string
  onClose: () => void
  children: React.ReactNode
  width?: number
}): JSX.Element {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="cos-modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="cos-modal" role="dialog" aria-modal="true" aria-label={title} style={{ maxWidth: `${width}px` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.1rem' }}>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#FFFFFF' }}>{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '1.3rem', cursor: 'pointer', lineHeight: 1 }}>
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function EmptyPanel({ title, text, action }: { title: string; text: React.ReactNode; action?: React.ReactNode }): JSX.Element {
  return (
    <div className="cos-card" style={{ textAlign: 'center', padding: '2.5rem 1.5rem' }}>
      <div style={{ fontSize: '0.98rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '0.4rem' }}>{title}</div>
      <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', maxWidth: '460px', margin: '0 auto', lineHeight: 1.55 }}>{text}</div>
      {action && <div style={{ marginTop: '1.1rem' }}>{action}</div>}
    </div>
  )
}

export function Spinner({ label = 'Loading...' }: { label?: string }): JSX.Element {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--text-muted)', fontSize: '0.82rem', padding: '1rem 0' }}>
      <span
        style={{
          width: '14px',
          height: '14px',
          border: '2px solid var(--border-subtle)',
          borderTopColor: 'var(--emerald-glow)',
          borderRadius: '50%',
          display: 'inline-block',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      {label}
    </div>
  )
}

const VERDICT_CLASS: Record<string, string> = {
  ALLOW: 'cos-badge-green',
  ASK: 'cos-badge-amber',
  BLOCK: 'cos-badge-red',
}

export function VerdictBadge({ verdict }: { verdict: string }): JSX.Element {
  return <span className={`cos-badge ${VERDICT_CLASS[verdict] || ''}`}>{verdict}</span>
}

const STATUS_CLASS: Record<string, string> = {
  ready: 'cos-badge-green',
  sent: 'cos-badge-green',
  booked: 'cos-badge-green',
  approved: 'cos-badge-green',
  pending: 'cos-badge-amber',
  degraded: 'cos-badge-amber',
  approved_manual: 'cos-badge-amber',
  blocked: 'cos-badge-red',
  failed: 'cos-badge-red',
  unavailable: 'cos-badge-red',
  rejected: '',
  expired: '',
  not_configured: '',
}

export function StatusBadge({ status }: { status: string }): JSX.Element {
  return <span className={`cos-badge ${STATUS_CLASS[status] ?? ''}`}>{status.replace(/_/g, ' ')}</span>
}

// ---------------------------------------------------------------------------
// Minimal, safe Markdown rendering (no HTML injection): paragraphs, bullet and
// numbered lists, headings, **bold**, *italic* and `code`.
// ---------------------------------------------------------------------------
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*|_[^_\s][^_]*_)/g
  let last = 0
  let match: RegExpExecArray | null
  let i = 0
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index))
    const token = match[0]
    const key = `${keyPrefix}-${i++}`
    if (token.startsWith('**')) nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>)
    else if (token.startsWith('`')) nodes.push(<code key={key}>{token.slice(1, -1)}</code>)
    else nodes.push(<em key={key}>{token.slice(1, -1)}</em>)
    last = match.index + token.length
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}

export function Markdown({ text }: { text: string }): JSX.Element {
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  const blocks: React.ReactNode[] = []
  let list: { ordered: boolean; items: string[] } | null = null
  let paragraph: string[] = []

  const flushParagraph = () => {
    if (paragraph.length) {
      const k = `p${blocks.length}`
      blocks.push(
        <p key={k}>
          {paragraph.map((line, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <br />}
              {renderInline(line, `${k}-${idx}`)}
            </React.Fragment>
          ))}
        </p>
      )
      paragraph = []
    }
  }
  const flushList = () => {
    if (list) {
      const k = `l${blocks.length}`
      const items = list.items.map((item, idx) => <li key={idx}>{renderInline(item, `${k}-${idx}`)}</li>)
      blocks.push(list.ordered ? <ol key={k}>{items}</ol> : <ul key={k}>{items}</ul>)
      list = null
    }
  }

  for (const raw of lines) {
    const line = raw.trimEnd()
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/)
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/)
    const heading = line.match(/^#{1,6}\s+(.*)$/)
    if (bullet || numbered) {
      flushParagraph()
      const ordered = Boolean(numbered)
      if (!list || list.ordered !== ordered) {
        flushList()
        list = { ordered, items: [] }
      }
      list.items.push((bullet ?? numbered)![1])
    } else if (heading) {
      flushParagraph()
      flushList()
      blocks.push(<h3 key={`h${blocks.length}`}>{renderInline(heading[1], `h${blocks.length}`)}</h3>)
    } else if (line.trim() === '') {
      flushParagraph()
      flushList()
    } else {
      flushList()
      paragraph.push(line)
    }
  }
  flushParagraph()
  flushList()
  return <div className="cos-md">{blocks}</div>
}
