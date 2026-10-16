import React, { useState, useEffect } from 'react'
import type { FounderBrief, BriefItem } from '../api/types'
import { apiCall } from '../api/client'

export function FounderBriefView(): JSX.Element {
  const [brief, setBrief] = useState<FounderBrief | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false)
  const [showFullNarration, setShowFullNarration] = useState<boolean>(false)

  const fetchBrief = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await apiCall<FounderBrief>('/brief')
      setBrief(data)
    } catch (err) {
      setError((err as Error).message || 'Failed to generate founder brief')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchBrief()
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }
    }
  }, [])

  const handleToggleSpeech = () => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      alert('Speech synthesis is not supported on this device. The deterministic narration text is displayed below.')
      setShowFullNarration(true)
      return
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
      return
    }

    if (!brief?.narration_text) return

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(brief.narration_text)
    utterance.rate = 1.0
    utterance.pitch = 1.0
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    window.speechSynthesis.speak(utterance)
    setIsSpeaking(true)
  }

  if (isLoading) {
    return (
      <div style={{ padding: '1rem', textAlign: 'center', color: '#6b7280' }}>
        <div style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>🎙️</div>
        <div>Generating verified founder brief...</div>
      </div>
    )
  }

  if (error || !brief) {
    return (
      <div
        style={{
          padding: '1rem',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '0.5rem',
          color: '#991b1b',
          fontSize: '0.875rem',
        }}
      >
        <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Brief Unavailable</div>
        <div>{error || 'Unable to load founder brief'}</div>
        <button
          onClick={fetchBrief}
          style={{
            marginTop: '0.75rem',
            padding: '0.375rem 0.75rem',
            backgroundColor: '#dc2626',
            color: 'white',
            border: 'none',
            borderRadius: '0.25rem',
            cursor: 'pointer',
            fontSize: '0.75rem',
            fontWeight: 600,
          }}
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header card */}
      <div
        style={{
          padding: '1rem',
          backgroundColor: '#1e293b',
          color: 'white',
          borderRadius: '0.75rem',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>🎙️</span>
            <span style={{ fontWeight: 700, fontSize: '0.9375rem' }}>Founder Morning Standup</span>
          </div>
          <span
            style={{
              fontSize: '0.65rem',
              padding: '0.15rem 0.4rem',
              backgroundColor: '#334155',
              borderRadius: '0.25rem',
              color: '#94a3b8',
              fontFamily: 'monospace',
            }}
          >
            {brief.workspace_id}
          </span>
        </div>

        <div style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#f8fafc', lineHeight: 1.4 }}>
          {brief.headline}
        </div>

        {/* Audio Narration Bar */}
        <div
          style={{
            marginTop: '0.875rem',
            padding: '0.625rem',
            backgroundColor: '#0f172a',
            borderRadius: '0.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.5rem',
          }}
        >
          <button
            onClick={handleToggleSpeech}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              backgroundColor: isSpeaking ? '#ef4444' : '#3b82f6',
              color: 'white',
              border: 'none',
              padding: '0.375rem 0.75rem',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.75rem',
            }}
          >
            <span>{isSpeaking ? '⏹ Stop' : '🔊 Listen'}</span>
          </button>

          <button
            onClick={() => setShowFullNarration(!showFullNarration)}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: '0.7rem',
              textDecoration: 'underline',
            }}
          >
            {showFullNarration ? 'Hide script' : 'Read script'}
          </button>
        </div>

        {showFullNarration && (
          <div
            style={{
              marginTop: '0.75rem',
              padding: '0.625rem',
              backgroundColor: '#0f172a',
              borderRadius: '0.375rem',
              fontSize: '0.75rem',
              color: '#cbd5e1',
              lineHeight: 1.5,
              borderLeft: '2px solid #3b82f6',
            }}
          >
            <div style={{ fontSize: '0.65rem', color: '#64748b', fontWeight: 700, marginBottom: '0.25rem' }}>
              DETERMINISTIC NARRATION SCRIPT
            </div>
            {brief.narration_text}
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
        <div
          style={{
            padding: '0.75rem 0.5rem',
            backgroundColor: 'white',
            borderRadius: '0.5rem',
            border: '1px solid #e2e8f0',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#059669' }}>
            {brief.metrics.actions_executed_count}
          </div>
          <div style={{ fontSize: '0.65rem', color: '#64748b', fontWeight: 600 }}>Executed</div>
        </div>

        <div
          style={{
            padding: '0.75rem 0.5rem',
            backgroundColor: 'white',
            borderRadius: '0.5rem',
            border: '1px solid #e2e8f0',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#d97706' }}>
            {brief.metrics.pending_approvals_count}
          </div>
          <div style={{ fontSize: '0.65rem', color: '#64748b', fontWeight: 600 }}>Needs Review</div>
        </div>

        <div
          style={{
            padding: '0.75rem 0.5rem',
            backgroundColor: 'white',
            borderRadius: '0.5rem',
            border: '1px solid #e2e8f0',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#2563eb' }}>
            {brief.metrics.estimated_founder_minutes_saved}m
          </div>
          <div style={{ fontSize: '0.65rem', color: '#64748b', fontWeight: 600 }}>Time Saved</div>
        </div>
      </div>

      {/* Action Items List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 700, color: '#1e293b' }}>
            Verified State & Items ({brief.items.length})
          </h3>
          <button
            onClick={fetchBrief}
            style={{
              background: 'none',
              border: 'none',
              color: '#3b82f6',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: 600,
            }}
          >
            ↻ Refresh
          </button>
        </div>

        {brief.items.length === 0 ? (
          <div
            style={{
              padding: '1.5rem',
              backgroundColor: 'white',
              borderRadius: '0.5rem',
              border: '1px dashed #cbd5e1',
              textAlign: 'center',
              color: '#64748b',
              fontSize: '0.8125rem',
            }}
          >
            All systems quiet. No actions require founder attention.
          </div>
        ) : (
          brief.items.map((item) => <BriefItemCard key={item.id} item={item} />)
        )}
      </div>

      {/* Safety & Source of Truth Disclaimer */}
      <div
        style={{
          padding: '0.625rem',
          backgroundColor: '#f8fafc',
          borderRadius: '0.375rem',
          border: '1px solid #e2e8f0',
          fontSize: '0.65rem',
          color: '#64748b',
          lineHeight: 1.4,
        }}
      >
        🔒 <strong>Safety Guarantee:</strong> {brief.disclaimer}
      </div>
    </div>
  )
}

function BriefItemCard({ item }: { item: BriefItem }): JSX.Element {
  const getBadgeStyle = () => {
    switch (item.category) {
      case 'executed_action':
        return { bg: '#ecfdf5', text: '#065f46', border: '#a7f3d0', label: 'EXECUTED' }
      case 'pending_decision':
        return { bg: '#fffbeb', text: '#92400e', border: '#fde68a', label: 'DECISION NEEDED' }
      case 'escalation':
        return { bg: '#fef2f2', text: '#991b1b', border: '#fecaca', label: 'ESCALATION' }
      case 'pipeline_quiet':
        return { bg: '#f0fdf4', text: '#166534', border: '#bbf7d0', label: 'QUIET PIPELINE' }
      case 'blocked_action':
        return { bg: '#f1f5f9', text: '#475569', border: '#cbd5e1', label: 'BLOCKED' }
    }
  }

  const badge = getBadgeStyle()

  return (
    <div
      style={{
        padding: '0.875rem',
        backgroundColor: 'white',
        borderRadius: '0.5rem',
        border: '1px solid #e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.375rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          style={{
            fontSize: '0.625rem',
            fontWeight: 800,
            padding: '0.125rem 0.375rem',
            borderRadius: '0.25rem',
            backgroundColor: badge.bg,
            color: badge.text,
            border: `1px solid ${badge.border}`,
          }}
        >
          {badge.label}
        </span>
        {item.evidence_receipt_id && (
          <span style={{ fontSize: '0.65rem', color: '#059669', fontFamily: 'monospace', fontWeight: 600 }}>
            rcpt: {item.evidence_receipt_id}
          </span>
        )}
      </div>

      <div style={{ fontWeight: 600, fontSize: '0.8125rem', color: '#1e293b' }}>{item.summary}</div>

      {item.authority_clause && (
        <div style={{ fontSize: '0.7rem', color: '#475569', fontStyle: 'italic' }}>
          Authority: {item.authority_clause}
        </div>
      )}

      {item.recommended_followup && (
        <div style={{ fontSize: '0.7rem', color: '#2563eb', fontWeight: 500, marginTop: '0.125rem' }}>
          → {item.recommended_followup}
        </div>
      )}

      {item.evidence_facts.length > 0 && (
        <div style={{ marginTop: '0.25rem', display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
          {item.evidence_facts.map((fact) => (
            <span
              key={fact.key}
              style={{
                fontSize: '0.625rem',
                padding: '0.1rem 0.3rem',
                backgroundColor: '#f1f5f9',
                borderRadius: '0.2rem',
                color: '#334155',
              }}
            >
              {fact.label}: <strong>{fact.value}</strong>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
