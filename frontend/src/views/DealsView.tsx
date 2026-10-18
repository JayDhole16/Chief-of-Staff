/**
 * Deals pipeline: create, edit, delete deals and draft AI follow-ups for approval.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { apiCall, errorMessage } from '../api/client'
import type { Deal, DealInput, DealsResponse, DealStage, Proposal, SweepResponse } from '../api/types'
import type { DashboardContext } from '../pages/DashboardPage'
import { PlusIcon, SparkIcon, TrashIcon } from '../components/Icons'
import { EmptyPanel, Modal, PageHeader, Spinner, StatCard } from '../components/ui'
import { ScheduleMeetingModal } from '../components/ScheduleMeetingModal'
import { formatRupees, STAGE_LABELS, timeAgo } from '../utils/formatters'

const STAGES: DealStage[] = ['lead', 'qualified', 'proposal_sent', 'negotiating', 'won', 'lost']

const EMPTY_DEAL: DealInput = {
  company: '',
  title: '',
  contact_name: '',
  contact_email: '',
  contact_phone: '',
  stage: 'lead',
  value_inr: 0,
  notes: '',
  do_not_contact: false,
  last_contact_at: null,
}

function toDateInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  return isNaN(d.getTime()) ? '' : d.toISOString().slice(0, 10)
}

export function DealsView({ ctx }: { ctx: DashboardContext }): JSX.Element {
  const [data, setData] = useState<DealsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'open' | 'quiet' | DealStage>('all')
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<{ id: string | null; form: DealInput } | null>(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [drafting, setDrafting] = useState<Deal | null>(null)
  const [scheduling, setScheduling] = useState<Deal | null>(null)
  const [instructions, setInstructions] = useState('')
  const [draftBusy, setDraftBusy] = useState(false)
  const [sweeping, setSweeping] = useState(false)

  const load = useCallback(() => {
    apiCall<DealsResponse>('/deals')
      .then((res) => {
        setData(res)
        setError(null)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  useEffect(load, [load])

  const visible = useMemo(() => {
    if (!data) return []
    const q = search.trim().toLowerCase()
    return data.deals.filter((d) => {
      if (filter === 'open' && ['won', 'lost'].includes(d.stage)) return false
      if (filter === 'quiet' && !d.is_quiet) return false
      if (STAGES.includes(filter as DealStage) && d.stage !== filter) return false
      if (!q) return true
      return [d.company, d.title, d.contact_name, d.contact_email].some((v) => v.toLowerCase().includes(q))
    })
  }, [data, filter, search])

  const openCreate = () => {
    setFormError(null)
    setEditing({ id: null, form: { ...EMPTY_DEAL, last_contact_at: new Date().toISOString() } })
  }

  const openEdit = (d: Deal) => {
    setFormError(null)
    setEditing({
      id: d.id,
      form: {
        company: d.company,
        title: d.title,
        contact_name: d.contact_name,
        contact_email: d.contact_email,
        contact_phone: d.contact_phone || '',
        stage: d.stage,
        value_inr: d.value_inr,
        notes: d.notes,
        do_not_contact: d.do_not_contact,
        last_contact_at: d.last_contact_at,
      },
    })
  }

  const setField = <K extends keyof DealInput>(key: K, value: DealInput[K]) =>
    setEditing((prev) => (prev ? { ...prev, form: { ...prev.form, [key]: value } } : prev))

  const saveDeal = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editing) return
    setSaving(true)
    setFormError(null)
    try {
      const body = { ...editing.form, value_inr: Number(editing.form.value_inr) || 0 }
      if (editing.id) {
        await apiCall<Deal>(`/deals/${editing.id}`, { method: 'PUT', body })
        ctx.notify('Deal updated')
      } else {
        await apiCall<Deal>('/deals', { method: 'POST', body })
        ctx.notify('Deal added')
      }
      setEditing(null)
      load()
    } catch (err) {
      setFormError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const deleteDeal = async (d: Deal) => {
    if (!window.confirm(`Delete the deal with ${d.company}? This cannot be undone.`)) return
    try {
      await apiCall(`/deals/${d.id}`, { method: 'DELETE' })
      ctx.notify('Deal deleted')
      load()
    } catch (err) {
      ctx.notify(errorMessage(err), 'error')
    }
  }

  const changeStage = async (d: Deal, stage: DealStage) => {
    try {
      await apiCall(`/deals/${d.id}`, { method: 'PUT', body: { stage } })
      load()
    } catch (err) {
      ctx.notify(errorMessage(err), 'error')
    }
  }

  const draftFollowup = async () => {
    if (!drafting) return
    setDraftBusy(true)
    try {
      const proposal = await apiCall<Proposal>(`/deals/${drafting.id}/draft-followup`, { method: 'POST', body: { instructions } })
      ctx.notify(
        proposal.status === 'blocked'
          ? 'Draft created but blocked by guards. Edit it in Approvals.'
          : `Draft ready for ${proposal.contact_name}. Review it in Approvals.`,
        proposal.status === 'blocked' ? 'error' : 'ok'
      )
      ctx.refreshApprovals()
      setDrafting(null)
      setInstructions('')
      ctx.navigate('approvals')
    } catch (err) {
      ctx.notify(errorMessage(err), 'error')
    } finally {
      setDraftBusy(false)
    }
  }

  const runSweep = async () => {
    setSweeping(true)
    try {
      const res = await apiCall<SweepResponse>('/sweep', { method: 'POST' })
      ctx.notify(res.drafted.length ? `Drafted ${res.drafted.length} follow-up(s) for quiet deals.` : `No quiet deals needed a draft (${res.skipped.length} skipped).`)
      ctx.refreshApprovals()
    } catch (err) {
      ctx.notify(errorMessage(err), 'error')
    } finally {
      setSweeping(false)
    }
  }

  return (
    <div className="cos-page">
      <div className="cos-page-inner">
        <PageHeader
          title="Deals"
          subtitle="Your pipeline. Deals with no contact for a while are flagged as quiet."
          actions={
            <>
              <button type="button" className="cos-btn cos-btn-ghost" onClick={runSweep} disabled={sweeping || !data?.count}>
                <SparkIcon size={15} /> {sweeping ? 'Sweeping...' : 'Draft for all quiet deals'}
              </button>
              <button type="button" className="cos-btn cos-btn-primary" onClick={openCreate}>
                <PlusIcon size={15} /> Add deal
              </button>
            </>
          }
        />

        {error && <div className="cos-alert cos-alert-error" style={{ marginBottom: '1rem' }}>{error}</div>}
        {!data && !error && <Spinner />}

        {data && (
          <>
            <div className="cos-grid cos-grid-4" style={{ marginBottom: '1.25rem' }}>
              <StatCard label="Open pipeline" value={formatRupees(data.open_pipeline_inr)} />
              <StatCard label="Won" value={formatRupees(data.won_inr)} />
              <StatCard label="Deals" value={data.count} />
              <StatCard label="Quiet" value={data.deals.filter((d) => d.is_quiet).length} hint={`${ctx.user.quiet_days_threshold}+ days without contact`} />
            </div>

            {data.count === 0 ? (
              <EmptyPanel
                title="No deals yet"
                text="Add a deal with the contact's name and email. Chief of Staff uses it to answer questions and draft follow-ups."
                action={
                  <button type="button" className="cos-btn cos-btn-primary" onClick={openCreate}>
                    Add your first deal
                  </button>
                }
              />
            ) : (
              <>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem', alignItems: 'center' }}>
                  {(['all', 'open', 'quiet', ...STAGES] as const).map((f) => (
                    <button
                      key={f}
                      type="button"
                      className={`cos-btn cos-btn-sm ${filter === f ? 'cos-btn-primary' : 'cos-btn-ghost'}`}
                      onClick={() => setFilter(f)}
                    >
                      {f === 'all' ? 'All' : f === 'open' ? 'Open' : f === 'quiet' ? 'Quiet' : STAGE_LABELS[f]}
                    </button>
                  ))}
                  <input className="cos-input" style={{ maxWidth: '240px', marginLeft: 'auto' }} placeholder="Search deals..." value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search deals" />
                </div>

                <div style={{ display: 'grid', gap: '0.75rem' }}>
                  {visible.length === 0 && <div className="cos-muted" style={{ fontSize: '0.85rem' }}>No deals match this filter.</div>}
                  {visible.map((d) => (
                    <div key={d.id} className="cos-card" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                      <div style={{ flex: '1 1 320px', minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: 800, color: '#FFFFFF', fontSize: '0.95rem' }}>{d.company}</span>
                          <span className="cos-dim cos-mono" style={{ fontSize: '0.7rem' }}>{d.id}</span>
                          {d.is_quiet && <span className="cos-badge cos-badge-amber">{d.days_quiet}d quiet</span>}
                          {d.do_not_contact && <span className="cos-badge cos-badge-red">do not contact</span>}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-main)', marginTop: '0.2rem' }}>{d.title}</div>
                        <div className="cos-muted" style={{ fontSize: '0.78rem', marginTop: '0.25rem' }}>
                          {d.contact_name}
                          {d.contact_email ? ` · ${d.contact_email}` : ' · no email'}
                          {d.contact_phone ? ` · ${d.contact_phone}` : ''}
                          {d.last_contact_at ? ` · last contact ${timeAgo(d.last_contact_at)}` : ''}
                        </div>
                        {d.notes && <div className="cos-dim" style={{ fontSize: '0.78rem', marginTop: '0.35rem', whiteSpace: 'pre-wrap' }}>{d.notes}</div>}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                        <span className="cos-mono" style={{ fontWeight: 800, color: 'var(--emerald-glow)' }}>{formatRupees(d.value_inr)}</span>
                        <select className="cos-select" value={d.stage} onChange={(e) => changeStage(d, e.target.value as DealStage)} style={{ width: '150px', padding: '0.4rem 0.6rem' }} aria-label={`Stage for ${d.company}`}>
                          {STAGES.map((s) => (
                            <option key={s} value={s}>
                              {STAGE_LABELS[s]}
                            </option>
                          ))}
                        </select>
                        <div style={{ display: 'flex', gap: '0.4rem' }}>
                          <button
                            type="button"
                            className="cos-btn cos-btn-primary cos-btn-sm"
                            onClick={() => {
                              setInstructions('')
                              setDrafting(d)
                            }}
                            disabled={d.do_not_contact || !d.contact_email}
                            title={!d.contact_email ? 'Add a contact email first' : d.do_not_contact ? 'Contact opted out' : 'Draft an AI follow-up'}
                          >
                            <SparkIcon size={13} /> Draft follow-up
                          </button>
                          <button
                            type="button"
                            className="cos-btn cos-btn-ghost cos-btn-sm"
                            onClick={() => setScheduling(d)}
                            disabled={d.do_not_contact || !d.contact_email}
                            title={!d.contact_email ? 'Add a contact email first' : 'Book a Google Calendar meeting'}
                          >
                            Schedule meeting
                          </button>
                          <button type="button" className="cos-btn cos-btn-ghost cos-btn-sm" onClick={() => openEdit(d)}>
                            Edit
                          </button>
                          <button type="button" className="cos-btn cos-btn-danger cos-btn-sm" onClick={() => deleteDeal(d)} aria-label={`Delete ${d.company}`}>
                            <TrashIcon size={13} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>

      {editing && (
        <Modal title={editing.id ? 'Edit deal' : 'Add deal'} onClose={() => setEditing(null)}>
          <form onSubmit={saveDeal}>
            <div className="cos-grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '0.85rem' }}>
              <div>
                <label className="cos-label" htmlFor="deal-company">Company *</label>
                <input id="deal-company" className="cos-input" value={editing.form.company} onChange={(e) => setField('company', e.target.value)} required />
              </div>
              <div>
                <label className="cos-label" htmlFor="deal-title">Deal title *</label>
                <input id="deal-title" className="cos-input" value={editing.form.title} onChange={(e) => setField('title', e.target.value)} placeholder="e.g. CRM integration" required />
              </div>
              <div>
                <label className="cos-label" htmlFor="deal-contact">Contact name *</label>
                <input id="deal-contact" className="cos-input" value={editing.form.contact_name} onChange={(e) => setField('contact_name', e.target.value)} required />
              </div>
              <div>
                <label className="cos-label" htmlFor="deal-email">Contact email</label>
                <input id="deal-email" className="cos-input" type="email" value={editing.form.contact_email} onChange={(e) => setField('contact_email', e.target.value)} />
              </div>
              <div>
                <label className="cos-label" htmlFor="deal-phone">
                  WhatsApp / phone <span className="cos-dim" style={{ fontWeight: 400 }}>(with country code)</span>
                </label>
                <input id="deal-phone" className="cos-input" type="tel" value={editing.form.contact_phone} onChange={(e) => setField('contact_phone', e.target.value)} placeholder="+91 98765 43210" />
              </div>
              <div>
                <label className="cos-label" htmlFor="deal-value">Value (₹)</label>
                <input id="deal-value" className="cos-input" type="number" min={0} step={1000} value={editing.form.value_inr} onChange={(e) => setField('value_inr', Number(e.target.value))} />
              </div>
              <div>
                <label className="cos-label" htmlFor="deal-stage">Stage</label>
                <select id="deal-stage" className="cos-select" value={editing.form.stage} onChange={(e) => setField('stage', e.target.value as DealStage)}>
                  {STAGES.map((s) => (
                    <option key={s} value={s}>
                      {STAGE_LABELS[s]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="cos-label" htmlFor="deal-last">Last contact</label>
                <input
                  id="deal-last"
                  className="cos-input"
                  type="date"
                  value={toDateInput(editing.form.last_contact_at)}
                  max={new Date().toISOString().slice(0, 10)}
                  onChange={(e) => setField('last_contact_at', e.target.value ? new Date(`${e.target.value}T09:00:00`).toISOString() : null)}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', color: 'var(--text-main)', cursor: 'pointer', paddingBottom: '0.6rem' }}>
                  <input type="checkbox" checked={editing.form.do_not_contact} onChange={(e) => setField('do_not_contact', e.target.checked)} />
                  Do not contact (opted out)
                </label>
              </div>
            </div>
            <div style={{ marginTop: '0.85rem' }}>
              <label className="cos-label" htmlFor="deal-notes">Notes for your chief of staff</label>
              <textarea id="deal-notes" className="cos-textarea" value={editing.form.notes} onChange={(e) => setField('notes', e.target.value)} placeholder="Context, objections, next steps..." />
            </div>
            {formError && <div className="cos-alert cos-alert-error" style={{ marginTop: '0.85rem' }}>{formError}</div>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.1rem' }}>
              <button type="button" className="cos-btn cos-btn-ghost" onClick={() => setEditing(null)}>
                Cancel
              </button>
              <button type="submit" className="cos-btn cos-btn-primary" disabled={saving}>
                {saving ? 'Saving...' : editing.id ? 'Save changes' : 'Add deal'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {scheduling && (
        <ScheduleMeetingModal
          deal={scheduling}
          onClose={() => setScheduling(null)}
          onConnectGoogle={() => {
            setScheduling(null)
            ctx.navigate('keys')
          }}
          onCreated={(proposal) => {
            setScheduling(null)
            ctx.notify(
              proposal.policy_verdict === 'ALLOW'
                ? `Meeting with ${proposal.contact_name} ready to approve`
                : `Meeting proposed. Review the findings in Approvals.`,
              proposal.status === 'blocked' ? 'error' : 'ok'
            )
            ctx.refreshApprovals()
            ctx.navigate('approvals')
          }}
        />
      )}

      {drafting && (
        <Modal title={`Draft follow-up · ${drafting.company}`} onClose={() => !draftBusy && setDrafting(null)}>
          <p className="cos-muted" style={{ fontSize: '0.84rem', lineHeight: 1.55, marginBottom: '0.9rem' }}>
            Your AI provider drafts an email to <strong style={{ color: '#FFFFFF' }}>{drafting.contact_name}</strong> ({drafting.contact_email}) using only this deal's facts. The draft is checked by the policy guards and waits in Approvals. Nothing is sent until you approve it.
          </p>
          <label className="cos-label" htmlFor="draft-instructions">Instructions (optional)</label>
          <textarea id="draft-instructions" className="cos-textarea" value={instructions} onChange={(e) => setInstructions(e.target.value)} placeholder="e.g. Propose a call next Tuesday afternoon; mention the case study we sent." />
          {!ctx.user.active_llm_provider && (
            <div className="cos-alert cos-alert-warn" style={{ marginTop: '0.85rem' }}>
              Add an AI provider key in API Keys first.
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.1rem' }}>
            <button type="button" className="cos-btn cos-btn-ghost" onClick={() => setDrafting(null)} disabled={draftBusy}>
              Cancel
            </button>
            <button type="button" className="cos-btn cos-btn-primary" onClick={draftFollowup} disabled={draftBusy || !ctx.user.active_llm_provider}>
              {draftBusy ? 'Drafting...' : 'Generate draft'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
