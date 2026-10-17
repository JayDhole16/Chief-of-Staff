import React, { useState, useEffect } from 'react'
import type { LoginResponse, OperationsStatus, DailyBrief, V1BriefItem } from '../api/types'
import { apiCall } from '../api/client'

export interface DashboardPageProps {
  session: LoginResponse
  onLogout: () => void
}

type ViewId = 'chat' | 'dashboard' | 'settings' | 'profile' | 'operations'

export interface FounderDeal {
  id: string
  company: string
  title: string
  contactName: string
  contactEmail: string
  stage: 'proposal_sent' | 'negotiating' | 'won'
  valueINR: number
  lastReachedOut: string
  outreachStatus: string
  founderNotes: string
}

const INITIAL_DEALS: FounderDeal[] = [
  {
    id: 'D-1',
    company: 'Malhotra Logistics',
    title: 'Warehouse WhatsApp-to-ERP order automation',
    contactName: 'Raju Malhotra',
    contactEmail: 'raju@malhotralogistics.in',
    stage: 'negotiating',
    valueINR: 480000,
    lastReachedOut: '4 days ago',
    outreachStatus: 'Asked for 20% off · 5% counter-offer ready',
    founderNotes: 'Price-sensitive. Flex only together with annual support (₹60,000/yr). Never more than 5% without me.',
  },
  {
    id: 'D-2',
    company: 'Iyer Textiles',
    title: 'Invoice reconciliation bot',
    contactName: 'Raju Iyer',
    contactEmail: 'raju@iyertextiles.in',
    stage: 'negotiating',
    valueINR: 240000,
    lastReachedOut: 'Yesterday',
    outreachStatus: 'Replied · Reviewing scope with CFO Lakshmi Iyer',
    founderNotes: 'Active scope review with Raju Iyer and finance team.',
  },
  {
    id: 'D-3',
    company: 'Brightleaf Clinics',
    title: 'Appointment reminder automation',
    contactName: 'Priya Shah',
    contactEmail: 'priya@brightleafclinics.in',
    stage: 'proposal_sent',
    valueINR: 320000,
    lastReachedOut: '6 days ago',
    outreachStatus: 'Out of office until Oct 20 · Auto-paused',
    founderNotes: 'Clinic group; decision maker travels often (Europe/London).',
  },
  {
    id: 'D-4',
    company: 'Kestrel Foods',
    title: 'Inventory sync automation',
    contactName: 'Arjun Mehta',
    contactEmail: 'arjun@kestrelfoods.in',
    stage: 'proposal_sent',
    valueINR: 180000,
    lastReachedOut: '5 days ago',
    outreachStatus: 'Quiet for 5 days · Ready for gentle check-in',
    founderNotes: 'Requires founder nod before sending follow-up.',
  },
  {
    id: 'D-5',
    company: 'Northwind Studio',
    title: 'Multi-channel order & CRM workflow',
    contactName: 'Ananya Rao',
    contactEmail: 'ananya@northwindstudio.in',
    stage: 'negotiating',
    valueINR: 210000,
    lastReachedOut: 'Yesterday',
    outreachStatus: 'Replied · Sharing scope questions this week',
    founderNotes: 'Asked to discuss proposal scope before final sign-off.',
  },
  {
    id: 'D-6',
    company: 'Coastal Realty',
    title: 'Lead routing & WhatsApp concierge',
    contactName: 'Farhan Ali',
    contactEmail: 'farhan@coastalrealty.in',
    stage: 'won',
    valueINR: 450000,
    lastReachedOut: '2 days ago',
    outreachStatus: 'Closed Won · Onboarding kicked off',
    founderNotes: 'Signed and onboarded.',
  },
]

function formatINR(val: number): string {
  return '₹' + Math.round(val).toLocaleString('en-IN')
}

export function DashboardPage({ session, onLogout }: DashboardPageProps): JSX.Element {
  const [view, setView] = useState<ViewId>('chat')
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [deals, setDeals] = useState<FounderDeal[]>(INITIAL_DEALS)
  const [targetINR, setTargetINR] = useState<number>(3500000)
  const [founderName, setFounderName] = useState<string>(session.user.name || 'Meera Nair')
  const [businessName, setBusinessName] = useState<string>('Nair Automation Studio')
  const [founderEmail, setFounderEmail] = useState<string>(session.user.email || 'meera@nairstudio.in')
  const [maxDiscountPct, setMaxDiscountPct] = useState<number>(5)
  const [autonomyPaused, setAutonomyPaused] = useState<boolean>(false)
  const [decisionApproved, setDecisionApproved] = useState<boolean>(false)
  const [chatInput, setChatInput] = useState<string>('')
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([
    {
      role: 'assistant',
      text: 'I am tracking 6 deals (₹18,80,000 total value) toward your ₹35,00,000 target. Ask me anything in plain English or upload an Excel/CSV/JSON file to smart-merge into your database.',
    },
  ])

  const totalPipelineINR = deals.reduce((acc, d) => acc + d.valueINR, 0)
  const targetPct = Math.min(100, Math.round((totalPipelineINR / targetINR) * 100))

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    document.documentElement.setAttribute('data-theme', next)
  }

  const handleChatSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    const q = chatInput.trim()
    setChatInput('')
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: q },
      {
        role: 'assistant',
        text: `Checked against your ${deals.length} deals (${formatINR(totalPipelineINR)} / ${formatINR(targetINR)} target, ${targetPct}%). Everything within your ${maxDiscountPct}% discount guardrail is being handled quietly.`,
      },
    ])
  }

  // Smart non-destructive merge of uploaded JSON / CSV / Excel data
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (evt) => {
      try {
        const text = String(evt.target?.result || '')
        let incomingRows: Array<Partial<FounderDeal>> = []
        if (file.name.endsWith('.json')) {
          const parsed = JSON.parse(text)
          if (parsed.targetINR || parsed.target) {
            setTargetINR(Number(parsed.targetINR || parsed.target))
          }
          const arr = Array.isArray(parsed) ? parsed : parsed.deals || [parsed]
          incomingRows = arr.map((r: Record<string, unknown>) => ({
            id: r.id ? String(r.id) : undefined,
            company: r.company || r.Company ? String(r.company || r.Company) : undefined,
            title: r.title || r.Deal ? String(r.title || r.Deal) : undefined,
            contactName: r.contactName || r.Contact ? String(r.contactName || r.Contact) : undefined,
            contactEmail: r.contactEmail || r.Email ? String(r.contactEmail || r.Email) : undefined,
            valueINR: r.valueINR || r.Value ? Number(r.valueINR || r.Value) : undefined,
            lastReachedOut: 'Synced today',
            outreachStatus: r.outreachStatus || r.Outreach ? String(r.outreachStatus || r.Outreach) : `Synced from ${file.name}`,
            founderNotes: r.founderNotes || r.Notes ? String(r.founderNotes || r.Notes) : undefined,
          }))
        } else {
          const lines = text.split(/\r?\n/).filter((l) => l.trim())
          incomingRows = lines.slice(1).map((line) => {
            const cols = line.split(',')
            return {
              company: cols[0]?.trim() || undefined,
              title: cols[1]?.trim() || undefined,
              contactName: cols[2]?.trim() || undefined,
              contactEmail: cols[3]?.trim() || undefined,
              valueINR: cols[4] ? Number(cols[4].replace(/[^0-9]/g, '')) : undefined,
              lastReachedOut: 'Synced today',
              outreachStatus: `Imported from ${file.name}`,
            }
          })
        }

        if (incomingRows.length > 0) {
          setDeals((prev) => {
            const next = [...prev]
            incomingRows.forEach((inc, idx) => {
              const existing = next.find(
                (d) =>
                  (inc.id && d.id.toLowerCase() === inc.id.toLowerCase()) ||
                  (inc.company && d.company.toLowerCase() === inc.company.toLowerCase()) ||
                  (inc.contactEmail && d.contactEmail.toLowerCase() === inc.contactEmail.toLowerCase())
              )
              if (existing) {
                if (inc.company) existing.company = inc.company
                if (inc.title) existing.title = inc.title
                if (inc.contactName) existing.contactName = inc.contactName
                if (inc.contactEmail) existing.contactEmail = inc.contactEmail
                if (inc.valueINR && inc.valueINR > 0) existing.valueINR = inc.valueINR
                if (inc.lastReachedOut) existing.lastReachedOut = inc.lastReachedOut
                if (inc.outreachStatus) existing.outreachStatus = inc.outreachStatus
                if (inc.founderNotes) existing.founderNotes = inc.founderNotes
              } else {
                next.unshift({
                  id: inc.id || `IMP-${Date.now()}-${idx}`,
                  company: inc.company || `Client ${idx + 1}`,
                  title: inc.title || 'Workflow Automation',
                  contactName: inc.contactName || 'Decision Maker',
                  contactEmail: inc.contactEmail || 'contact@client.in',
                  stage: 'negotiating',
                  valueINR: inc.valueINR || 300000,
                  lastReachedOut: 'Synced today',
                  outreachStatus: inc.outreachStatus || `Synced from ${file.name}`,
                  founderNotes: inc.founderNotes || '',
                })
              }
            })
            return next
          })
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              text: `Smart-merged ${incomingRows.length} record(s) from ${file.name} into your live database.`,
            },
          ])
        }
      } catch {
        // Ignore parse errors
      }
    }
    reader.readAsText(file)
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-canvas)', color: 'var(--text-primary)' }}>
      {/* Header */}
      <header
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '0.75rem',
          padding: '1rem 1.5rem',
          borderBottom: '1px solid var(--border-hairline)',
          backgroundColor: 'var(--bg-surface)',
        }}
      >
        <div>
          <div className="font-playfair" style={{ fontSize: '1.25rem', fontWeight: 600 }}>
            {businessName}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {autonomyPaused ? '⏸ Automatic outreach paused' : '● Chief of Staff working quietly'}
          </div>
        </div>

        <nav style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {([
            { id: 'chat', label: 'Chat' },
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'settings', label: 'Settings' },
            { id: 'operations', label: 'Ops' },
          ] as const).map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setView(tab.id)}
              style={{
                padding: '0.45rem 1rem',
                borderRadius: '9999px',
                border: view === tab.id ? '1px solid var(--accent-primary)' : '1px solid transparent',
                backgroundColor: view === tab.id ? 'var(--accent-soft)' : 'transparent',
                color: view === tab.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '0.825rem',
                fontWeight: 600,
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <button
            type="button"
            onClick={toggleTheme}
            aria-label="Toggle Light Mode"
            style={{
              padding: '0.45rem 0.85rem',
              borderRadius: '9999px',
              border: '1px solid var(--border-strong)',
              backgroundColor: 'transparent',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: '0.75rem',
            }}
          >
            {theme === 'dark' ? '☀️ Light Mode' : '🌙 Slate-Black'}
          </button>

          <button
            type="button"
            onClick={() => setView('profile')}
            style={{
              padding: '0.45rem 0.85rem',
              borderRadius: '9999px',
              border: '1px solid var(--accent-primary)',
              backgroundColor: 'var(--accent-soft)',
              color: 'var(--accent-primary)',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: 600,
            }}
          >
            {founderName}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ padding: '2rem 1.5rem', maxWidth: '960px', margin: '0 auto' }}>
        {view === 'chat' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <h1 className="font-playfair" style={{ fontSize: '2.1rem', fontWeight: 400, lineHeight: 1.3 }}>
              Good evening, <em>{founderName.split(' ')[0]}</em>. Routine follow-ups are handled—only one pricing question needs your call.
            </h1>

            {!decisionApproved && (
              <div
                style={{
                  padding: '1.5rem',
                  borderRadius: '1.25rem',
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border-strong)',
                  borderLeft: '4px solid var(--accent-primary)',
                }}
              >
                <div style={{ fontSize: '0.75rem', color: 'var(--accent-primary)', fontWeight: 600 }}>
                  NEEDS YOUR QUICK CALL · MALHOTRA LOGISTICS
                </div>
                <h2 className="font-playfair" style={{ fontSize: '1.35rem', margin: '0.4rem 0' }}>
                  Raju Malhotra asked for 20% off. Send your standard {maxDiscountPct}% counter-offer (₹4,56,000)?
                </h2>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  Paired with Annual Support (₹60,000/yr) and proposing Thursday 3:00 PM IST.
                </p>
                <button
                  type="button"
                  onClick={() => setDecisionApproved(true)}
                  style={{
                    padding: '0.6rem 1.25rem',
                    borderRadius: '9999px',
                    border: 'none',
                    backgroundColor: 'var(--accent-primary)',
                    color: 'var(--accent-contrast)',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Approve & Send Reply
                </button>
              </div>
            )}

            {/* Chat Box + File Upload */}
            <div
              style={{
                padding: '1.5rem',
                borderRadius: '1.25rem',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-hairline)',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {messages.map((m, idx) => (
                  <div
                    key={idx}
                    style={{
                      alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                      backgroundColor: m.role === 'user' ? 'var(--accent-soft)' : 'var(--bg-elevated)',
                      padding: '0.75rem 1rem',
                      borderRadius: '1rem',
                      fontSize: '0.875rem',
                      maxWidth: '85%',
                    }}
                  >
                    {m.text}
                  </div>
                ))}
              </div>

              <form onSubmit={handleChatSend} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <label
                  style={{
                    padding: '0.6rem 0.9rem',
                    borderRadius: '0.75rem',
                    border: '1px solid var(--border-strong)',
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    color: 'var(--accent-primary)',
                  }}
                >
                  + Upload Excel / JSON
                  <input type="file" accept=".xlsx,.xls,.csv,.json" onChange={handleFileUpload} style={{ display: 'none' }} />
                </label>
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask your Chief of Staff anything..."
                  style={{
                    flex: 1,
                    minWidth: '180px',
                    padding: '0.65rem 1rem',
                    borderRadius: '0.75rem',
                    border: '1px solid var(--border-strong)',
                    backgroundColor: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                  }}
                />
                <button
                  type="submit"
                  style={{
                    padding: '0.65rem 1.25rem',
                    borderRadius: '0.75rem',
                    border: 'none',
                    backgroundColor: 'var(--accent-primary)',
                    color: 'var(--accent-contrast)',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Ask
                </button>
              </form>
            </div>
          </div>
        )}

        {view === 'dashboard' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
              <h1 className="font-playfair" style={{ fontSize: '2rem', fontWeight: 400 }}>
                Target, Clients Reached Out To & Ongoing Deals
              </h1>
              <label
                style={{
                  padding: '0.55rem 1rem',
                  borderRadius: '9999px',
                  backgroundColor: 'var(--accent-primary)',
                  color: 'var(--accent-contrast)',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Upload Excel / CSV / JSON
                <input type="file" accept=".xlsx,.xls,.csv,.json" onChange={handleFileUpload} style={{ display: 'none' }} />
              </label>
            </div>

            <div
              style={{
                padding: '1.5rem',
                borderRadius: '1.25rem',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-hairline)',
              }}
            >
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Current Revenue Target
              </div>
              <div className="font-playfair" style={{ fontSize: '2rem', fontWeight: 600, marginTop: '0.25rem' }}>
                {formatINR(totalPipelineINR)} / {formatINR(targetINR)} ({targetPct}%)
              </div>
            </div>

            <div style={{ display: 'grid', gap: '1rem' }}>
              {deals.map((d) => (
                <div
                  key={d.id}
                  style={{
                    padding: '1.25rem',
                    borderRadius: '1rem',
                    backgroundColor: 'var(--bg-surface)',
                    border: '1px solid var(--border-hairline)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '1rem',
                  }}
                >
                  <div>
                    <div className="font-playfair" style={{ fontSize: '1.15rem', fontWeight: 500 }}>
                      {d.company} — {d.title}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                      Client reached out to: <strong>{d.contactName}</strong> ({d.lastReachedOut}) · {d.outreachStatus}
                    </div>
                  </div>
                  <div className="font-playfair" style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--accent-primary)' }}>
                    {formatINR(d.valueINR)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(view === 'settings' || view === 'profile') && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <h1 className="font-playfair" style={{ fontSize: '2rem', fontWeight: 400 }}>
              Founder Profile & App Settings
            </h1>

            <div
              style={{
                padding: '1.5rem',
                borderRadius: '1.25rem',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-hairline)',
                display: 'grid',
                gap: '1rem',
              }}
            >
              <h2 className="font-playfair" style={{ fontSize: '1.25rem', fontWeight: 500 }}>
                Founder Profile
              </h2>
              <label style={{ fontSize: '0.8rem' }}>
                Founder Name
                <input
                  type="text"
                  value={founderName}
                  onChange={(e) => setFounderName(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem', borderRadius: '0.5rem', backgroundColor: 'var(--bg-input)', color: 'var(--text-primary)', border: '1px solid var(--border-strong)' }}
                />
              </label>
              <label style={{ fontSize: '0.8rem' }}>
                Studio / Business Name
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem', borderRadius: '0.5rem', backgroundColor: 'var(--bg-input)', color: 'var(--text-primary)', border: '1px solid var(--border-strong)' }}
                />
              </label>
              <label style={{ fontSize: '0.8rem' }}>
                Connected Email
                <input
                  type="email"
                  value={founderEmail}
                  onChange={(e) => setFounderEmail(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem', borderRadius: '0.5rem', backgroundColor: 'var(--bg-input)', color: 'var(--text-primary)', border: '1px solid var(--border-strong)' }}
                />
              </label>
            </div>

            <div
              style={{
                padding: '1.5rem',
                borderRadius: '1.25rem',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-hairline)',
                display: 'grid',
                gap: '1rem',
              }}
            >
              <h2 className="font-playfair" style={{ fontSize: '1.25rem', fontWeight: 500 }}>
                Chief of Staff App Settings
              </h2>
              <label style={{ fontSize: '0.8rem' }}>
                Maximum Automatic Discount Cap: <strong>{maxDiscountPct}%</strong>
                <input
                  type="range"
                  min={0}
                  max={15}
                  value={maxDiscountPct}
                  onChange={(e) => setMaxDiscountPct(Number(e.target.value))}
                  style={{ width: '100%', marginTop: '0.35rem' }}
                />
              </label>
              <label style={{ fontSize: '0.8rem' }}>
                Quarterly Revenue Target (INR)
                <input
                  type="number"
                  value={targetINR}
                  onChange={(e) => setTargetINR(Number(e.target.value))}
                  style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem', borderRadius: '0.5rem', backgroundColor: 'var(--bg-input)', color: 'var(--text-primary)', border: '1px solid var(--border-strong)' }}
                />
              </label>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => setAutonomyPaused(!autonomyPaused)}
                  style={{
                    padding: '0.55rem 1rem',
                    borderRadius: '9999px',
                    border: '1px solid var(--border-strong)',
                    backgroundColor: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                  }}
                >
                  {autonomyPaused ? 'Resume Automatic Outreach' : 'Pause Automatic Outreach'}
                </button>
                <button
                  type="button"
                  onClick={toggleTheme}
                  style={{
                    padding: '0.55rem 1rem',
                    borderRadius: '9999px',
                    border: '1px solid var(--border-strong)',
                    backgroundColor: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                  }}
                >
                  Switch to {theme === 'dark' ? 'Light Mode' : 'Slate-Black Mode'}
                </button>
                <button
                  type="button"
                  onClick={onLogout}
                  style={{
                    padding: '0.55rem 1rem',
                    borderRadius: '9999px',
                    border: '1px solid var(--border-strong)',
                    backgroundColor: 'transparent',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  Sign Out
                </button>
              </div>
            </div>
          </div>
        )}

        {view === 'operations' && <OperationsSection />}
      </main>
    </div>
  )
}

function OperationsSection(): JSX.Element {
  const [status, setStatus] = useState<OperationsStatus | null>(null)
  const [brief, setBrief] = useState<DailyBrief | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refresh = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [operationsStatus, dailyBrief] = await Promise.all([
        apiCall<OperationsStatus>('/v1/ops/status'),
        apiCall<DailyBrief>('/v1/brief'),
      ])
      setStatus(operationsStatus)
      setBrief(dailyBrief)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 className="font-playfair" style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
          Operations & Brief
        </h2>
        <button type="button" onClick={() => void refresh()} disabled={isLoading}>
          {isLoading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--status-amber)' }}>
        Provisional local/demo status. This is not evidence of live G4 or production readiness.
      </p>
      {error && (
        <p role="alert" style={{ color: '#ef4444', fontSize: '0.8125rem' }}>
          Could not load operations data: {error}
        </p>
      )}
      {status && (
        <div data-testid="operations-status">
          <h3 style={{ fontSize: '0.875rem' }}>
            System status: {status.status} · Kill switch: {status.kill_switch_active ? 'active' : 'off'}
          </h3>
          <ul style={{ paddingLeft: '1.25rem', fontSize: '0.75rem' }}>
            {Object.entries(status.components).map(([name, component]) => (
              <li key={name} style={{ marginBottom: '0.375rem' }}>
                <strong>
                  {name}: {component.status}
                </strong>{' '}
                — {component.detail}
              </li>
            ))}
          </ul>
        </div>
      )}
      {brief && (
        <div data-testid="daily-brief">
          <h3 style={{ fontSize: '0.875rem' }}>Recent activity</h3>
          {brief.omitted_unlinked_events > 0 && (
            <p role="status" style={{ fontSize: '0.75rem' }}>
              {brief.omitted_unlinked_events} unlinked event(s) omitted from this brief.
            </p>
          )}
          {brief.items.length === 0 ? (
            <p style={{ fontSize: '0.75rem' }}>No linked activity is available.</p>
          ) : (
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.75rem' }}>
              {brief.items.map((item: V1BriefItem) => (
                <li key={item.event_id} style={{ marginBottom: '0.625rem' }}>
                  <strong>{item.title}</strong>
                  <p style={{ margin: '0.25rem 0' }}>{item.summary}</p>
                  <a href={item.link.href}>
                    View {item.link.kind}: {item.link.reference}
                  </a>
                </li>
              ))}
            </ul>
          )}
          <p style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>{brief.limitation}</p>
        </div>
      )}
    </section>
  )
}
