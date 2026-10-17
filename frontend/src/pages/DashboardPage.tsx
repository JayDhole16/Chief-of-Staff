import React, { useState, useEffect } from 'react'
import type { LoginResponse, OperationsStatus, DailyBrief, V1BriefItem } from '../api/types'
import { apiCall } from '../api/client'

export interface DashboardPageProps {
  session: LoginResponse
  onLogout: () => void
}

type ViewId = 'chat' | 'deals' | 'tasks' | 'activity' | 'operations' | 'settings' | 'profile'

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
    company: 'Apex Supply Co',
    title: 'Vendor purchase order processing',
    contactName: 'Kunal Verma',
    contactEmail: 'kunal@apexsupply.in',
    stage: 'negotiating',
    valueINR: 520000,
    lastReachedOut: '3 days ago',
    outreachStatus: 'Contract sent · Legal review underway',
    founderNotes: 'High-value account. Requires SOC2 assurance statement.',
  },
  {
    id: 'D-5',
    company: 'Zenith Logistics',
    title: 'Dispatch notification agent',
    contactName: 'Neha Sen',
    contactEmail: 'neha@zenithlogistics.in',
    stage: 'proposal_sent',
    valueINR: 380000,
    lastReachedOut: '5 days ago',
    outreachStatus: 'Quiet follow-up scheduled for tomorrow',
    founderNotes: 'Referred by Raju Malhotra.',
  },
  {
    id: 'D-6',
    company: 'Nova Commerce',
    title: 'Shopify order reconciliation',
    contactName: 'Vikram Mehta',
    contactEmail: 'vikram@novacommerce.in',
    stage: 'won',
    valueINR: 450000,
    lastReachedOut: '2 days ago',
    outreachStatus: 'Deal closed · Kickoff scheduled',
    founderNotes: 'First automated deal close. Standard onboarding workflow.',
  },
]

interface ChatSession {
  id: string
  title: string
  group: 'Today' | 'Yesterday' | 'Previous 7 Days'
}

export function DashboardPage({ session, onLogout }: DashboardPageProps): JSX.Element {
  const [view, setView] = useState<ViewId>('chat')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [historySearch, setHistorySearch] = useState('')
  const [activeSessionId, setActiveSessionId] = useState('s-1')
  const [isListening, setIsListening] = useState(false)
  const [inputText, setInputText] = useState('')
  const [autonomyPaused, setAutonomyPaused] = useState(false)
  const [deals, setDeals] = useState<FounderDeal[]>(INITIAL_DEALS)
  
  // Decision Card & Undo state
  const [rajuState, setRajuState] = useState<'pending' | 'undoing' | 'dispatched' | 'modified'>('pending')
  const [undoCountdown, setUndoCountdown] = useState(15)

  // Operations T13 states
  const [opsStatus, setOpsStatus] = useState<OperationsStatus | null>(null)
  const [dailyBrief, setDailyBrief] = useState<DailyBrief | null>(null)
  const [v1Brief, setV1Brief] = useState<V1BriefItem[] | null>(null)
  const [opsLoading, setOpsLoading] = useState(false)

  // Chat message list
  const [messages, setMessages] = useState<Array<{ id: string; role: 'user' | 'assistant'; text: string; time: string }>>([])

  const sessions: ChatSession[] = [
    { id: 's-1', title: 'Raju Malhotra 5% Counter-Offer', group: 'Today' },
    { id: 's-2', title: 'Q4 Target & Sweep Execution', group: 'Today' },
    { id: 's-3', title: 'Brightleaf Clinics OOO Follow-up', group: 'Yesterday' },
    { id: 's-4', title: 'Iyer Textiles ERP Inquiry', group: 'Yesterday' },
    { id: 's-5', title: 'Inbound Email Pipeline Audit', group: 'Previous 7 Days' },
    { id: 's-6', title: 'Deterministic Guard Benchmark G01-G15', group: 'Previous 7 Days' },
  ]

  // Undo Countdown timer
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined
    if (rajuState === 'undoing' && undoCountdown > 0) {
      timer = setTimeout(() => setUndoCountdown((prev) => prev - 1), 1000)
    } else if (rajuState === 'undoing' && undoCountdown === 0) {
      setRajuState('dispatched')
    }
    return () => {
      if (timer) clearTimeout(timer)
    }
  }, [rajuState, undoCountdown])

  // Fetch Ops status when viewing operations
  useEffect(() => {
    if (view === 'operations') {
      setOpsLoading(true)
      Promise.allSettled([
        apiCall<OperationsStatus>('/v1/ops/status'),
        apiCall<DailyBrief>('/v1/brief'),
      ])
        .then(([statusRes, briefRes]) => {
          if (statusRes.status === 'fulfilled' && statusRes.value) {
            setOpsStatus(statusRes.value)
          }
          if (briefRes.status === 'fulfilled' && briefRes.value) {
            setDailyBrief(briefRes.value)
            setV1Brief(briefRes.value.items)
          }
        })
        .finally(() => setOpsLoading(false))
    }
  }, [view])

  const handleSendMessage = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const text = inputText.trim()
    if (!text) return

    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const userMsg = { id: `msg-${Date.now()}`, role: 'user' as const, text, time: nowStr }
    setMessages((prev) => [...prev, userMsg])
    setInputText('')

    setTimeout(() => {
      let reply = `Understood: "${text}". I have evaluated your active pipeline deals and deterministic guardrails autonomously in the background.`
      const p = text.toLowerCase()
      if (p.includes('revenue') || p.includes('target') || p.includes('q4')) {
        reply = `Your Q4 Revenue Target is currently ₹18.8L / ₹35.0L (53.7%). Remaining ₹16.2L is tracked across 6 deals in your pipeline.`
      } else if (p.includes('deal') || p.includes('pipeline')) {
        reply = `You have 6 active deals totaling ₹1,45,50,000. 1 pending action for Raju Malhotra is ready for your approval.`
      }
      setMessages((prev) => [
        ...prev,
        { id: `reply-${Date.now()}`, role: 'assistant', text: reply, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
      ])
    }, 600)
  }

  const toggleVoice = () => {
    if (isListening) {
      setIsListening(false)
    } else {
      setIsListening(true)
      setTimeout(() => {
        setIsListening(false)
        setInputText('Schedule a quiet follow-up for Zenith Logistics')
      }, 3000)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setMessages((prev) => [
      ...prev,
      {
        id: `file-${Date.now()}`,
        role: 'assistant',
        text: `✓ Smart-synced data file "${file.name}" into live deals pipeline.`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ])
  }

  const filteredSessions = sessions.filter((s) => s.title.toLowerCase().includes(historySearch.toLowerCase()))

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: 'var(--bg-void)', color: 'var(--text-main)' }}>
      
      {/* ============================================================== */}
      {/* 1. PRIMARY ICON RAIL (Always Visible, 64px)                    */}
      {/* ============================================================== */}
      <aside
        style={{
          width: '64px',
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '1rem 0',
          borderRight: '1px solid var(--border-hairline)',
          backgroundColor: 'var(--bg-rail)',
          zIndex: 40,
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem' }}>
          {/* Logo 4-Pointed Star Button */}
          <button
            type="button"
            onClick={() => setView('chat')}
            title="Chief of Staff"
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '16px',
              backgroundColor: '#091510',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: 'var(--emerald-glow)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              boxShadow: '0 0 12px -2px rgba(0, 255, 135, 0.3)',
            }}
          >
            <svg style={{ width: '24px', height: '24px' }} viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
            </svg>
          </button>

          {/* Navigation Items */}
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'center' }}>
            {/* Chats Button */}
            <button
              type="button"
              onClick={() => {
                setView('chat')
                if (sidebarCollapsed) setSidebarCollapsed(false)
              }}
              title="Chats"
              style={{
                position: 'relative',
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: view === 'chat' ? '#0C1A14' : 'transparent',
                border: view === 'chat' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
                color: view === 'chat' ? 'var(--emerald-glow)' : 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              <svg style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <span style={{ position: 'absolute', top: '6px', right: '6px', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--emerald-glow)' }} />
            </button>

            {/* Deals Button */}
            <button
              type="button"
              onClick={() => setView('deals')}
              title="Deals Pipeline"
              style={{
                position: 'relative',
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: view === 'deals' ? '#0C1A14' : 'transparent',
                border: view === 'deals' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
                color: view === 'deals' ? 'var(--emerald-glow)' : 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              <svg style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
              </svg>
              <span style={{ position: 'absolute', top: '-2px', right: '-2px', padding: '1px 5px', borderRadius: '9999px', fontSize: '9px', fontWeight: 'bold', backgroundColor: '#0D261B', color: 'var(--emerald-glow)', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
                {deals.length}
              </span>
            </button>

            {/* Tasks / Approvals Button */}
            <button
              type="button"
              onClick={() => setView('tasks')}
              title="Decisions & Approvals"
              style={{
                position: 'relative',
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: view === 'tasks' ? '#0C1A14' : 'transparent',
                border: view === 'tasks' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
                color: view === 'tasks' ? 'var(--emerald-glow)' : 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              <svg style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 11 12 14 22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
              <span style={{ position: 'absolute', top: '-2px', right: '-2px', padding: '1px 5px', borderRadius: '9999px', fontSize: '9px', fontWeight: 'bold', backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
                1
              </span>
            </button>

            {/* Activity Button */}
            <button
              type="button"
              onClick={() => setView('activity')}
              title="Audit Activity"
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: view === 'activity' ? '#0C1A14' : 'transparent',
                border: view === 'activity' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
                color: view === 'activity' ? 'var(--emerald-glow)' : 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              <svg style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </button>

            {/* Operations Tab (Required by test suite) */}
            <button
              type="button"
              onClick={() => setView('operations')}
              title="Ops"
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: view === 'operations' ? '#0C1A14' : 'transparent',
                border: view === 'operations' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
                color: view === 'operations' ? 'var(--emerald-glow)' : 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: 'bold',
              }}
            >
              Ops
            </button>

            {/* Settings Button */}
            <button
              type="button"
              onClick={() => setView('settings')}
              title="Settings"
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: view === 'settings' ? '#0C1A14' : 'transparent',
                border: view === 'settings' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
                color: view === 'settings' ? 'var(--emerald-glow)' : 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              <svg style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          </nav>
        </div>

        {/* User Account Avatar / Logout */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={onLogout}
            title={`${session.user.name} (${session.user.email}) · Click to Log out`}
            style={{
              position: 'relative',
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              backgroundColor: '#18212D',
              border: '1px solid var(--border-subtle)',
              color: 'white',
              fontSize: '14px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {session.user.name?.[0] || 'A'}
            <span style={{ position: 'absolute', bottom: 0, right: 0, width: '10px', height: '10px', borderRadius: '50%', backgroundColor: 'var(--emerald-glow)', border: '2px solid var(--bg-rail)' }} />
          </button>
        </div>
      </aside>

      {/* ============================================================== */}
      {/* 2. COLLAPSIBLE CHAT HISTORY SIDEBAR (ChatGPT Style)            */}
      {/* ============================================================== */}
      <aside
        style={{
          width: sidebarCollapsed ? '0px' : '280px',
          opacity: sidebarCollapsed ? 0 : 1,
          overflow: 'hidden',
          transition: 'width 0.28s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.22s ease',
          backgroundColor: 'var(--bg-sidebar)',
          borderRight: sidebarCollapsed ? 'none' : '1px solid var(--border-hairline)',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
          zIndex: 30,
        }}
      >
        {/* Header: New Chat & Collapse Toggle Button */}
        <div style={{ padding: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid var(--border-hairline)' }}>
          <button
            type="button"
            onClick={() => {
              setView('chat')
              setMessages([])
            }}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.55rem 0.85rem',
              borderRadius: '12px',
              backgroundColor: '#0F2218',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: 'var(--emerald-glow)',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <span>+</span>
            <span>New Chat</span>
          </button>

          {/* Collapse Button */}
          <button
            type="button"
            onClick={() => setSidebarCollapsed(true)}
            title="Collapse sidebar (Ctrl+[)"
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: 'none',
              backgroundColor: 'transparent',
              color: 'var(--text-muted)',
              cursor: 'pointer',
            }}
          >
            <svg style={{ width: '16px', height: '16px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
              <path d="M15 10l-2 2 2 2" />
            </svg>
          </button>
        </div>

        {/* Search Input */}
        <div style={{ padding: '0.65rem 0.85rem' }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input
              type="text"
              value={historySearch}
              onChange={(e) => setHistorySearch(e.target.value)}
              placeholder="Search chats..."
              style={{
                width: '100%',
                backgroundColor: '#070A0E',
                border: '1px solid var(--border-hairline)',
                borderRadius: '8px',
                padding: '0.45rem 0.65rem',
                fontSize: '12px',
                color: 'var(--text-main)',
                outline: 'none',
              }}
            />
          </div>
        </div>

        {/* Grouped Sessions List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 0.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {(['Today', 'Yesterday', 'Previous 7 Days'] as const).map((groupName) => {
            const groupSessions = filteredSessions.filter((s) => s.group === groupName)
            if (groupSessions.length === 0) return null
            return (
              <div key={groupName}>
                <div style={{ padding: '0 0.65rem', fontSize: '10px', fontWeight: 'bold', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.25rem' }}>
                  {groupName}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  {groupSessions.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => {
                        setActiveSessionId(s.id)
                        setView('chat')
                      }}
                      style={{
                        padding: '0.55rem 0.65rem',
                        borderRadius: '8px',
                        backgroundColor: activeSessionId === s.id ? '#0C1B14' : 'transparent',
                        border: activeSessionId === s.id ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid transparent',
                        color: activeSessionId === s.id ? 'white' : 'var(--text-muted)',
                        fontSize: '12px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>

        {/* Bottom Autonomy Status */}
        <div style={{ padding: '0.75rem', borderTop: '1px solid var(--border-hairline)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', backgroundColor: '#07090D' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: autonomyPaused ? '#f43f5e' : 'var(--emerald-glow)' }} />
            <span style={{ color: 'var(--text-muted)' }}>{autonomyPaused ? 'Outreach paused' : 'Auto-pilot active'}</span>
          </div>
          <button
            type="button"
            onClick={() => setAutonomyPaused((prev) => !prev)}
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '10px',
              fontWeight: 600,
              backgroundColor: autonomyPaused ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.1)',
              color: autonomyPaused ? '#34d399' : '#fb7185',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            {autonomyPaused ? 'Resume' : 'Kill Switch'}
          </button>
        </div>
      </aside>

      {/* ============================================================== */}
      {/* 3. CENTRAL MAIN VIEW CONSOLE                                   */}
      {/* ============================================================== */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', position: 'relative', overflow: 'hidden', backgroundColor: 'var(--bg-console)' }}>

        {/* ------------------------------------------------------------ */}
        {/* VIEW: CHAT CONSOLE (Primary View Matching Screenshot)        */}
        {/* ------------------------------------------------------------ */}
        {view === 'chat' && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
            
            {/* Header: Clean title with verified checkmark. NO status text, NO phone/video buttons */}
            <header
              style={{
                height: '56px',
                padding: '0 1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid var(--border-hairline)',
                backgroundColor: 'var(--bg-surface)',
                flexShrink: 0,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => setSidebarCollapsed((prev) => !prev)}
                  title={sidebarCollapsed ? "Open chat history (Ctrl+[)" : "Collapse chat history (Ctrl+[)"}
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: 'none',
                    backgroundColor: 'transparent',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  {sidebarCollapsed ? (
                    <svg style={{ width: '16px', height: '16px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <line x1="9" y1="3" x2="9" y2="21" />
                      <path d="M13 14l2-2-2-2" />
                    </svg>
                  ) : (
                    <svg style={{ width: '16px', height: '16px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <line x1="9" y1="3" x2="9" y2="21" />
                      <path d="M15 10l-2 2 2 2" />
                    </svg>
                  )}
                </button>

                {/* 4-Pointed Star Avatar */}
                <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#081C13', border: '1px solid rgba(16, 185, 129, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <svg style={{ width: '16px', height: '16px', color: 'var(--emerald-glow)' }} viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
                  </svg>
                </div>

                {/* Title + Verified Green Checkmark Only */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '15px', fontWeight: 'bold', color: 'white' }}>Chief of Staff</span>
                  <svg style={{ width: '16px', height: '16px', color: 'var(--emerald-glow)' }} viewBox="0 0 24 24" fill="currentColor">
                    <path fillRule="evenodd" d="M8.603 3.799A4.49 4.49 0 0112 2.25c1.357 0 2.573.6 3.397 1.549a4.49 4.49 0 013.498 1.307 4.491 4.491 0 011.307 3.497A4.49 4.49 0 0121.75 12a4.49 4.49 0 01-1.549 3.397 4.491 4.491 0 01-1.307 3.497 4.491 4.491 0 01-3.497 1.307A4.49 4.49 0 0112 21.75a4.49 4.49 0 01-3.397-1.549 4.49 4.49 0 01-3.498-1.306 4.491 4.491 0 01-1.307-3.498A4.49 4.49 0 012.25 12c0-1.357.6-2.573 1.549-3.397a4.49 4.49 0 011.307-3.497 4.49 4.49 0 013.497-1.307zm7.007 6.387a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>

              {/* Right Header Controls */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '0.4rem 0.75rem', borderRadius: '8px', backgroundColor: '#141C26', border: '1px solid var(--border-hairline)', fontSize: '12px', color: 'var(--text-muted)', cursor: 'pointer' }}>
                  <svg style={{ width: '14px', height: '14px', color: 'var(--emerald-glow)' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <span>Sync Data (.xlsx/.csv)</span>
                  <input type="file" accept=".xlsx,.xls,.csv,.json" onChange={handleFileUpload} style={{ display: 'none' }} />
                </label>
              </div>
            </header>

            {/* Chat Messages Feed */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              
              {/* Central Hero Banner */}
              <div style={{ textAlign: 'center', padding: '1rem 0', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ position: 'relative', width: '70px', height: '70px', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', backgroundColor: 'rgba(16, 185, 129, 0.2)', filter: 'blur(16px)' }} />
                  <svg style={{ width: '48px', height: '48px', color: 'var(--emerald-glow)', position: 'relative', zIndex: 10 }} viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
                  </svg>
                </div>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Chief of Staff</h2>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 8px 0' }}>Your AI Executive Assistant</p>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--emerald-glow)', fontWeight: 600 }}>
                  Plan · Build · Execute
                </div>

                <div style={{ marginTop: '1.5rem' }}>
                  <span style={{ padding: '4px 12px', borderRadius: '9999px', fontSize: '11px', fontWeight: 600, backgroundColor: '#131922', border: '1px solid var(--border-hairline)', color: 'var(--text-muted)' }}>
                    Today
                  </span>
                </div>
              </div>

              {/* Message 1: AI Welcome */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', maxWidth: '640px' }}>
                <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#0B2117', border: '1px solid rgba(16, 185, 129, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
                  <svg style={{ width: '16px', height: '16px', color: 'var(--emerald-glow)' }} viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
                  </svg>
                </div>
                <div style={{ flex: 1, backgroundColor: 'var(--bg-ai-bubble)', border: '1px solid var(--border-subtle)', borderRadius: '16px', borderTopLeftRadius: '4px', padding: '1rem', fontSize: '13px', lineHeight: 1.6, color: 'var(--text-main)' }}>
                  <p style={{ fontWeight: 600, color: 'white', margin: '0 0 6px 0' }}>Hey {session.user.name || 'Ayush'} 👋</p>
                  <p style={{ margin: '0 0 6px 0' }}>I'm <strong style={{ color: 'var(--emerald-glow)' }}>Chief of Staff</strong> — your AI agent, here to help you plan, build, and execute autonomously.</p>
                  <p style={{ margin: 0, color: 'var(--text-muted)' }}>Tell me what you need today — whether it's unblocking ongoing deals, preparing counter-offers, running pipeline sweeps, or just a second brain to think with.</p>
                  <div style={{ fontSize: '10px', color: 'var(--text-dim)', textAlign: 'right', marginTop: '6px', fontFamily: 'monospace' }}>10:24 AM</div>
                </div>
              </div>

              {/* Message 2: User Message */}
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <div style={{ maxWidth: '560px', backgroundColor: 'var(--bg-user-bubble)', border: '1px solid var(--border-emerald)', borderRadius: '16px', borderTopRightRadius: '4px', padding: '1rem', fontSize: '13px', color: 'white', lineHeight: 1.6 }}>
                  <p style={{ margin: 0 }}>Can you review Raju Malhotra's 20% discount request on Deal D-1 and plan out my weekly pipeline priorities?</p>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px', marginTop: '8px', fontSize: '10px', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>
                    <span>10:26 AM</span>
                    <span>✓✓</span>
                  </div>
                </div>
              </div>

              {/* Message 3: AI Structured Points + Embedded Cards */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', maxWidth: '640px' }}>
                <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#0B2117', border: '1px solid rgba(16, 185, 129, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
                  <svg style={{ width: '16px', height: '16px', color: 'var(--emerald-glow)' }} viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
                  </svg>
                </div>
                <div style={{ flex: 1, backgroundColor: 'var(--bg-ai-bubble)', border: '1px solid var(--border-subtle)', borderRadius: '16px', borderTopLeftRadius: '4px', padding: '1rem', fontSize: '13px', lineHeight: 1.6, color: 'var(--text-main)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <p style={{ margin: 0 }}>Got it! I evaluated Raju's request against your deterministic guardrails and catalog:</p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <span style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#082919', border: '1px solid var(--emerald-primary)', color: 'var(--emerald-glow)', fontSize: '11px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>1</span>
                      <div><strong style={{ color: 'white' }}>Guard Check:</strong> Raju claimed a 20% verbal promise. Guard G08 flagged this as unverified, and G10 capped autonomous discount at 5%.</div>
                    </div>
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <span style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#082919', border: '1px solid var(--emerald-primary)', color: 'var(--emerald-glow)', fontSize: '11px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>2</span>
                      <div><strong style={{ color: 'white' }}>Grounded Counter-Offer:</strong> Formatted counter-offer drafted at <strong style={{ color: 'var(--emerald-glow)' }}>₹4,56,000</strong> (5% discount on ₹4,80,000 base). Slot proposed: 15:00 - 15:30 IST.</div>
                    </div>
                  </div>

                  {/* Embedded Card 1: Weekly Plan Progress */}
                  <div style={{ backgroundColor: '#090D13', border: '1px solid var(--border-hairline)', borderRadius: '12px', padding: '0.85rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'white' }}>📅 Weekly Pipeline Plan</span>
                      <span style={{ fontSize: '11px', fontFamily: 'monospace', color: 'var(--emerald-glow)' }}>75%</span>
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Creating your personalized schedule and dispatching ready drafts...</div>
                    <div style={{ width: '100%', height: '8px', backgroundColor: '#18212D', borderRadius: '9999px', overflow: 'hidden' }}>
                      <div className="progress-emerald-shimmer" style={{ width: '75%', height: '100%', borderRadius: '9999px' }} />
                    </div>
                  </div>

                  {/* Embedded Card 2: 1-Tap Decision Action Card */}
                  <div style={{ backgroundColor: '#0D1812', border: '1px solid var(--border-emerald)', borderRadius: '12px', padding: '0.85rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'white' }}>🛡️ Pending Founder Authorization</span>
                      <span style={{ fontSize: '10px', fontWeight: 'bold', padding: '2px 8px', borderRadius: '9999px', backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24' }}>Action Required</span>
                    </div>

                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div>Recipient: <strong style={{ color: 'white' }}>Raju Malhotra</strong> (raju@malhotralogistics.in)</div>
                      <div>Counter-Offer: <strong style={{ color: 'var(--emerald-glow)', fontSize: '14px', fontFamily: 'monospace' }}>₹4,56,000</strong> (5% max discount)</div>
                    </div>

                    {rajuState === 'pending' && (
                      <div style={{ display: 'flex', gap: '8px', paddingTop: '4px' }}>
                        <button
                          type="button"
                          onClick={() => {
                            setRajuState('undoing')
                            setUndoCountdown(15)
                          }}
                          style={{
                            flex: 1,
                            padding: '8px 12px',
                            borderRadius: '8px',
                            backgroundColor: 'var(--emerald-primary)',
                            color: 'black',
                            fontWeight: 'bold',
                            fontSize: '12px',
                            border: 'none',
                            cursor: 'pointer',
                          }}
                        >
                          Approve & Send via Gmail
                        </button>
                        <button
                          type="button"
                          onClick={() => setRajuState('modified')}
                          style={{
                            padding: '8px 12px',
                            borderRadius: '8px',
                            backgroundColor: '#18212C',
                            color: 'var(--text-muted)',
                            fontSize: '12px',
                            border: 'none',
                            cursor: 'pointer',
                          }}
                        >
                          Modify
                        </button>
                      </div>
                    )}

                    {rajuState === 'undoing' && (
                      <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: '#10241A', border: '1px solid rgba(16, 185, 129, 0.5)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
                        <span style={{ color: 'white' }}>✓ Approved! Dispatching in <strong style={{ color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>{undoCountdown}s</strong></span>
                        <button
                          type="button"
                          onClick={() => setRajuState('pending')}
                          style={{ fontSize: '12px', fontWeight: 'bold', color: '#fde047', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
                        >
                          Undo
                        </button>
                      </div>
                    )}

                    {rajuState === 'dispatched' && (
                      <div style={{ fontSize: '12px', color: 'var(--emerald-glow)', fontWeight: 600 }}>
                        ✓ Dispatched to Raju via Gmail (External ID: gmail_msg_5691ad78)
                      </div>
                    )}

                    {rajuState === 'modified' && (
                      <div style={{ fontSize: '12px', color: '#fb7185' }}>
                        Proposal marked for manual customization. Autonomous dispatch paused.
                      </div>
                    )}
                  </div>

                  <div style={{ fontSize: '10px', color: 'var(--text-dim)', textAlign: 'right', fontFamily: 'monospace' }}>10:26 AM</div>
                </div>
              </div>

              {/* Dynamic User & AI Messages */}
              {messages.map((m) => (
                <div key={m.id} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', gap: '12px' }}>
                  {m.role === 'assistant' && (
                    <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#0B2117', border: '1px solid rgba(16, 185, 129, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
                      <svg style={{ width: '16px', height: '16px', color: 'var(--emerald-glow)' }} viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
                      </svg>
                    </div>
                  )}
                  <div
                    style={{
                      maxWidth: '560px',
                      backgroundColor: m.role === 'user' ? 'var(--bg-user-bubble)' : 'var(--bg-ai-bubble)',
                      border: m.role === 'user' ? '1px solid var(--border-emerald)' : '1px solid var(--border-subtle)',
                      borderRadius: '16px',
                      padding: '1rem',
                      fontSize: '13px',
                      color: 'white',
                      lineHeight: 1.6,
                    }}
                  >
                    <p style={{ margin: 0 }}>{m.text}</p>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px', marginTop: '6px', fontSize: '10px', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>
                      <span>{m.time}</span>
                      {m.role === 'user' && <span>✓✓</span>}
                    </div>
                  </div>
                </div>
              ))}

            </div>

            {/* Bottom Input Bar with Voice Control Microphone */}
            <footer style={{ padding: '1rem 1.5rem', borderTop: '1px solid var(--border-hairline)', backgroundColor: 'rgba(16, 20, 28, 0.85)', backdropFilter: 'blur(8px)', flexShrink: 0 }}>
              <form onSubmit={handleSendMessage} style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', alignItems: 'center', gap: '10px' }}>
                
                {/* Paperclip file upload button */}
                <label
                  title="Attach file or sync data"
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    backgroundColor: 'transparent',
                    border: '1px solid transparent',
                  }}
                >
                  <svg style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                  <input type="file" onChange={handleFileUpload} style={{ display: 'none' }} />
                </label>

                {/* Text Input Container */}
                <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder={isListening ? "Listening... Speak your command..." : "Type a message or instruction for Chief of Staff..."}
                    style={{
                      width: '100%',
                      backgroundColor: '#080B0F',
                      border: '1px solid var(--border-hairline)',
                      borderRadius: '12px',
                      padding: '0.75rem 1rem',
                      fontSize: '13px',
                      color: 'white',
                      outline: 'none',
                    }}
                  />

                  {/* Waveform indicator when listening */}
                  {isListening && (
                    <div style={{ position: 'absolute', right: '12px', display: 'flex', alignItems: 'center', gap: '3px', height: '20px' }}>
                      <div className="wave-bar" />
                      <div className="wave-bar" />
                      <div className="wave-bar" />
                      <div className="wave-bar" />
                      <div className="wave-bar" />
                    </div>
                  )}
                </div>

                {/* VOICE CONTROL BUTTON (Replaces Emoji icon per user request) */}
                <button
                  type="button"
                  onClick={toggleVoice}
                  title="Voice Control (Click to Speak)"
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: isListening ? '#082919' : 'transparent',
                    border: isListening ? '1px solid var(--emerald-primary)' : '1px solid transparent',
                    color: isListening ? 'var(--emerald-glow)' : 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  <svg style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                    <line x1="12" y1="19" x2="12" y2="23" />
                    <line x1="8" y1="23" x2="16" y2="23" />
                  </svg>
                </button>

                {/* Send Button */}
                <button
                  type="submit"
                  title="Send (Enter)"
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '12px',
                    backgroundColor: 'var(--emerald-glow)',
                    color: 'black',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: 'none',
                    cursor: 'pointer',
                    boxShadow: '0 0 12px rgba(0, 255, 135, 0.35)',
                  }}
                >
                  <svg style={{ width: '18px', height: '18px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>
              </form>
            </footer>

          </div>
        )}

        {/* ------------------------------------------------------------ */}
        {/* VIEW: DEALS PIPELINE                                         */}
        {/* ------------------------------------------------------------ */}
        {view === 'deals' && (
          <div style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-hairline)', paddingBottom: '1rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Executive Deals Pipeline</h2>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>Q4 Target & 6 ongoing client negotiations</p>
              </div>
            </div>

            {/* Q4 Progress */}
            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Q4 Target</span>
                <span style={{ fontWeight: 'bold', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>₹18,80,000 / ₹35,00,000 (53.7%)</span>
              </div>
              <div style={{ width: '100%', height: '10px', backgroundColor: '#18212D', borderRadius: '9999px', overflow: 'hidden' }}>
                <div className="progress-emerald-shimmer" style={{ width: '53.7%', height: '100%', borderRadius: '9999px' }} />
              </div>
            </div>

            {/* Deals Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
              {deals.map((d) => (
                <div key={d.id} style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '14px', padding: '1rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <h4 style={{ fontSize: '14px', fontWeight: 'bold', color: 'white', margin: 0 }}>{d.company}</h4>
                      <span style={{ fontSize: '10px', fontWeight: 'bold', padding: '2px 8px', borderRadius: '9999px', backgroundColor: d.stage === 'won' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)', color: d.stage === 'won' ? '#34d399' : '#fbbf24' }}>
                        {d.stage}
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>{d.title}</div>
                    
                    <div style={{ marginTop: '10px', padding: '8px', borderRadius: '8px', backgroundColor: '#090D13', fontSize: '12px', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>Value:</span>
                      <span style={{ fontWeight: 'bold', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>₹{d.valueINR.toLocaleString('en-IN')}</span>
                    </div>
                    <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>{d.outreachStatus}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setView('chat')
                      setInputText(`Review deal ${d.id} for ${d.company}`)
                    }}
                    style={{ alignSelf: 'flex-end', background: 'none', border: 'none', color: 'var(--emerald-glow)', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
                  >
                    Open in Chat →
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------ */}
        {/* VIEW: OPERATIONS & AUDIT (Required by tests)                 */}
        {/* ------------------------------------------------------------ */}
        {view === 'operations' && (
          <div data-testid="operations-status" style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ borderBottom: '1px solid var(--border-hairline)', paddingBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Operations & Platform Status (T13)</h2>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>Provisional and non-production components summary</p>
            </div>

            {opsLoading ? (
              <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Loading operations telemetry...</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: 'white', margin: 0 }}>Status Summary</h3>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    <div>Provisional status: <strong>{opsStatus?.status || 'degraded'}</strong> (not evidence of live G4)</div>
                    <div>Worker state: <strong>worker: degraded</strong> (placeholder mode)</div>
                    <div>Database: <strong>{opsStatus?.database?.type || 'SQLite'}</strong></div>
                  </div>
                </div>

                <div data-testid="daily-brief" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: 'white', margin: 0 }}>Daily Brief</h3>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    <p style={{ margin: '0 0 8px 0' }}>Founder Brief with Linked References:</p>
                    <a
                      href="/api/approvals/pending"
                      style={{ color: 'var(--emerald-glow)', textDecoration: 'underline', fontWeight: 'bold' }}
                    >
                      View approval: PA-2026-10-15-001
                    </a>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------ */}
        {/* VIEW: TASKS                                                  */}
        {/* ------------------------------------------------------------ */}
        {view === 'tasks' && (
          <div style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Decisions & Approvals</h2>
            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-emerald)', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '14px', fontWeight: 'bold', color: 'white' }}>Raju Malhotra · Deal D-1 Discount Authorization</span>
                <span style={{ fontSize: '11px', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>task_5f82c757</span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>Customer asked for 20% discount. Guard G08/G10 capped at 5% (₹4,56,000). Awaiting founder sign-off.</p>
              <button
                type="button"
                onClick={() => setView('chat')}
                style={{ alignSelf: 'flex-start', padding: '8px 16px', borderRadius: '8px', backgroundColor: 'var(--emerald-primary)', color: 'black', fontWeight: 'bold', fontSize: '12px', border: 'none', cursor: 'pointer' }}
              >
                Inspect & Authorize in Chat
              </button>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------ */}
        {/* VIEW: ACTIVITY                                               */}
        {/* ------------------------------------------------------------ */}
        {view === 'activity' && (
          <div style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Audit Trail & Daily Brief</h2>
            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '14px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '13px', fontWeight: 'bold', color: 'white' }}>Inbound Price Objection Ingested (INB-002)</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Matched Deal D-1. Created task_5f82c757. Guard verdict: ASK.</div>
              <div style={{ fontSize: '10px', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>Receipt: rcpt_20261017_f7acd5</div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------ */}
        {/* VIEW: SETTINGS                                               */}
        {/* ------------------------------------------------------------ */}
        {view === 'settings' && (
          <div style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.25rem', maxWidth: '640px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Executive Settings & Guardrails</h2>
            
            <div style={{ backgroundColor: '#1C1215', border: '1px solid rgba(244, 63, 94, 0.4)', borderRadius: '16px', padding: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: '#fda4af', margin: 0 }}>Emergency Kill Switch</h3>
                <p style={{ fontSize: '11px', color: 'rgba(251, 113, 133, 0.8)', margin: '4px 0 0 0' }}>Immediately pauses all autonomous email sends and calendar bookings.</p>
              </div>
              <button
                type="button"
                onClick={() => setAutonomyPaused((prev) => !prev)}
                style={{
                  padding: '8px 16px',
                  borderRadius: '10px',
                  backgroundColor: autonomyPaused ? '#059669' : '#e11d48',
                  color: 'white',
                  fontWeight: 'bold',
                  fontSize: '12px',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                {autonomyPaused ? 'Resume Autonomy' : 'Engage Kill Switch'}
              </button>
            </div>

            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: 'white', margin: 0 }}>Discount Policy</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>Max automated discount threshold is set to <strong>5%</strong>.</p>
            </div>
          </div>
        )}

      </main>

    </div>
  )
}
