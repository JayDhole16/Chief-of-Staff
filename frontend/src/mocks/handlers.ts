/**
 * MSW request handlers: login, session, activity, approvals, receipts, pipeline, settings.
 * Only enabled in development (VITE_USE_MSW=true).
 * Never shipped to production.
 */

import { http, HttpResponse, delay } from 'msw'
import type {
  LoginRequest,
  LoginResponse,
  SessionResponse,
  ActivityFeedResponse,
  ApprovalsResponse,
  PipelineResponse,
  ProposedAction,
  ApprovalDecisionRequest,
  ApprovalDecisionResponse,
  ActionReceipt,
  CancelActionResponse,
  SystemSettings,
  OperationsStatus,
  V1DailyBrief,
} from '../api/types'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

// Mock state
const mockSessions = new Map<string, { userId: string; email: string; name: string }>([
  ['test_session_123', { userId: 'user_123', email: 'test@example.com', name: 'Meera Nair' }],
])
let sessionCounter = 0

// Beat 3 Golden Path Proposal
export const MOCK_PROPOSAL_GOLDEN_HASH =
  '8f9b7c62d4e13589a12c8b74619d08e5c3e06182a93746c59b2184d8f1e6b392'

let pendingProposal: ProposedAction = {
  ref: 'PA-2026-10-15-001',
  kind: 'email',
  deal_id: 'deal_raju_01',
  deal_title: 'Acme Warehouse Automation',
  contact_name: 'Raju Patel',
  contact_email: 'raju@patel-warehousing.in',
  subject: 'Re: Automation Project Proposal & Scope',
  rendered_body: `Dear Raju,

Thank you for your response regarding our proposal.

Regarding your query on pricing: we are pleased to confirm a 5% discount on the one-time implementation fee, bringing the setup cost to ₹4,56,000 (standard ₹4,80,000). For annual ongoing maintenance, our SUP-ANNUAL tier is ₹60,000/year, and our standard cloud connector remains ₹15,000/month.

I would be delighted to walk you through the architecture this Thursday at 15:00 - 15:30 IST.

Best regards,
Meera Nair
Chief of Staff`,
  rendered_hash: MOCK_PROPOSAL_GOLDEN_HASH,
  facts_used: [
    { key: 'setup_cost', label: 'Setup (5% discount applied)', value: '₹4,56,000', source: 'mandate_c2:rate_card' },
    { key: 'discount_pct', label: 'Discount', value: '5%', source: 'mandate_c2:max_discount' },
    { key: 'support_annual', label: 'Annual Support', value: '₹60,000', source: 'catalog:SUP-ANNUAL' },
    { key: 'monthly_maintenance', label: 'Monthly Maintenance', value: '₹15,000', source: 'catalog:CONN-MONTHLY' },
    { key: 'meeting_slot', label: 'Proposed Slot', value: '15:00 - 15:30 IST', source: 'calendar:slot_token' },
  ],
  risk_flags: [
    {
      code: 'G08',
      severity: 'warning',
      reason: 'Customer referenced verbal 20% discount on call. Exceeds mandate limit (5%). Requires founder review.',
      customer_claim: 'promised 20% on a call',
    },
  ],
  policy_verdict: 'ASK',
  policy_reasons: [
    'Customer claim "promised 20% on a call" is unverified',
    'Founder review required before sending counter-offer',
  ],
  created_at: new Date(Date.now() - 600000).toISOString(),
  expires_at: new Date(Date.now() + 3000000).toISOString(),
  status: 'pending',
}

let killSwitchState = false

export const handlers = [
  // POST /auth/login
  http.post(`${API_BASE}/auth/login`, async (info) => {
    const { email, password } = (await info.request.json()) as LoginRequest

    if (!email || !password) {
      return HttpResponse.json(
        { error: { code: 422, message: 'Email and password required' } },
        { status: 422 }
      )
    }

    if (password.length < 6) {
      return HttpResponse.json(
        { error: { code: 422, message: 'Invalid credentials' } },
        { status: 422 }
      )
    }

    await delay(100)

    const sessionId = `session_${++sessionCounter}`
    mockSessions.set(sessionId, {
      userId: 'user_123',
      email,
      name: email.split('@')[0],
    })

    const response: LoginResponse = {
      session_id: sessionId,
      user: {
        id: 'user_123',
        email,
        name: email.split('@')[0],
      },
    }

    return HttpResponse.json(response, { status: 200 })
  }),

  // GET /session
  http.get(`${API_BASE}/session`, (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')

    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json(
        { error: { code: 401, message: 'Unauthorized' } },
        { status: 401 }
      )
    }

    const session = mockSessions.get(sessionId)!

    const response: SessionResponse = {
      session_id: sessionId,
      user: {
        id: session.userId,
        email: session.email,
        name: session.name,
      },
    }

    return HttpResponse.json(response, { status: 200 })
  }),

  // GET /approvals/pending (T09.4)
  http.get(`${API_BASE}/approvals/pending`, (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')

    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json(
        { error: { code: 401, message: 'Unauthorized' } },
        { status: 401 }
      )
    }

    const hasPending = pendingProposal.status === 'pending'
    const approvalsList = hasPending
      ? [
          {
            id: pendingProposal.ref,
            ref: pendingProposal.ref,
            title: `${pendingProposal.deal_title} counter-offer`,
            description: `Requires approval: ₹4,56,000 setup with 5% discount`,
            state: 'pending' as const,
            created_at: pendingProposal.created_at,
            expires_at: pendingProposal.expires_at,
            proposal: pendingProposal,
          },
        ]
      : []

    const response: ApprovalsResponse = {
      approvals: approvalsList,
      count: approvalsList.length,
    }

    return HttpResponse.json(response, { status: 200 })
  }),

  // POST /approvals/:ref/decision (T09.4 - Hash-bound decision)
  http.post(`${API_BASE}/approvals/:ref/decision`, async (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')
    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json({ error: { code: 401, message: 'Unauthorized' } }, { status: 401 })
    }

    const { ref } = info.params
    const body = (await info.request.json()) as ApprovalDecisionRequest

    // Check rendered_hash binding: MUST match backend exact hash!
    if (body.rendered_hash !== pendingProposal.rendered_hash) {
      return HttpResponse.json(
        {
          error: {
            code: 409,
            message:
              'Proposal version mismatch (rendered_hash mismatch) or proposal has expired. Please reload.',
          },
        },
        { status: 409 }
      )
    }

    if (body.decision === 'approve') {
      pendingProposal.status = 'approved'
      const executeAfter = new Date(Date.now() + 5000).toISOString() // 5-second undo window
      const response: ApprovalDecisionResponse = {
        ref: String(ref),
        status: 'approved',
        rendered_hash: body.rendered_hash,
        execute_after: executeAfter,
        message: 'Proposal approved. Dispatched with 5s undo window.',
      }
      return HttpResponse.json(response, { status: 200 })
    } else {
      pendingProposal.status = 'rejected'
      const response: ApprovalDecisionResponse = {
        ref: String(ref),
        status: 'rejected',
        rendered_hash: body.rendered_hash,
        message: `Proposal rejected by founder: ${body.rejection_reason || 'No reason specified'}`,
      }
      return HttpResponse.json(response, { status: 200 })
    }
  }),

  // GET /activity (T09.5)
  http.get(`${API_BASE}/activity`, (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')

    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json(
        { error: { code: 401, message: 'Unauthorized' } },
        { status: 401 }
      )
    }

    const response: ActivityFeedResponse = {
      events: [
        {
          id: 'evt_raju_prop',
          timestamp: new Date().toISOString(),
          type: 'proposed',
          title: 'Proposed follow-up to Raju Patel',
          description: 'Counter-offer ₹4,56,000 + ₹60,000/yr support drafted. Pending founder approval.',
          user_id: 'agent_cos',
          action_ref: 'PA-2026-10-15-001',
          rendered_hash: MOCK_PROPOSAL_GOLDEN_HASH,
        },
        {
          id: 'evt_d1_executed',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          type: 'execution',
          title: 'D-1 Follow-up Sent',
          description: 'Follow-up email autonomously sent to Acme Warehousing under Mandate M-1.',
          user_id: 'worker_executor',
          action_ref: 'act_d1_01',
          receipt_id: 'rcpt_20261015_001',
        },
        {
          id: 'evt_priya_ooo',
          timestamp: new Date(Date.now() - 7200000).toISOString(),
          type: 'approval',
          title: 'Priya Shah OOO Auto-Reply Received',
          description: 'Out-of-office detected. Autonomous follow-up paused until 20 Oct.',
          user_id: 'agent_inbound',
        },
      ],
      count: 3,
    }

    return HttpResponse.json(response, { status: 200 })
  }),

  // POST /actions/:ref/cancel (T09.5 - Undo Timer)
  http.post(`${API_BASE}/actions/:ref/cancel`, (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')
    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json({ error: { code: 401, message: 'Unauthorized' } }, { status: 401 })
    }

    const { ref } = info.params

    const response: CancelActionResponse = {
      ref: String(ref),
      status: 'cancelled',
      cancelled_at: new Date().toISOString(),
      receipt_id: `rcpt_cancel_${Date.now()}`,
      message: `Action ${ref} cancelled successfully within undo window.`,
    }

    return HttpResponse.json(response, { status: 200 })
  }),

  // GET /receipts/:receiptId (T09.5)
  http.get(`${API_BASE}/receipts/:receiptId`, (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')
    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json({ error: { code: 401, message: 'Unauthorized' } }, { status: 401 })
    }

    const { receiptId } = info.params

    const receipt: ActionReceipt = {
      receipt_id: String(receiptId),
      action_ref: 'act_d1_01',
      action_kind: 'email',
      status: 'executed',
      authority_clause: 'Mandate M-2026-10-15 Clause C2: Follow-up quiet deals with <=5% discount',
      recipient_email: 'raju@patel-warehousing.in',
      external_id: 'gmail_msg_18b93f8e71c29a04',
      rendered_hash: '9a7e6b54c3d2e1f089123456789abcdef0123456789abcdef0123456789abcde',
      checks_passed: ['G01', 'G04', 'G05', 'G06', 'G07', 'G09', 'G10', 'G11'],
      facts_used: [
        { key: 'deal_value', label: 'Deal Value', value: '₹12,50,000', source: 'crm:deal_d1' },
        { key: 'contact_name', label: 'Contact', value: 'Raju Patel', source: 'crm:contact_raju' },
        { key: 'mandate_clause', label: 'Max Discount', value: '5%', source: 'mandate:C2' },
      ],
      executed_at: new Date(Date.now() - 3600000).toISOString(),
      undo_window_seconds: 15,
      timeline: [
        { timestamp: new Date(Date.now() - 3615000).toISOString(), event: 'Mandate sweep proposed action' },
        { timestamp: new Date(Date.now() - 3600000).toISOString(), event: 'Undo window elapsed; dispatched' },
        { timestamp: new Date(Date.now() - 3598000).toISOString(), event: 'Gmail API confirmed send' },
      ],
    }

    return HttpResponse.json(receipt, { status: 200 })
  }),

  // GET /pipeline/deals (T09.5 - Beat 0 6 deals)
  http.get(`${API_BASE}/pipeline/deals`, (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')

    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json(
        { error: { code: 401, message: 'Unauthorized' } },
        { status: 401 }
      )
    }

    const response: PipelineResponse = {
      deals: [
        {
          id: 'D-1',
          title: 'Acme Warehousing Automation',
          contact_name: 'Raju Patel',
          contact_email: 'raju@patel-warehousing.in',
          stage: 'negotiation',
          value_paise: 125000000, // ₹12,50,000
          created_at: new Date(Date.now() - 864000000).toISOString(),
          days_quiet: 3,
          is_quiet: true,
          last_interaction: new Date(Date.now() - 259200000).toISOString(),
        },
        {
          id: 'D-2',
          title: 'Apex Logistics Cloud Connector',
          contact_name: 'Sunil Mehta',
          contact_email: 'sunil@apexlogistics.in',
          stage: 'lead',
          value_paise: 250000000, // ₹25,00,000
          created_at: new Date(Date.now() - 172800000).toISOString(),
          days_quiet: 0,
          is_quiet: false,
          last_interaction: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          id: 'D-3',
          title: 'QuickShip Solutions Inventory Sync',
          contact_name: 'Priya Shah',
          contact_email: 'priya@quickship.in',
          stage: 'negotiation',
          value_paise: 180000000, // ₹18,00,000
          created_at: new Date(Date.now() - 604800000).toISOString(),
          days_quiet: 4,
          is_quiet: true,
          last_interaction: new Date(Date.now() - 345600000).toISOString(),
        },
        {
          id: 'D-4',
          title: 'BlueDart Regional Franchise',
          contact_name: 'Arjun Verma',
          contact_email: 'arjun@bluedart-franchise.in',
          stage: 'negotiation',
          value_paise: 300000000, // ₹30,00,000
          created_at: new Date(Date.now() - 259200000).toISOString(),
          days_quiet: 1,
          is_quiet: true,
          last_interaction: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          id: 'D-5',
          title: 'ExpressCargo Route Automation',
          contact_name: 'Deepak Roy',
          contact_email: 'deepak@expresscargo.in',
          stage: 'active',
          value_paise: 150000000, // ₹15,00,000
          created_at: new Date(Date.now() - 345600000).toISOString(),
          days_quiet: 0,
          is_quiet: false,
          last_interaction: new Date(Date.now() - 43200000).toISOString(),
        },
        {
          id: 'D-6',
          title: 'MegaFreight ERP Integration',
          contact_name: 'Kavita Nair',
          contact_email: 'kavita@megafreight.in',
          stage: 'won',
          value_paise: 450000000, // ₹45,00,000
          created_at: new Date(Date.now() - 1209600000).toISOString(),
          days_quiet: 0,
          is_quiet: false,
          last_interaction: new Date(Date.now() - 172800000).toISOString(),
        },
      ],
      count: 6,
    }

    return HttpResponse.json(response, { status: 200 })
  }),

  // GET /settings (T09.5)
  http.get(`${API_BASE}/settings`, (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')
    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json({ error: { code: 401, message: 'Unauthorized' } }, { status: 401 })
    }

    const response: SystemSettings = {
      founder: {
        name: 'Meera Nair',
        email: 'meera@agency.in',
        business_name: 'Nair Automation Labs',
        timezone: 'Asia/Kolkata',
      },
      google_account: {
        connected: true,
        email: 'meera@agency.in',
        token_status: 'valid',
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        scopes: [
          'https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/calendar.events',
        ],
      },
      kill_switch: {
        active: killSwitchState,
        triggered_at: killSwitchState ? new Date().toISOString() : undefined,
        reason: killSwitchState ? 'Manual founder override' : undefined,
      },
    }

    return HttpResponse.json(response, { status: 200 })
  }),

  // POST /settings/kill-switch (T09.5)
  http.post(`${API_BASE}/settings/kill-switch`, async (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')
    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json({ error: { code: 401, message: 'Unauthorized' } }, { status: 401 })
    }

    const body = (await info.request.json()) as { active: boolean }
    killSwitchState = Boolean(body.active)

    return HttpResponse.json(
      {
        active: killSwitchState,
        message: killSwitchState
          ? 'Emergency kill switch active. All mandate sweeps halted.'
          : 'Kill switch released. Autonomous sweeps normal.',
      },
      { status: 200 }
    )
  }),

  // GET /v1/ops/status (T13.1)
  http.get(`${API_BASE}/v1/ops/status`, () => {
    const response: OperationsStatus = {
      status: 'degraded',
      checked_at: new Date().toISOString(),
      data_mode: 'provisional',
      kill_switch_active: killSwitchState,
      components: {
        api: { status: 'ready', detail: 'Mock API responding' },
        task_repository: { status: 'ready', detail: 'Mock task store' },
        worker: { status: 'degraded', detail: 'Health-only placeholder; no jobs are executed' },
        google: { status: 'not_configured', detail: 'Fake adapters only' },
        agent_runtime: { status: 'not_configured', detail: 'No live agent configured' },
        benchmarks: { status: 'not_configured', detail: 'No benchmark run recorded' },
        deployment: { status: 'not_configured', detail: 'No approved target configured' },
      },
    }
    return HttpResponse.json(response)
  }),

  // GET /v1/brief (T13.2)
  http.get(`${API_BASE}/v1/brief`, () => {
    const response: V1DailyBrief = {
      generated_at: new Date().toISOString(),
      items: [
        {
          event_id: 'evt_001',
          timestamp: new Date().toISOString(),
          title: 'Proposed follow-up to Raju Patel',
          summary: 'Counter-offer drafted for founder approval.',
          link: {
            kind: 'approval',
            reference: 'PA-2026-10-15-001',
            href: `${API_BASE}/approvals/pending`,
          },
        },
      ],
      omitted_unlinked_events: 0,
      limitation: 'Mock response; not live operational data.',
    }
    return HttpResponse.json(response)
  }),
]
