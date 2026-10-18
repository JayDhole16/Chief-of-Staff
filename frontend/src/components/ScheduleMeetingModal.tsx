/**
 * Propose a Google Calendar meeting with a deal's contact. Creates a hash-bound
 * proposal that is booked (with invite and Meet link) only after approval.
 */

import React, { useEffect, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { Deal, GoogleStatus, MeetingRequest, Proposal } from '../api/types'
import { Modal, Spinner } from './ui'

function defaultStart(): string {
  // Next weekday at 11:00 local time, formatted for <input type="datetime-local">.
  const d = new Date()
  d.setDate(d.getDate() + 1)
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1)
  d.setHours(11, 0, 0, 0)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function ScheduleMeetingModal({
  deal,
  onClose,
  onCreated,
  onConnectGoogle,
}: {
  deal: Deal
  onClose: () => void
  onCreated: (proposal: Proposal) => void
  onConnectGoogle: () => void
}): JSX.Element {
  const [google, setGoogle] = useState<GoogleStatus | null>(null)
  const [title, setTitle] = useState(`${deal.company} × call`)
  const [start, setStart] = useState(defaultStart)
  const [duration, setDuration] = useState(30)
  const [agenda, setAgenda] = useState('')
  const [withMeet, setWithMeet] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

  useEffect(() => {
    apiCall<GoogleStatus>('/integrations/google')
      .then(setGoogle)
      .catch((err) => setError(errorMessage(err)))
  }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const startDate = new Date(start)
    if (isNaN(startDate.getTime())) {
      setError('Pick a valid date and time')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const body: MeetingRequest = {
        title: title.trim(),
        start_utc: startDate.toISOString(),
        duration_minutes: duration,
        agenda,
        timezone,
        with_meet: withMeet,
      }
      onCreated(await apiCall<Proposal>(`/deals/${deal.id}/meeting`, { method: 'POST', body }))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const ready = google?.connected && google.can_manage_calendar

  return (
    <Modal title={`Schedule meeting · ${deal.company}`} onClose={() => !busy && onClose()}>
      {!google && !error && <Spinner />}
      {google && !ready && (
        <div className="cos-alert cos-alert-warn" style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem' }}>
          <span>
            {google.configured
              ? 'Connect your Google account (with calendar permission) to book meetings.'
              : 'Google sign-in is not enabled on this server yet.'}
          </span>
          {google.configured && (
            <button type="button" className="cos-btn cos-btn-primary cos-btn-sm" onClick={onConnectGoogle}>
              Connect Google
            </button>
          )}
        </div>
      )}
      <form onSubmit={submit}>
        <p className="cos-muted" style={{ fontSize: '0.82rem', lineHeight: 1.55, marginBottom: '0.9rem' }}>
          Invites <strong style={{ color: '#FFFFFF' }}>{deal.contact_name}</strong> ({deal.contact_email}). Your calendar is checked for conflicts, and the booking waits in Approvals until you confirm it.
        </p>
        <div style={{ display: 'grid', gap: '0.8rem' }}>
          <div>
            <label className="cos-label" htmlFor="meeting-title">Title</label>
            <input id="meeting-title" className="cos-input" value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} />
          </div>
          <div className="cos-grid" style={{ gridTemplateColumns: '2fr 1fr', gap: '0.8rem' }}>
            <div>
              <label className="cos-label" htmlFor="meeting-start">
                Starts <span className="cos-dim" style={{ fontWeight: 400 }}>({timezone})</span>
              </label>
              <input id="meeting-start" className="cos-input" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} required />
            </div>
            <div>
              <label className="cos-label" htmlFor="meeting-duration">Duration</label>
              <select id="meeting-duration" className="cos-select" value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                {[15, 30, 45, 60, 90].map((m) => (
                  <option key={m} value={m}>
                    {m} min
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="cos-label" htmlFor="meeting-agenda">Agenda (goes in the invite)</label>
            <textarea id="meeting-agenda" className="cos-textarea" value={agenda} onChange={(e) => setAgenda(e.target.value)} placeholder={`Call with ${deal.contact_name} about ${deal.title}.`} />
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={withMeet} onChange={(e) => setWithMeet(e.target.checked)} />
            Add a Google Meet link
          </label>
        </div>
        {error && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.85rem' }}>{error}</div>}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.1rem' }}>
          <button type="button" className="cos-btn cos-btn-ghost" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="cos-btn cos-btn-primary" disabled={busy || !ready || !title.trim()}>
            {busy ? 'Checking calendar...' : 'Propose meeting'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
