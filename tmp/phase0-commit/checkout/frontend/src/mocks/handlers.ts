/**
 * MSW request handlers: login, session, activity, approvals, pipeline.
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
} from '../api/types'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

// Mock data storage (session state)
const mockSessions = new Map<string, { userId: string; email: string; name: string }>()
let sessionCounter = 0

export const handlers = [
  // POST /auth/login
  http.post(`${API_BASE}/auth/login`, async (info) => {
    const { email, password } = (await info.request.json()) as LoginRequest

    // Mock validation
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

    await delay(300) // Simulate network latency

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

  // GET /activity
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
          id: 'evt_1',
          timestamp: new Date().toISOString(),
          type: 'approval',
          title: 'Deal approved',
          description: 'Summer clearance deal approved',
          user_id: 'user_456',
        },
        {
          id: 'evt_2',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          type: 'execution',
          title: 'Email sent',
          description: 'Approval notification sent to customer',
          user_id: 'user_123',
        },
      ],
      count: 2,
    }

    return HttpResponse.json(response, { status: 200 })
  }),

  // GET /approvals/pending
  http.get(`${API_BASE}/approvals/pending`, (info) => {
    const sessionId = info.request.headers.get('X-Session-ID')

    if (!sessionId || !mockSessions.has(sessionId)) {
      return HttpResponse.json(
        { error: { code: 401, message: 'Unauthorized' } },
        { status: 401 }
      )
    }

    const response: ApprovalsResponse = {
      approvals: [
        {
          id: 'appr_1',
          title: '₹12,50,000 deal approval',
          description: 'Summer sale offer requires approval',
          state: 'pending',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 3600000).toISOString(),
        },
      ],
      count: 1,
    }

    return HttpResponse.json(response, { status: 200 })
  }),

  // GET /pipeline/deals
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
          id: 'deal_1',
          title: 'Summer Clearance',
          stage: 'negotiation',
          value_paise: 125000000,
          created_at: new Date().toISOString(),
        },
        {
          id: 'deal_2',
          title: 'B2B Partnership',
          stage: 'lead',
          value_paise: 250000000,
          created_at: new Date(Date.now() - 604800000).toISOString(),
        },
      ],
      count: 2,
    }

    return HttpResponse.json(response, { status: 200 })
  }),
]
