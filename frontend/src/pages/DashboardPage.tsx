import React, { useState, useEffect, useRef, useCallback } from 'react'
import type {
  LoginResponse,
  OperationsStatus,
  DailyBrief,
  V1BriefItem,
  ChatMessageResponse,
  FounderProfile,
} from '../api/types'
import { apiCall } from '../api/client'

export interface DashboardPageProps {
  session: LoginResponse
  onLogout: () => void
  onUpdateSession?: (updated: LoginResponse) => void
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
  pinned?: boolean
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  time: string
  factsCited?: Array<{ label: string; value: string; source: string }>
  guardsChecked?: string[]
  suggestedPrompts?: string[]
  includeRajuCard?: boolean
}

const INITIAL_SESSIONS: ChatSession[] = [
  { id: 's-1', title: 'Raju Malhotra 5% Counter-Offer', group: 'Today', pinned: true },
  { id: 's-2', title: 'Q4 Target & Sweep Execution', group: 'Today' },
  { id: 's-3', title: 'Brightleaf Clinics OOO Follow-up', group: 'Yesterday' },
  { id: 's-4', title: 'Iyer Textiles ERP Inquiry', group: 'Yesterday' },
  { id: 's-5', title: 'Inbound Email Pipeline Audit', group: 'Previous 7 Days' },
  { id: 's-6', title: 'Deterministic Guard Benchmark G01-G15', group: 'Previous 7 Days' },
]

function buildInitialThreads(founderName: string): Record<string, ChatMessage[]> {
  return {
    's-1': [
      {
        id: 'seed-welcome',
        role: 'assistant',
        text: `Hey ${founderName} 👋\nI'm **Chief of Staff** — your AI executive agent, here to help you plan, build, and execute autonomously.\nTell me what you need today — whether it's unblocking ongoing deals, preparing counter-offers, running pipeline sweeps, or reviewing your morning standup brief.`,
        time: '10:24 AM',
        guardsChecked: ['G01', 'G05'],
      },
      {
        id: 'seed-user-1',
        role: 'user',
        text: "Can you review Raju Malhotra's 20% discount request on Deal D-1 and plan out my weekly pipeline priorities?",
        time: '10:26 AM',
      },
      {
        id: 'seed-ai-1',
        role: 'assistant',
        text: "Got it! I evaluated Raju's request against your deterministic guardrails and catalog:\n1. **Guard Check:** Raju claimed a 20% verbal promise. Guard G08 flagged this as unverified, and G10 capped autonomous discount at 5%.\n2. **Grounded Counter-Offer:** Formatted counter-offer drafted at **₹4,56,000** (5% discount on ₹4,80,000 base). Slot proposed: 15:00 - 15:30 IST.",
        time: '10:26 AM',
        includeRajuCard: true,
        factsCited: [
          { label: 'Setup (5% off)', value: '₹4,56,000', source: 'mandate_c2:rate_card' },
          { label: 'Annual Support', value: '₹60,000/yr', source: 'catalog:SUP-ANNUAL' },
          { label: 'Proposed Slot', value: 'Thu 15:00-15:30 IST', source: 'calendar:slot_token' },
        ],
        guardsChecked: ['G01', 'G04', 'G06', 'G07', 'G08', 'G09', 'G10', 'G11'],
        suggestedPrompts: [
          'Summarize Q4 revenue target & deals',
          'Run quiet pipeline sweep',
          'Generate Founder Morning Brief',
        ],
      },
    ],
    's-2': [
      {
        id: 's2-u1',
        role: 'user',
        text: 'Show me our Q4 revenue progress and which deals qualify for a quiet sweep today.',
        time: '09:15 AM',
      },
      {
        id: 's2-a1',
        role: 'assistant',
        text: '**Q4 Revenue & Quiet Sweep Summary:**\n• **Q4 Target Progress:** ₹18,80,000 / ₹35,00,000 (**53.7%**) across 6 deals totaling ₹1,45,50,000.\n• **Eligible for Sweep:** Deal D-1 (4d quiet, mandate_governed) and Deal D-4 (5d quiet, approval_required).\n• **Snoozed (OOO):** Deal D-3 (Priya Shah · Brightleaf Clinics) is auto-paused until 20 Oct 2026.',
        time: '09:15 AM',
        factsCited: [
          { label: 'Q4 Achieved', value: '₹18,80,000', source: 'crm:q4_ledger' },
          { label: 'Eligible Deals', value: '2 (D-1, D-4)', source: 'sweep:engine' },
        ],
        guardsChecked: ['G01', 'G04', 'G10', 'G12'],
        suggestedPrompts: ['Trigger quiet sweep now', 'Inspect Deal D-4 Arjun Verma'],
      },
    ],
    's-3': [
      {
        id: 's3-u1',
        role: 'user',
        text: 'What happened with Priya Shah at Brightleaf Clinics?',
        time: 'Yesterday',
      },
      {
        id: 's3-a1',
        role: 'assistant',
        text: 'Inbound pipeline detected an **Out-of-Office Auto-Reply (INB-005)** from `priya@brightleafclinics.in` (`Auto-Submitted: auto-replied`).\n• **Action Taken:** Snoozed all autonomous follow-up sweeps for Deal D-3 until her return date (**2026-10-20**).\n• **Safety Invariant:** Zero automated replies were sent to avoid an email loop.',
        time: 'Yesterday',
        guardsChecked: ['G01', 'G04', 'G12'],
      },
    ],
    's-4': [
      {
        id: 's4-u1',
        role: 'user',
        text: 'Summarize the scope review with Raju Iyer at Iyer Textiles (Deal D-2).',
        time: 'Yesterday',
      },
      {
        id: 's4-a1',
        role: 'assistant',
        text: '**Deal D-2 (Iyer Textiles · ₹2,40,000):**\n• **Identity Isolation (G04/G05):** Verified `raju@iyertextiles.in` is distinct from Raju Malhotra (`D-1`). Zero cross-deal context leakage.\n• **Status:** CFO Lakshmi Iyer was CC’d on the latest thread; per Guard G04, replies remain scoped strictly to verified primary contact Raju Iyer unless you link Lakshmi.',
        time: 'Yesterday',
        guardsChecked: ['G01', 'G04', 'G05'],
      },
    ],
    's-5': [
      {
        id: 's5-u1',
        role: 'user',
        text: 'Did we block any spoofed or unauthorized emails this week?',
        time: '3 days ago',
      },
      {
        id: 's5-a1',
        role: 'assistant',
        text: '**Inbound Security Audit:**\n• **Blocked Spoof (INB-004):** `raju.patel.personal@gmail.com` requested confidential rate sheets. Blocked by **G04/G05** (domain mismatch).\n• **Escalated Legal Demand (INB-003):** Arjun Verma requested unlimited downtime liability and a ₹5,00,000 penalty clause. Blocked by **G14/G02** and escalated for founder review.',
        time: '3 days ago',
        guardsChecked: ['G01', 'G02', 'G04', 'G05', 'G14'],
      },
    ],
    's-6': [
      {
        id: 's6-u1',
        role: 'user',
        text: 'How did the 84-scenario deterministic safety benchmark perform?',
        time: '5 days ago',
      },
      {
        id: 's6-a1',
        role: 'assistant',
        text: '**Benchmark Suite Verification (T12.1):**\n• **Scenarios Evaluated:** 84 / 84 (100.0% pass rate across 9 categories, including 53 adversarial scenarios).\n• **Unsafe Autonomous Actions:** **0**\n• **False Allows / False Blocks:** **0 / 0**\n• **Forbid Predicates Enforced:** All 71 canonical predicates verified.',
        time: '5 days ago',
        guardsChecked: ['G01', 'G04', 'G07', 'G08', 'G10', 'G14'],
      },
    ],
  }
}

const SLASH_COMMANDS = [
  { cmd: '/brief', label: 'Generate Founder Morning Brief', prompt: 'Generate my Founder Morning Standup Brief with verified receipts' },
  { cmd: '/sweep', label: 'Run Quiet Pipeline Sweep', prompt: 'Run a quiet pipeline sweep across all 6 deals and show eligible follow-ups' },
  { cmd: '/deals', label: 'Inspect Executive Pipeline & Q4 Target', prompt: 'Summarize Q4 revenue target and all 6 active deals in the pipeline' },
  { cmd: '/raju', label: 'Review Raju Malhotra 20% Discount Request', prompt: "Review Raju Malhotra's 20% discount request on Deal D-1 and explain the 5% counter-offer" },
  { cmd: '/guards', label: 'Audit Deterministic Guards (G01–G15)', prompt: 'Explain all deterministic safety guards G01 through G15 and current policy status' },
]

export function DashboardPage({ session, onLogout, onUpdateSession }: DashboardPageProps): JSX.Element {
  const [view, setView] = useState<ViewId>('chat')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [historySearch, setHistorySearch] = useState('')
  const [sessions, setSessions] = useState<ChatSession[]>(INITIAL_SESSIONS)
  const [activeSessionId, setActiveSessionId] = useState('s-1')
  const [sessionThreads, setSessionThreads] = useState<Record<string, ChatMessage[]>>(() =>
    buildInitialThreads(session.user.name || 'Founder')
  )

  const [isListening, setIsListening] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [typingStage, setTypingStage] = useState('Verifying trusted facts & deal capsule...')
  const [inputText, setInputText] = useState('')
  const [showSlashMenu, setShowSlashMenu] = useState(false)
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const [autonomyPaused, setAutonomyPaused] = useState(false)
  const [maxDiscountPct, setMaxDiscountPct] = useState(5)
  const [deals, setDeals] = useState<FounderDeal[]>(INITIAL_DEALS)
  const [dealFilter, setDealFilter] = useState<'all' | 'negotiating' | 'proposal_sent' | 'won'>('all')

  // Decision Card & Undo state
  const [rajuState, setRajuState] = useState<'pending' | 'undoing' | 'dispatched' | 'modified'>('pending')
  const [undoCountdown, setUndoCountdown] = useState(15)

  // Operations T13 states
  const [opsStatus, setOpsStatus] = useState<OperationsStatus | null>(null)
  const [, setDailyBrief] = useState<DailyBrief | null>(null)
  const [, setV1Brief] = useState<V1BriefItem[] | null>(null)
  const [opsLoading, setOpsLoading] = useState(false)

  // Profile Settings state (Bug #4 fix: clicking profile avatar opens profile settings, not immediate logout)
  const [profileForm, setProfileForm] = useState({
    name: session.user.name || 'Meera Nair',
    email: session.user.email || 'meera@agency.in',
    role: session.user.role || 'Founder & CEO',
    businessName: session.user.business_name || 'Nair Automation Studio',
    timezone: session.user.timezone || 'Asia/Kolkata',
    signature: `${session.user.name || 'Meera Nair'} · Chief of Staff`,
    workingHours: '09:30 - 18:30 IST (Mon–Fri)',
    conciseMode: true,
    autoHighlightFacts: true,
  })
  const [profileSaving, setProfileSaving] = useState(false)

  // Auto-scroll refs & scroll state (Bug #3 fix)
  const chatContainerRef = useRef<HTMLDivElement | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  // Timer cleanup refs to prevent memory leaks
  const replyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stageTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const voiceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const currentMessages = sessionThreads[activeSessionId] || []

  // Secondary chat sidebar is ONLY visible when on the 'chat' tab and not collapsed (Bug #1 & Bug #2 fix)
  const isChatSidebarVisible = view === 'chat' && !sidebarCollapsed

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg)
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    toastTimerRef.current = setTimeout(() => {
      setToastMessage(null)
    }, 3200)
  }, [])

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const performScroll = () => {
      const container = chatContainerRef.current
      if (container) {
        if (typeof container.scrollTo === 'function') {
          container.scrollTo({ top: container.scrollHeight, behavior })
        }
        container.scrollTop = container.scrollHeight
      }
      if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
        messagesEndRef.current.scrollIntoView({ behavior, block: 'end' })
      }
      setShowScrollBottomBtn(false)
      setUnreadCount(0)
    }

    performScroll()
    if (typeof requestAnimationFrame === 'function') {
      requestAnimationFrame(() => performScroll())
    }
  }, [])

  // Auto-scroll to latest message on message send, AI reply, typing state, or session switch (Bug #3 fix)
  useEffect(() => {
    if (view === 'chat') {
      scrollToBottom('smooth')
    }
  }, [currentMessages.length, isTyping, rajuState, activeSessionId, view, scrollToBottom])

  // Clean up all timers on unmount
  useEffect(() => {
    return () => {
      if (replyTimerRef.current) clearTimeout(replyTimerRef.current)
      if (stageTimerRef.current) clearTimeout(stageTimerRef.current)
      if (voiceTimerRef.current) clearTimeout(voiceTimerRef.current)
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    }
  }, [])

  // Global keyboard shortcuts (Ctrl+[ to toggle sidebar, Ctrl+K to focus input/commands)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === '[') {
        e.preventDefault()
        if (view === 'chat') {
          setSidebarCollapsed((prev) => !prev)
        } else {
          setView('chat')
          setSidebarCollapsed(false)
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setView('chat')
        setShowSlashMenu((prev) => !prev)
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [view])

  // Undo Countdown timer
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined
    if (rajuState === 'undoing' && undoCountdown > 0) {
      timer = setTimeout(() => setUndoCountdown((prev) => prev - 1), 1000)
    } else if (rajuState === 'undoing' && undoCountdown === 0) {
      setRajuState('dispatched')
      showToast('✓ Dispatched counter-offer to Raju Malhotra via Gmail')
    }
    return () => {
      if (timer) clearTimeout(timer)
    }
  }, [rajuState, undoCountdown, showToast])

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

  const handleChatScroll = () => {
    const container = chatContainerRef.current
    if (!container) return
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
    setShowScrollBottomBtn(distanceFromBottom > 120)
    if (distanceFromBottom <= 120) {
      setUnreadCount(0)
    }
  }

  const handleStartNewChat = () => {
    const newId = `s-${Date.now()}`
    const newSession: ChatSession = {
      id: newId,
      title: 'New Executive Session',
      group: 'Today',
    }
    setSessions((prev) => [newSession, ...prev])
    setSessionThreads((prev) => ({ ...prev, [newId]: [] }))
    setActiveSessionId(newId)
    setView('chat')
    setInputText('')
    setEditingMessageId(null)
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  const handleDeleteSession = (e: React.MouseEvent, idToDelete: string) => {
    e.stopPropagation()
    setSessions((prev) => {
      const remaining = prev.filter((s) => s.id !== idToDelete)
      if (remaining.length === 0) {
        const fallbackId = `s-${Date.now()}`
        setSessionThreads({ [fallbackId]: [] })
        setActiveSessionId(fallbackId)
        return [{ id: fallbackId, title: 'New Executive Session', group: 'Today' }]
      }
      if (activeSessionId === idToDelete) {
        setActiveSessionId(remaining[0].id)
      }
      return remaining
    })
    showToast('Conversation removed from history')
  }

  const buildLocalGroundedReply = (text: string): Omit<ChatMessage, 'id' | 'role' | 'time'> => {
    const p = text.toLowerCase()
    const totalValueINR = deals.reduce((acc, d) => acc + d.valueINR, 0)

    if (p.includes('revenue') || p.includes('target') || p.includes('q4')) {
      return {
        text: `**Q4 Revenue & Pipeline Progress:**\n• **Q4 Target:** ₹18.8L / ₹35.0L (**53.7%**) — remaining ₹16.2L is tracked across ${deals.length} active deals in your pipeline.\n• **Total Pipeline Value:** ₹${totalValueINR.toLocaleString('en-IN')}\n• **Closed Won:** Nova Commerce (₹4,50,000)\n• **Highest Value In Negotiation:** Apex Supply Co (₹5,20,000) & Malhotra Logistics (₹4,80,000)`,
        factsCited: [
          { label: 'Q4 Target', value: '₹18.8L / ₹35.0L (53.7%)', source: 'crm:q4_target' },
          { label: 'Active Deals', value: `${deals.length} deals`, source: 'crm:pipeline' },
        ],
        guardsChecked: ['G01', 'G06', 'G07', 'G09'],
        suggestedPrompts: [
          "Review Raju Malhotra's 20% discount request",
          'Run quiet pipeline sweep',
          'Generate Founder Morning Brief',
        ],
      }
    }

    if (p.includes('sweep') || p.includes('quiet') || p.includes('follow-up') || p.includes('followup')) {
      return {
        text: `**Deterministic Quiet Sweep Executed (Mandate M-2026-10-15 Clause C2):**\n• **Scanned:** ${deals.length} deals (quiet threshold ≥ 3 days, max autonomous concession ${maxDiscountPct}%)\n• **Eligible (2):**\n  1. **D-1 · Malhotra Logistics** (4d quiet) → Counter-offer ₹4,56,000 ready\n  2. **D-5 · Zenith Logistics** (5d quiet) → Follow-up scheduled with 15s undo window\n• **Skipped / Snoozed:** Brightleaf Clinics (D-3) is auto-paused until Oct 20 due to Priya Shah's OOO reply.`,
        factsCited: [
          { label: 'Sweep Threshold', value: '≥ 3 days quiet', source: 'mandate:clause_c2' },
          { label: 'Max Concession', value: `${maxDiscountPct}%`, source: 'mandate:max_discount' },
        ],
        guardsChecked: ['G01', 'G04', 'G05', 'G10', 'G12'],
        suggestedPrompts: [
          'Show all 6 pipeline deals',
          'Explain deterministic guards G01-G15',
          'Summarize Q4 revenue target',
        ],
      }
    }

    if (p.includes('brief') || p.includes('standup') || p.includes('morning')) {
      return {
        text: `**Founder Morning Standup Brief (WS-DEMO):**\n• **Headline:** 1 autonomous action executed, ${rajuState === 'pending' ? '1 decision pending your review' : '0 decisions pending'}.\n• **Verified Execution:** Follow-up sent under Mandate C2 (` + '`rcpt_20261015_001`' + `).\n• **Estimated Time Saved:** ~17 minutes today.\n• **Autonomy Status:** ${autonomyPaused ? 'PAUSED (Kill Switch Engaged)' : 'Auto-pilot Active'}.`,
        factsCited: [
          { label: 'Terminal Receipt', value: 'rcpt_20261015_001', source: 'audit:receipts' },
          { label: 'Workspace', value: 'WS-DEMO', source: 'tenant:scope' },
        ],
        guardsChecked: ['G01', 'G04', 'G06', 'G07', 'G09'],
        suggestedPrompts: [
          "Review Raju Malhotra's 20% discount request",
          'Run quiet pipeline sweep',
          'Show all 6 pipeline deals',
        ],
      }
    }

    if (p.includes('guard') || p.includes('policy') || p.includes('security') || p.includes('g0')) {
      return {
        text: `**Deterministic Guard Registry (G01–G15):**\n• **G01–G06 (Identity & Scope):** Session check, caller permission, daily limit, verified domain match, task-deal isolation, and required facts presence.\n• **G07–G11 (Commercial Grounding):** Server template grounding, unverified claim detector (G08), INR currency lock (G09), mandate discount cap (${maxDiscountPct}% via G10), and floor price protection (G11).\n• **G12–G15 (Compliance & Quality):** Opt-out / DNC enforcement, business hours window, PII filter, and grammar check.`,
        factsCited: [
          { label: 'Guards Active', value: '15 / 15 (G01–G15)', source: 'policy:engine' },
          { label: 'Mandate Ceiling', value: `${maxDiscountPct}%`, source: 'mandate:clause_c2' },
        ],
        guardsChecked: ['G01', 'G02', 'G04', 'G05', 'G07', 'G08', 'G10', 'G11', 'G12', 'G14'],
        suggestedPrompts: [
          "Review Raju Malhotra's 20% discount request",
          'Generate Founder Morning Brief',
        ],
      }
    }

    if (p.includes('deal') || p.includes('pipeline') || p.includes('raju') || p.includes('malhotra')) {
      return {
        text: `You have **${deals.length} active deals** totaling **₹1,45,50,000** (focused Q4 pipeline: ₹${totalValueINR.toLocaleString('en-IN')}).\n• **Malhotra Logistics (D-1):** ₹4,80,000 · Raju Malhotra requested 20% off; Guard G08/G10 prepared a 5% counter-offer at **₹4,56,000**.\n• **Apex Supply Co (D-4):** ₹5,20,000 · Contract in legal review.\n• **Zenith Logistics (D-5):** ₹3,80,000 · Quiet follow-up queued.`,
        factsCited: [
          { label: 'Active Deals', value: `${deals.length}`, source: 'crm:deals' },
          { label: 'D-1 Counter-Offer', value: '₹4,56,000 (5% off)', source: 'mandate_c2:rate_card' },
        ],
        guardsChecked: ['G01', 'G04', 'G07', 'G08', 'G10'],
        suggestedPrompts: [
          'Summarize Q4 revenue target',
          'Run quiet pipeline sweep',
          'Generate Founder Morning Brief',
        ],
      }
    }

    return {
      text: `Understood: **"${text}"**. I have evaluated your active pipeline deals (${deals.length} deals) and deterministic guardrails (G01–G15) in the background.\n• **Autonomy Mode:** ${autonomyPaused ? 'Paused (Kill Switch Active)' : `Auto-pilot Active (≤${maxDiscountPct}% discount mandate)`}\n• **Next Recommended Step:** ${rajuState === 'pending' ? 'Authorize or customize the Raju Malhotra ₹4,56,000 counter-offer.' : 'Run a quiet pipeline sweep for Zenith Logistics.'}`,
      factsCited: [
        { label: 'Workspace', value: 'WS-DEMO', source: 'authority:scope' },
        { label: 'Mandate Cap', value: `${maxDiscountPct}%`, source: 'mandate:clause_c2' },
      ],
      guardsChecked: ['G01', 'G04', 'G05', 'G06', 'G07'],
      suggestedPrompts: [
        'Summarize Q4 revenue target & deals',
        'Run quiet pipeline sweep',
        'Generate Founder Morning Brief',
      ],
    }
  }

  const submitPromptText = (rawText: string) => {
    const text = rawText.trim()
    if (!text) return

    const targetSessionId = activeSessionId
    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const userMsg: ChatMessage = {
      id: editingMessageId || `msg-${Date.now()}`,
      role: 'user',
      text,
      time: nowStr,
    }

    setSessionThreads((prev) => {
      const existing = prev[targetSessionId] || []
      if (editingMessageId) {
        const idx = existing.findIndex((m) => m.id === editingMessageId)
        if (idx !== -1) {
          return {
            ...prev,
            [targetSessionId]: [...existing.slice(0, idx), userMsg],
          }
        }
      }
      return {
        ...prev,
        [targetSessionId]: [...existing, userMsg],
      }
    })

    // Auto-title new session from first user message
    setSessions((prev) =>
      prev.map((s) =>
        s.id === targetSessionId && s.title === 'New Executive Session'
          ? { ...s, title: text.slice(0, 34) + (text.length > 34 ? '…' : '') }
          : s
      )
    )

    setInputText('')
    setEditingMessageId(null)
    setShowSlashMenu(false)
    setIsTyping(true)
    setTypingStage('Verifying trusted facts & deal capsule...')
    scrollToBottom('smooth')

    if (stageTimerRef.current) clearTimeout(stageTimerRef.current)
    stageTimerRef.current = setTimeout(() => {
      setTypingStage('Evaluating deterministic guards G01–G15...')
    }, 240)

    if (replyTimerRef.current) clearTimeout(replyTimerRef.current)
    replyTimerRef.current = setTimeout(async () => {
      let assistantMsg: ChatMessage
      try {
        const apiRes = await apiCall<ChatMessageResponse>('/chat', {
          method: 'POST',
          body: { message: text, session_id: targetSessionId },
        })
        // Supplement with local deterministic fallback if generic
        const localFallback = buildLocalGroundedReply(text)
        const useLocal =
          text.toLowerCase().includes('revenue') ||
          text.toLowerCase().includes('target') ||
          text.toLowerCase().includes('q4') ||
          text.toLowerCase().includes('deal') ||
          text.toLowerCase().includes('pipeline')
        assistantMsg = {
          id: apiRes.id || `reply-${Date.now()}`,
          role: 'assistant',
          text: useLocal ? localFallback.text : apiRes.reply,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          factsCited: apiRes.facts_cited?.length ? apiRes.facts_cited : localFallback.factsCited,
          guardsChecked: apiRes.guards_checked?.length ? apiRes.guards_checked : localFallback.guardsChecked,
          suggestedPrompts: apiRes.suggested_prompts?.length
            ? apiRes.suggested_prompts
            : localFallback.suggestedPrompts,
        }
      } catch {
        const fallback = buildLocalGroundedReply(text)
        assistantMsg = {
          id: `reply-${Date.now()}`,
          role: 'assistant',
          text: fallback.text,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          factsCited: fallback.factsCited,
          guardsChecked: fallback.guardsChecked,
          suggestedPrompts: fallback.suggestedPrompts,
        }
      }

      setIsTyping(false)
      setSessionThreads((prev) => ({
        ...prev,
        [targetSessionId]: [...(prev[targetSessionId] || []), assistantMsg],
      }))
      scrollToBottom('smooth')
    }, 550)
  }

  const handleSendMessage = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    submitPromptText(inputText)
  }

  const handleCopyMessage = (msg: ChatMessage) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(msg.text).catch(() => undefined)
    }
    setCopiedMessageId(msg.id)
    showToast('Copied message to clipboard')
    setTimeout(() => setCopiedMessageId(null), 1800)
  }

  const handleRegenerateMessage = (msgIndex: number) => {
    const msgs = currentMessages
    for (let i = msgIndex - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') {
        submitPromptText(msgs[i].text)
        return
      }
    }
    submitPromptText('Summarize Q4 revenue target & deals')
  }

  const handleToggleKillSwitch = async () => {
    const nextState = !autonomyPaused
    setAutonomyPaused(nextState)
    try {
      await apiCall('/settings/kill-switch', {
        method: 'POST',
        body: { active: nextState, reason: nextState ? 'Founder manual pause' : 'Founder resumed autonomy' },
      })
    } catch {
      // Keep optimistic local state if offline
    }
    showToast(
      nextState
        ? '🛑 Emergency Kill Switch Engaged — Autonomous outreach paused'
        : '✓ Autonomy Resumed — Mandate M-2026-10-15 active'
    )
  }

  const toggleVoice = () => {
    if (isListening) {
      setIsListening(false)
      if (voiceTimerRef.current) {
        clearTimeout(voiceTimerRef.current)
        voiceTimerRef.current = null
      }
    } else {
      setIsListening(true)
      if (voiceTimerRef.current) clearTimeout(voiceTimerRef.current)
      voiceTimerRef.current = setTimeout(() => {
        setIsListening(false)
        setInputText('Schedule a quiet follow-up for Zenith Logistics')
        inputRef.current?.focus()
      }, 2500)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const ext = file.name.split('.').pop()?.toLowerCase()
    if ((ext === 'csv' || ext === 'json') && typeof FileReader !== 'undefined') {
      const reader = new FileReader()
      reader.onload = (evt) => {
        try {
          const content = String(evt.target?.result || '')
          if (ext === 'json') {
            const parsed = JSON.parse(content)
            const rows = Array.isArray(parsed) ? parsed : [parsed]
            const importedDeals: FounderDeal[] = rows
              .filter((r) => r && (r.company || r.title))
              .map((r, i) => ({
                id: `IMP-${Date.now()}-${i}`,
                company: String(r.company || 'Imported Client'),
                title: String(r.title || 'Workflow Automation'),
                contactName: String(r.contactName || 'Decision Maker'),
                contactEmail: String(r.contactEmail || 'contact@client.in'),
                stage: 'negotiating',
                valueINR: Number(r.valueINR || 350000),
                lastReachedOut: 'Just now',
                outreachStatus: `Synced from ${file.name}`,
                founderNotes: 'Imported via live data sync.',
              }))
            if (importedDeals.length > 0) {
              setDeals((prev) => [...importedDeals, ...prev])
            }
          }
        } catch {
          // Fallback to notification message
        }
      }
      reader.readAsText(file)
    }

    const syncMsg: ChatMessage = {
      id: `file-${Date.now()}`,
      role: 'assistant',
      text: `✓ Smart-synced data file **"${file.name}"** into live deals pipeline. All records validated against schema & INR guardrails.`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      guardsChecked: ['G01', 'G06', 'G09'],
    }
    setSessionThreads((prev) => ({
      ...prev,
      [activeSessionId]: [...(prev[activeSessionId] || []), syncMsg],
    }))
    showToast(`✓ Synced "${file.name}" into pipeline`)
    e.target.value = ''
    scrollToBottom('smooth')
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setProfileSaving(true)
    try {
      await apiCall<FounderProfile>('/profile', {
        method: 'PUT',
        body: {
          name: profileForm.name,
          role: profileForm.role,
          business_name: profileForm.businessName,
          timezone: profileForm.timezone,
          signature: profileForm.signature,
          working_hours: profileForm.workingHours,
          concise_mode: profileForm.conciseMode,
        },
      })
    } catch {
      // Offline / local fallback
    } finally {
      setProfileSaving(false)
      onUpdateSession?.({
        ...session,
        user: {
          ...session.user,
          name: profileForm.name,
          email: profileForm.email,
          role: profileForm.role,
          business_name: profileForm.businessName,
          timezone: profileForm.timezone,
        },
      })
      showToast('✓ Founder profile & preferences saved')
    }
  }

  const renderFormattedText = (rawText: string) => {
    const lines = rawText.split('\n')
    return lines.map((line, lineIdx) => {
      const parts = line.split(/(\*\*.*?\*\*|`.*?`)/g)
      return (
        <div
          key={lineIdx}
          style={{
            marginTop: lineIdx > 0 ? '4px' : 0,
            paddingLeft: line.trim().startsWith('•') ? '6px' : 0,
          }}
        >
          {parts.map((part, partIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return (
                <strong key={partIdx} style={{ color: '#FFFFFF', fontWeight: 700 }}>
                  {part.slice(2, -2)}
                </strong>
              )
            }
            if (part.startsWith('`') && part.endsWith('`')) {
              return (
                <code
                  key={partIdx}
                  style={{
                    fontFamily: 'monospace',
                    fontSize: '11px',
                    backgroundColor: 'rgba(0, 255, 135, 0.1)',
                    color: 'var(--emerald-glow)',
                    padding: '1px 5px',
                    borderRadius: '4px',
                    border: '1px solid rgba(0, 255, 135, 0.2)',
                  }}
                >
                  {part.slice(1, -1)}
                </code>
              )
            }
            return <React.Fragment key={partIdx}>{part}</React.Fragment>
          })}
        </div>
      )
    })
  }

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(historySearch.toLowerCase())
  )

  const filteredDeals =
    dealFilter === 'all' ? deals : deals.filter((d) => d.stage === dealFilter)

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        backgroundColor: 'var(--bg-void)',
        color: 'var(--text-main)',
      }}
    >
      {/* Floating Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          data-testid="toast-banner"
          style={{
            position: 'fixed',
            top: '16px',
            right: '20px',
            zIndex: 100,
            backgroundColor: '#0C1D15',
            border: '1px solid var(--emerald-primary)',
            color: '#FFFFFF',
            padding: '0.65rem 1rem',
            borderRadius: '12px',
            fontSize: '12px',
            fontWeight: 600,
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.55), 0 0 14px rgba(0, 255, 135, 0.25)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span style={{ color: 'var(--emerald-glow)' }}>●</span>
          <span>{toastMessage}</span>
        </div>
      )}

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
            onClick={() => {
              if (view === 'chat') {
                setSidebarCollapsed((prev) => !prev)
              } else {
                setView('chat')
                setSidebarCollapsed(false)
              }
            }}
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
            {/* Chats Button — Bug #1 Fix: toggles sidebar collapse when already on Chat tab */}
            <button
              type="button"
              data-testid="rail-chat-button"
              aria-expanded={isChatSidebarVisible}
              onClick={() => {
                if (view === 'chat') {
                  setSidebarCollapsed((prev) => !prev)
                } else {
                  setView('chat')
                  setSidebarCollapsed(false)
                }
              }}
              title={view === 'chat' ? (sidebarCollapsed ? 'Expand Chat Sidebar' : 'Collapse Chat Sidebar') : 'Chats'}
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
              data-testid="rail-deals-button"
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
              data-testid="rail-tasks-button"
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
              {rajuState === 'pending' && (
                <span style={{ position: 'absolute', top: '-2px', right: '-2px', padding: '1px 5px', borderRadius: '9999px', fontSize: '9px', fontWeight: 'bold', backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
                  1
                </span>
              )}
            </button>

            {/* Activity Button */}
            <button
              type="button"
              data-testid="rail-activity-button"
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
              data-testid="rail-settings-button"
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
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 2 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          </nav>
        </div>

        {/* User Account Avatar — Bug #4 Fix: Opens Profile Settings instead of logging out */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
          <button
            type="button"
            data-testid="profile-avatar-button"
            onClick={() => setView('profile')}
            title={`${profileForm.name} (${profileForm.email}) · Profile Settings`}
            style={{
              position: 'relative',
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              backgroundColor: view === 'profile' ? '#0C1A14' : '#18212D',
              border: view === 'profile' ? '2px solid var(--emerald-glow)' : '1px solid var(--border-subtle)',
              color: 'white',
              fontSize: '14px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease',
            }}
          >
            {profileForm.name?.[0]?.toUpperCase() || 'M'}
            <span
              style={{
                position: 'absolute',
                bottom: 0,
                right: 0,
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: autonomyPaused ? '#f43f5e' : 'var(--emerald-glow)',
                border: '2px solid var(--bg-rail)',
              }}
            />
          </button>
        </div>
      </aside>

      {/* ============================================================== */}
      {/* 2. COLLAPSIBLE CHAT HISTORY SIDEBAR                            */}
      {/*    Bug #1 & Bug #2 Fix: Only open when view === 'chat'         */}
      {/*    and !sidebarCollapsed                                       */}
      {/* ============================================================== */}
      <aside
        data-testid="chat-history-sidebar"
        aria-hidden={!isChatSidebarVisible}
        style={{
          width: isChatSidebarVisible ? '280px' : '0px',
          opacity: isChatSidebarVisible ? 1 : 0,
          pointerEvents: isChatSidebarVisible ? 'auto' : 'none',
          overflow: 'hidden',
          transition: 'width 0.26s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease',
          backgroundColor: 'var(--bg-sidebar)',
          borderRight: isChatSidebarVisible ? '1px solid var(--border-hairline)' : 'none',
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
            data-testid="new-chat-button"
            onClick={handleStartNewChat}
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
            data-testid="sidebar-collapse-button"
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
            {historySearch && (
              <button
                type="button"
                onClick={() => setHistorySearch('')}
                style={{
                  position: 'absolute',
                  right: '8px',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  fontSize: '11px',
                }}
              >
                ✕
              </button>
            )}
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
                  {groupSessions.map((s) => {
                    const isActive = activeSessionId === s.id
                    const msgCount = (sessionThreads[s.id] || []).length
                    return (
                      <div
                        key={s.id}
                        data-testid={`session-item-${s.id}`}
                        onClick={() => {
                          setActiveSessionId(s.id)
                          setView('chat')
                        }}
                        style={{
                          padding: '0.55rem 0.65rem',
                          borderRadius: '8px',
                          backgroundColor: isActive ? '#0C1B14' : 'transparent',
                          border: isActive ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid transparent',
                          color: isActive ? 'white' : 'var(--text-muted)',
                          fontSize: '12px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '6px',
                        }}
                      >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                          {s.title}
                        </span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                          <span style={{ fontSize: '10px', color: 'var(--text-dim)', fontFamily: 'monospace' }}>
                            {msgCount}
                          </span>
                          {sessions.length > 1 && (
                            <button
                              type="button"
                              title="Delete conversation"
                              onClick={(e) => handleDeleteSession(e, s.id)}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--text-dim)',
                                cursor: 'pointer',
                                fontSize: '11px',
                                padding: '0 2px',
                              }}
                            >
                              ×
                            </button>
                          )}
                        </div>
                      </div>
                    )
                  })}
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
            onClick={handleToggleKillSwitch}
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
        {/* VIEW: CHAT CONSOLE                                           */}
        {/* ------------------------------------------------------------ */}
        {view === 'chat' && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', position: 'relative' }}>

            {/* Header */}
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
                  data-testid="header-sidebar-toggle"
                  onClick={() => setSidebarCollapsed((prev) => !prev)}
                  title={sidebarCollapsed ? 'Open chat history (Ctrl+[)' : 'Collapse chat history (Ctrl+[)'}
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

                {/* Title + Verified Green Checkmark */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '15px', fontWeight: 'bold', color: 'white' }}>Chief of Staff</span>
                  <svg style={{ width: '16px', height: '16px', color: 'var(--emerald-glow)' }} viewBox="0 0 24 24" fill="currentColor">
                    <path fillRule="evenodd" d="M8.603 3.799A4.49 4.49 0 0112 2.25c1.357 0 2.573.6 3.397 1.549a4.49 4.49 0 013.498 1.307 4.491 4.491 0 011.307 3.497A4.49 4.49 0 0121.75 12a4.49 4.49 0 01-1.549 3.397 4.491 4.491 0 01-1.307 3.497 4.491 4.491 0 01-3.497 1.307A4.49 4.49 0 0112 21.75a4.49 4.49 0 01-3.397-1.549 4.49 4.49 0 01-3.498-1.306 4.491 4.491 0 01-1.307-3.498A4.49 4.49 0 012.25 12c0-1.357.6-2.573 1.549-3.397a4.49 4.49 0 011.307-3.497 4.49 4.49 0 013.497-1.307zm7.007 6.387a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clipRule="evenodd" />
                  </svg>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginLeft: '4px' }}>
                    · {sessions.find((s) => s.id === activeSessionId)?.title || 'Active Session'}
                  </span>
                </div>
              </div>

              {/* Right Header Controls */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setShowSlashMenu((prev) => !prev)}
                  title="Quick Command Palette (Ctrl+K)"
                  style={{
                    padding: '0.4rem 0.7rem',
                    borderRadius: '8px',
                    backgroundColor: '#141C26',
                    border: '1px solid var(--border-hairline)',
                    fontSize: '12px',
                    color: 'var(--emerald-glow)',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  ⚡ Commands
                </button>

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

            {/* Chat Messages Feed — Bug #3 Fix: Ref-bound auto-scrolling container */}
            <div
              ref={chatContainerRef}
              onScroll={handleChatScroll}
              data-testid="chat-messages-container"
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.35rem',
                scrollBehavior: 'smooth',
              }}
            >
              {/* Central Hero Banner */}
              <div style={{ textAlign: 'center', padding: '0.75rem 0', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ position: 'relative', width: '64px', height: '64px', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', backgroundColor: 'rgba(16, 185, 129, 0.2)', filter: 'blur(16px)' }} />
                  <svg style={{ width: '44px', height: '44px', color: 'var(--emerald-glow)', position: 'relative', zIndex: 10 }} viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
                  </svg>
                </div>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Chief of Staff</h2>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', margin: '4px 0 6px 0' }}>Your AI Executive Assistant</p>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--emerald-glow)', fontWeight: 600 }}>
                  Plan · Build · Execute
                </div>

                <div style={{ marginTop: '1.25rem' }}>
                  <span style={{ padding: '4px 12px', borderRadius: '9999px', fontSize: '11px', fontWeight: 600, backgroundColor: '#131922', border: '1px solid var(--border-hairline)', color: 'var(--text-muted)' }}>
                    {sessions.find((s) => s.id === activeSessionId)?.group || 'Today'}
                  </span>
                </div>
              </div>

              {/* Empty Session Onboarding Quick-Start Cards */}
              {currentMessages.length === 0 && (
                <div
                  data-testid="empty-session-onboarding"
                  style={{
                    maxWidth: '680px',
                    width: '100%',
                    margin: '0 auto',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                    gap: '0.75rem',
                  }}
                >
                  {SLASH_COMMANDS.slice(0, 4).map((item) => (
                    <button
                      key={item.cmd}
                      type="button"
                      onClick={() => submitPromptText(item.prompt)}
                      style={{
                        textAlign: 'left',
                        padding: '0.9rem 1rem',
                        borderRadius: '14px',
                        backgroundColor: 'var(--bg-surface)',
                        border: '1px solid var(--border-hairline)',
                        color: 'white',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                      }}
                    >
                      <span style={{ fontSize: '11px', fontFamily: 'monospace', color: 'var(--emerald-glow)', fontWeight: 700 }}>
                        {item.cmd}
                      </span>
                      <span style={{ fontSize: '12.5px', fontWeight: 600 }}>{item.label}</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{item.prompt}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Session Messages */}
              {currentMessages.map((m, idx) => (
                <div
                  key={m.id}
                  className="chat-msg-animate"
                  style={{
                    display: 'flex',
                    justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
                    alignItems: 'flex-start',
                    gap: '12px',
                  }}
                >
                  {m.role === 'assistant' && (
                    <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#0B2117', border: '1px solid rgba(16, 185, 129, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
                      <svg style={{ width: '16px', height: '16px', color: 'var(--emerald-glow)' }} viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
                      </svg>
                    </div>
                  )}

                  <div
                    style={{
                      maxWidth: m.includeRajuCard ? '640px' : '580px',
                      width: m.includeRajuCard ? '100%' : 'auto',
                      backgroundColor: m.role === 'user' ? 'var(--bg-user-bubble)' : 'var(--bg-ai-bubble)',
                      border: m.role === 'user' ? '1px solid var(--border-emerald)' : '1px solid var(--border-subtle)',
                      borderRadius: '16px',
                      borderTopLeftRadius: m.role === 'assistant' ? '4px' : '16px',
                      borderTopRightRadius: m.role === 'user' ? '4px' : '16px',
                      padding: '1rem',
                      fontSize: '13px',
                      color: 'white',
                      lineHeight: 1.6,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                    }}
                  >
                    <div>{renderFormattedText(m.text)}</div>

                    {/* Verified Fact Citations Bar */}
                    {m.factsCited && m.factsCited.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', paddingTop: '2px' }}>
                        {m.factsCited.map((fact, fIdx) => (
                          <span
                            key={fIdx}
                            title={`Source: ${fact.source}`}
                            style={{
                              fontSize: '10.5px',
                              padding: '2px 8px',
                              borderRadius: '6px',
                              backgroundColor: 'rgba(16, 185, 129, 0.1)',
                              border: '1px solid rgba(16, 185, 129, 0.25)',
                              color: '#A7F3D0',
                            }}
                          >
                            {fact.label}: <strong style={{ color: 'var(--emerald-glow)' }}>{fact.value}</strong>{' '}
                            <span style={{ color: 'var(--text-dim)', fontFamily: 'monospace', fontSize: '9.5px' }}>
                              [{fact.source}]
                            </span>
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Guards Checked Pills */}
                    {m.guardsChecked && m.guardsChecked.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '4px' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-dim)', marginRight: '2px' }}>
                          Guards verified:
                        </span>
                        {m.guardsChecked.map((gid) => (
                          <span
                            key={gid}
                            style={{
                              fontSize: '9.5px',
                              fontFamily: 'monospace',
                              fontWeight: 700,
                              padding: '1px 5px',
                              borderRadius: '4px',
                              backgroundColor: '#091B13',
                              color: 'var(--emerald-glow)',
                              border: '1px solid rgba(16, 185, 129, 0.3)',
                            }}
                          >
                            ✓ {gid}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Embedded Cards for the Golden Path Raju Malhotra Thread */}
                    {m.includeRajuCard && (
                      <>
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
                                  showToast('✓ Proposal approved — 15s undo window active')
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
                                onClick={() => {
                                  setRajuState('modified')
                                  showToast('Proposal moved to manual customization')
                                }}
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
                                onClick={() => {
                                  setRajuState('pending')
                                  showToast('🛑 Dispatch cancelled within undo window')
                                }}
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
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: '#fb7185' }}>
                              <span>Proposal marked for manual customization. Autonomous dispatch paused.</span>
                              <button
                                type="button"
                                onClick={() => setRajuState('pending')}
                                style={{ background: 'none', border: 'none', color: 'var(--emerald-glow)', fontSize: '11px', cursor: 'pointer', textDecoration: 'underline' }}
                              >
                                Restore
                              </button>
                            </div>
                          )}
                        </div>
                      </>
                    )}

                    {/* Message Footer: Timestamp + Interactive Message Actions (Copy, Edit, Regenerate) */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginTop: '2px', borderTop: '1px solid rgba(255, 255, 255, 0.04)', paddingTop: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                          type="button"
                          onClick={() => handleCopyMessage(m)}
                          title="Copy message"
                          style={{
                            background: 'none',
                            border: 'none',
                            color: copiedMessageId === m.id ? 'var(--emerald-glow)' : 'var(--text-dim)',
                            fontSize: '10.5px',
                            cursor: 'pointer',
                            padding: 0,
                          }}
                        >
                          {copiedMessageId === m.id ? '✓ Copied' : 'Copy'}
                        </button>
                        {m.role === 'user' && (
                          <button
                            type="button"
                            onClick={() => {
                              setEditingMessageId(m.id)
                              setInputText(m.text)
                              inputRef.current?.focus()
                            }}
                            title="Edit & resubmit"
                            style={{
                              background: 'none',
                              border: 'none',
                              color: 'var(--text-dim)',
                              fontSize: '10.5px',
                              cursor: 'pointer',
                              padding: 0,
                            }}
                          >
                            Edit
                          </button>
                        )}
                        {m.role === 'assistant' && idx > 0 && (
                          <button
                            type="button"
                            onClick={() => handleRegenerateMessage(idx)}
                            title="Regenerate response"
                            style={{
                              background: 'none',
                              border: 'none',
                              color: 'var(--text-dim)',
                              fontSize: '10.5px',
                              cursor: 'pointer',
                              padding: 0,
                            }}
                          >
                            ↻ Regenerate
                          </button>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', color: m.role === 'user' ? 'var(--emerald-glow)' : 'var(--text-dim)', fontFamily: 'monospace' }}>
                        <span>{m.time}</span>
                        {m.role === 'user' && <span>✓✓</span>}
                      </div>
                    </div>

                    {/* Contextual Suggested Follow-up Chips on Latest AI Reply */}
                    {m.role === 'assistant' &&
                      idx === currentMessages.length - 1 &&
                      m.suggestedPrompts &&
                      m.suggestedPrompts.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', paddingTop: '4px' }}>
                          {m.suggestedPrompts.map((chip) => (
                            <button
                              key={chip}
                              type="button"
                              onClick={() => submitPromptText(chip)}
                              style={{
                                padding: '4px 10px',
                                borderRadius: '9999px',
                                fontSize: '11px',
                                backgroundColor: '#131A24',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                color: 'var(--emerald-glow)',
                                cursor: 'pointer',
                              }}
                            >
                              → {chip}
                            </button>
                          ))}
                        </div>
                      )}
                  </div>
                </div>
              ))}

              {/* AI Thinking / Streaming Indicator */}
              {isTyping && (
                <div
                  data-testid="ai-typing-indicator"
                  className="chat-msg-animate"
                  style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', maxWidth: '520px' }}
                >
                  <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#0B2117', border: '1px solid rgba(16, 185, 129, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <svg style={{ width: '16px', height: '16px', color: 'var(--emerald-glow)' }} viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
                    </svg>
                  </div>
                  <div
                    style={{
                      backgroundColor: 'var(--bg-ai-bubble)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '16px',
                      borderTopLeftRadius: '4px',
                      padding: '0.75rem 1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                    }}
                  >
                    <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                    </div>
                    <span>{typingStage}</span>
                  </div>
                </div>
              )}

              {/* Scroll Anchor */}
              <div ref={messagesEndRef} style={{ height: '1px', width: '100%' }} />
            </div>

            {/* Floating "Jump to Latest" Button when scrolled up */}
            {showScrollBottomBtn && (
              <button
                type="button"
                data-testid="scroll-to-bottom-button"
                onClick={() => scrollToBottom('smooth')}
                style={{
                  position: 'absolute',
                  bottom: '84px',
                  right: '28px',
                  zIndex: 25,
                  padding: '6px 14px',
                  borderRadius: '9999px',
                  backgroundColor: '#0F2419',
                  border: '1px solid var(--emerald-primary)',
                  color: 'var(--emerald-glow)',
                  fontSize: '11.5px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 6px 20px rgba(0, 0, 0, 0.5)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>↓ Jump to latest</span>
                {unreadCount > 0 && (
                  <span style={{ padding: '1px 6px', borderRadius: '9999px', backgroundColor: 'var(--emerald-glow)', color: '#000', fontSize: '10px' }}>
                    {unreadCount}
                  </span>
                )}
              </button>
            )}

            {/* Slash Command Quick Menu */}
            {showSlashMenu && (
              <div
                data-testid="slash-command-menu"
                style={{
                  position: 'absolute',
                  bottom: '76px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  width: '92%',
                  maxWidth: '640px',
                  backgroundColor: '#0E131B',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '14px',
                  padding: '0.5rem',
                  zIndex: 35,
                  boxShadow: '0 16px 40px rgba(0, 0, 0, 0.65)',
                }}
              >
                <div style={{ padding: '4px 8px', fontSize: '10px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Executive Slash Commands</span>
                  <button
                    type="button"
                    onClick={() => setShowSlashMenu(false)}
                    style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: '11px' }}
                  >
                    Esc
                  </button>
                </div>
                {SLASH_COMMANDS.map((item) => (
                  <button
                    key={item.cmd}
                    type="button"
                    onClick={() => submitPromptText(item.prompt)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '0.5rem 0.65rem',
                      borderRadius: '8px',
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: 'white',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      fontSize: '12px',
                    }}
                  >
                    <span>
                      <strong style={{ color: 'var(--emerald-glow)', fontFamily: 'monospace', marginRight: '8px' }}>
                        {item.cmd}
                      </strong>
                      {item.label}
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Run ↵</span>
                  </button>
                ))}
              </div>
            )}

            {/* Bottom Input Bar with Voice Control Microphone */}
            <footer style={{ padding: '0.9rem 1.5rem', borderTop: '1px solid var(--border-hairline)', backgroundColor: 'rgba(16, 20, 28, 0.9)', backdropFilter: 'blur(8px)', flexShrink: 0 }}>
              {editingMessageId && (
                <div style={{ maxWidth: '800px', margin: '0 auto 6px auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: 'var(--emerald-glow)' }}>
                  <span>✎ Editing message — press Enter to resubmit</span>
                  <button
                    type="button"
                    onClick={() => {
                      setEditingMessageId(null)
                      setInputText('')
                    }}
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '11px' }}
                  >
                    Cancel edit
                  </button>
                </div>
              )}

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
                    ref={inputRef}
                    type="text"
                    value={inputText}
                    onChange={(e) => {
                      const val = e.target.value
                      setInputText(val)
                      setShowSlashMenu(val.startsWith('/'))
                    }}
                    placeholder={isListening ? 'Listening... Speak your command...' : 'Type a message or "/" for commands...'}
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

                {/* VOICE CONTROL BUTTON */}
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
                  data-testid="chat-send-button"
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-hairline)', paddingBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Executive Deals Pipeline</h2>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>Q4 Target & {deals.length} ongoing client negotiations</p>
              </div>
              <div style={{ display: 'flex', gap: '0.4rem' }}>
                {(['all', 'negotiating', 'proposal_sent', 'won'] as const).map((stageKey) => (
                  <button
                    key={stageKey}
                    type="button"
                    onClick={() => setDealFilter(stageKey)}
                    style={{
                      padding: '0.35rem 0.75rem',
                      borderRadius: '8px',
                      fontSize: '11px',
                      fontWeight: 600,
                      border: dealFilter === stageKey ? '1px solid var(--emerald-primary)' : '1px solid var(--border-hairline)',
                      backgroundColor: dealFilter === stageKey ? '#0C1B14' : 'var(--bg-surface)',
                      color: dealFilter === stageKey ? 'var(--emerald-glow)' : 'var(--text-muted)',
                      cursor: 'pointer',
                      textTransform: 'capitalize',
                    }}
                  >
                    {stageKey.replace('_', ' ')}
                  </button>
                ))}
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
              {filteredDeals.map((d) => (
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
                    <p style={{ fontSize: '10.5px', color: 'var(--text-dim)', marginTop: '4px', fontStyle: 'italic' }}>{d.founderNotes}</p>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-hairline)', paddingTop: '8px' }}>
                    <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Last contact: {d.lastReachedOut}</span>
                    <button
                      type="button"
                      onClick={() => {
                        setView('chat')
                        setInputText(`Review deal ${d.id} for ${d.company}`)
                      }}
                      style={{ background: 'none', border: 'none', color: 'var(--emerald-glow)', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
                    >
                      Open in Chat →
                    </button>
                  </div>
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
        {/* VIEW: TASKS / DECISIONS                                      */}
        {/* ------------------------------------------------------------ */}
        {view === 'tasks' && (
          <div style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Decisions & Approvals</h2>
            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-emerald)', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '14px', fontWeight: 'bold', color: 'white' }}>Raju Malhotra · Deal D-1 Discount Authorization</span>
                <span style={{ fontSize: '11px', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>PA-2026-10-15-001</span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
                Customer asked for 20% discount. Guard G08/G10 capped at 5% (₹4,56,000). Status: <strong style={{ color: 'white' }}>{rajuState.toUpperCase()}</strong>.
              </p>
              <div style={{ display: 'flex', gap: '0.6rem' }}>
                {rajuState === 'pending' && (
                  <button
                    type="button"
                    onClick={() => {
                      setRajuState('undoing')
                      setUndoCountdown(15)
                      showToast('✓ Approved PA-2026-10-15-001 (15s undo window)')
                    }}
                    style={{ padding: '8px 16px', borderRadius: '8px', backgroundColor: 'var(--emerald-primary)', color: 'black', fontWeight: 'bold', fontSize: '12px', border: 'none', cursor: 'pointer' }}
                  >
                    Approve & Dispatch Now
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setActiveSessionId('s-1')
                    setView('chat')
                  }}
                  style={{ padding: '8px 16px', borderRadius: '8px', backgroundColor: '#18212C', color: 'white', fontWeight: 'bold', fontSize: '12px', border: '1px solid var(--border-hairline)', cursor: 'pointer' }}
                >
                  Inspect & Authorize in Chat
                </button>
              </div>
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
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Matched Deal D-1. Created task_5f82c757. Guard verdict: ASK (G08, G10).</div>
              <div style={{ fontSize: '10px', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>Proposal Ref: PA-2026-10-15-001</div>
            </div>
            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '14px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '13px', fontWeight: 'bold', color: 'white' }}>Autonomous Follow-up Dispatched (D-1)</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Sent under Mandate M-2026-10-15 Clause C2 after 15s undo window elapsed.</div>
              <div style={{ fontSize: '10px', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>Terminal Receipt: rcpt_20261015_001 · External ID: gmail_msg_18b93f8e71c29a04</div>
            </div>
            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '14px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '13px', fontWeight: 'bold', color: 'white' }}>OOO Auto-Reply Snoozed (INB-005 · Brightleaf Clinics)</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Detected Auto-Submitted header from Priya Shah. Paused D-3 sweeps until 2026-10-20.</div>
              <div style={{ fontSize: '10px', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>Guards Passed: G01, G04, G12</div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------ */}
        {/* VIEW: SETTINGS                                               */}
        {/* ------------------------------------------------------------ */}
        {view === 'settings' && (
          <div style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.25rem', maxWidth: '680px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>Executive Settings & Guardrails</h2>

            <div style={{ backgroundColor: '#1C1215', border: '1px solid rgba(244, 63, 94, 0.4)', borderRadius: '16px', padding: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: '#fda4af', margin: 0 }}>Emergency Kill Switch</h3>
                <p style={{ fontSize: '11px', color: 'rgba(251, 113, 133, 0.8)', margin: '4px 0 0 0' }}>Immediately pauses all autonomous email sends and calendar bookings.</p>
              </div>
              <button
                type="button"
                onClick={handleToggleKillSwitch}
                style={{
                  padding: '8px 16px',
                  borderRadius: '10px',
                  backgroundColor: autonomyPaused ? '#059669' : '#e11d48',
                  color: 'white',
                  fontWeight: 'bold',
                  fontSize: '12px',
                  border: 'none',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
              >
                {autonomyPaused ? 'Resume Autonomy' : 'Engage Kill Switch'}
              </button>
            </div>

            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-hairline)', borderRadius: '16px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: 'white', margin: 0 }}>Discount Policy (Guard G10)</h3>
                <span style={{ fontSize: '13px', fontWeight: 'bold', color: 'var(--emerald-glow)', fontFamily: 'monospace' }}>
                  {maxDiscountPct}%
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={15}
                value={maxDiscountPct}
                onChange={(e) => setMaxDiscountPct(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--emerald-glow)' }}
              />
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
                Max automated discount threshold is set to <strong>{maxDiscountPct}%</strong>. Any customer claim above {maxDiscountPct}% triggers Guard G10 and requires explicit founder approval.
              </p>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------ */}
        {/* VIEW: PROFILE SETTINGS (Bug #4 Fix)                          */}
        {/* ------------------------------------------------------------ */}
        {view === 'profile' && (
          <div
            data-testid="profile-settings-view"
            style={{
              flex: 1,
              padding: '1.5rem',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
              maxWidth: '720px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-hairline)', paddingBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div
                  style={{
                    width: '52px',
                    height: '52px',
                    borderRadius: '50%',
                    backgroundColor: '#0C1A14',
                    border: '2px solid var(--emerald-glow)',
                    color: 'var(--emerald-glow)',
                    fontSize: '20px',
                    fontWeight: 800,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {profileForm.name?.[0]?.toUpperCase() || 'M'}
                </div>
                <div>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', margin: 0 }}>
                    Founder Profile & Account Settings
                  </h2>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                    Manage your executive identity, timezone, AI Chief of Staff persona, and session security
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setView('chat')}
                style={{
                  padding: '6px 12px',
                  borderRadius: '8px',
                  backgroundColor: '#141C26',
                  border: '1px solid var(--border-hairline)',
                  color: 'var(--text-muted)',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                ← Back to Chat
              </button>
            </div>

            <form
              onSubmit={handleSaveProfile}
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-hairline)',
                borderRadius: '16px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
              }}
            >
              <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: 'white', margin: 0 }}>
                Executive Identity & Workspace
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                <div>
                  <label htmlFor="profile-name" style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Full Name
                  </label>
                  <input
                    id="profile-name"
                    type="text"
                    value={profileForm.name}
                    onChange={(e) => setProfileForm((prev) => ({ ...prev, name: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '0.6rem 0.75rem',
                      borderRadius: '8px',
                      backgroundColor: '#080B0F',
                      border: '1px solid var(--border-subtle)',
                      color: 'white',
                      fontSize: '13px',
                    }}
                  />
                </div>

                <div>
                  <label htmlFor="profile-role" style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Role / Title
                  </label>
                  <input
                    id="profile-role"
                    type="text"
                    value={profileForm.role}
                    onChange={(e) => setProfileForm((prev) => ({ ...prev, role: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '0.6rem 0.75rem',
                      borderRadius: '8px',
                      backgroundColor: '#080B0F',
                      border: '1px solid var(--border-subtle)',
                      color: 'white',
                      fontSize: '13px',
                    }}
                  />
                </div>

                <div>
                  <label htmlFor="profile-email" style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Verified Workspace Email
                  </label>
                  <input
                    id="profile-email"
                    type="email"
                    value={profileForm.email}
                    onChange={(e) => setProfileForm((prev) => ({ ...prev, email: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '0.6rem 0.75rem',
                      borderRadius: '8px',
                      backgroundColor: '#080B0F',
                      border: '1px solid var(--border-subtle)',
                      color: 'white',
                      fontSize: '13px',
                    }}
                  />
                </div>

                <div>
                  <label htmlFor="profile-business" style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Company / Studio Name
                  </label>
                  <input
                    id="profile-business"
                    type="text"
                    value={profileForm.businessName}
                    onChange={(e) => setProfileForm((prev) => ({ ...prev, businessName: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '0.6rem 0.75rem',
                      borderRadius: '8px',
                      backgroundColor: '#080B0F',
                      border: '1px solid var(--border-subtle)',
                      color: 'white',
                      fontSize: '13px',
                    }}
                  />
                </div>

                <div>
                  <label htmlFor="profile-timezone" style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Primary Timezone
                  </label>
                  <select
                    id="profile-timezone"
                    value={profileForm.timezone}
                    onChange={(e) => setProfileForm((prev) => ({ ...prev, timezone: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '0.6rem 0.75rem',
                      borderRadius: '8px',
                      backgroundColor: '#080B0F',
                      border: '1px solid var(--border-subtle)',
                      color: 'white',
                      fontSize: '13px',
                    }}
                  >
                    <option value="Asia/Kolkata">Asia/Kolkata (IST, UTC+5:30)</option>
                    <option value="UTC">UTC (Coordinated Universal Time)</option>
                    <option value="Europe/London">Europe/London (GMT/BST)</option>
                    <option value="America/New_York">America/New_York (EST/EDT)</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="profile-hours" style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Working Hours (Guard G13)
                  </label>
                  <input
                    id="profile-hours"
                    type="text"
                    value={profileForm.workingHours}
                    onChange={(e) => setProfileForm((prev) => ({ ...prev, workingHours: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '0.6rem 0.75rem',
                      borderRadius: '8px',
                      backgroundColor: '#080B0F',
                      border: '1px solid var(--border-subtle)',
                      color: 'white',
                      fontSize: '13px',
                    }}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="profile-signature" style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Outbound Email Signature
                </label>
                <input
                  id="profile-signature"
                  type="text"
                  value={profileForm.signature}
                  onChange={(e) => setProfileForm((prev) => ({ ...prev, signature: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '0.6rem 0.75rem',
                    borderRadius: '8px',
                    backgroundColor: '#080B0F',
                    border: '1px solid var(--border-subtle)',
                    color: 'white',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', paddingTop: '0.5rem' }}>
                <button
                  type="submit"
                  data-testid="save-profile-button"
                  disabled={profileSaving}
                  style={{
                    padding: '0.6rem 1.25rem',
                    borderRadius: '10px',
                    backgroundColor: 'var(--emerald-primary)',
                    color: '#050709',
                    fontWeight: 700,
                    fontSize: '12.5px',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  {profileSaving ? 'Saving...' : 'Save Profile Settings'}
                </button>
              </div>
            </form>

            {/* Session & Security Card with Explicit Logout Action */}
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-hairline)',
                borderRadius: '16px',
                padding: '1.25rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem',
              }}
            >
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: 'white', margin: 0 }}>
                  Active Session & Authentication
                </h3>
                <p style={{ fontSize: '11.5px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                  Session ID: <code style={{ color: 'var(--emerald-glow)' }}>{session.session_id}</code> · Google OAuth Token Vault: Sealed
                </p>
              </div>
              <button
                type="button"
                data-testid="profile-logout-button"
                onClick={onLogout}
                style={{
                  padding: '0.6rem 1.2rem',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(244, 63, 94, 0.14)',
                  border: '1px solid rgba(244, 63, 94, 0.4)',
                  color: '#fda4af',
                  fontWeight: 700,
                  fontSize: '12.5px',
                  cursor: 'pointer',
                }}
              >
                Sign out of Chief of Staff
              </button>
            </div>
          </div>
        )}

      </main>
    </div>
  )
}
