import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DashboardPage } from '../pages/DashboardPage'
import { mockFetch, TEST_USER, type Handler } from './fetchMock'

const USER = { ...TEST_USER, active_llm_provider: 'anthropic' }

class FakeRecognition {
  static instances: FakeRecognition[] = []
  lang = ''
  continuous = false
  interimResults = false
  maxAlternatives = 1
  onresult: ((e: unknown) => void) | null = null
  onerror: ((e: unknown) => void) | null = null
  onend: (() => void) | null = null
  start = vi.fn()
  stop = vi.fn(() => this.onend?.())
  abort = vi.fn()
  constructor() {
    FakeRecognition.instances.push(this)
  }
  emit(text: string, isFinal: boolean) {
    const result = Object.assign([{ transcript: text }], { isFinal })
    this.onresult?.({ resultIndex: 0, results: [result] })
  }
}

const PROPOSAL = {
  ref: 'PA-20261018-ABC123',
  deal_id: 'D-1',
  kind: 'email',
  deal_title: 'Acme · Pilot',
  contact_name: 'Asha',
  contact_email: 'asha@acme.example',
  subject: 'Following up',
  rendered_body: 'Hi Asha, checking in.\n\nJay',
  rendered_hash: 'a'.repeat(64),
  policy_verdict: 'ALLOW',
  policy_reasons: [],
  guards_checked: ['G01'],
  facts_used: [],
  status: 'pending',
  created_at: '2026-10-18T00:00:00Z',
  expires_at: '2026-10-20T00:00:00Z',
  decided_at: null,
  receipt_id: null,
  payload: null,
}

function routes(extra: Record<string, Handler> = {}): Record<string, Handler> {
  return {
    'GET /approvals': () => [200, { approvals: [], count: 0 }],
    'GET /chat/sessions': () => [200, { sessions: [] }],
    'GET /brief': () => [200, { deal_count: 0, open_pipeline_inr: 0, won_inr: 0, stage_counts: {}, quiet_deals: [], pending_approvals: 0, emails_sent: 0, recent_activity: [], kill_switch_active: false, ai_provider: 'anthropic' }],
    'GET /settings/email': () => [200, { configured: false, settings: null }],
    'GET /integrations/google': () => [200, { configured: false, connected: false }],
    'GET /settings/api-keys': () => [200, { active_provider: 'anthropic', providers: [] }],
    ...extra,
  }
}

async function openChat() {
  render(<DashboardPage user={USER} onUserChange={vi.fn()} onLogout={vi.fn()} />)
  await userEvent.click(screen.getByRole('button', { name: 'Chat' }))
  return screen.getByRole('textbox', { name: 'Message' }) as HTMLTextAreaElement
}

describe('Voice dictation', () => {
  beforeEach(() => {
    FakeRecognition.instances = []
    ;(window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition = FakeRecognition
  })
  afterEach(() => {
    delete (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition
    vi.unstubAllGlobals()
  })

  it('streams speech into the input and keeps typed text', async () => {
    mockFetch(routes())
    const input = await openChat()
    await userEvent.type(input, 'Please')
    await userEvent.click(screen.getByRole('button', { name: 'Start voice dictation' }))
    const rec = FakeRecognition.instances[0]
    expect(rec.start).toHaveBeenCalled()
    expect(rec.lang.toLowerCase().startsWith('en')).toBe(true)

    act(() => rec.emit('email Asha', false))
    expect(input.value).toBe('Please email Asha')
    act(() => rec.emit('email Asha about the pilot', true))
    await userEvent.click(screen.getByRole('button', { name: 'Stop dictation' }))
    expect(rec.stop).toHaveBeenCalled()
    expect(input.value).toBe('Please email Asha about the pilot')
  })

  it('explains a denied microphone', async () => {
    mockFetch(routes())
    await openChat()
    await userEvent.click(screen.getByRole('button', { name: 'Start voice dictation' }))
    act(() => FakeRecognition.instances[0].onerror?.({ error: 'not-allowed' }))
    expect(await screen.findByText(/Microphone access was blocked/)).toBeInTheDocument()
  })

  it('reports unsupported browsers', async () => {
    delete (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition
    mockFetch(routes())
    await openChat()
    await userEvent.click(screen.getByRole('button', { name: 'Start voice dictation' }))
    expect(await screen.findByText(/not supported in this browser/)).toBeInTheDocument()
  })

  it('auto-sends after dictation when enabled', async () => {
    const { calls } = mockFetch(
      routes({
        'POST /chat': (body) => [200, {
          session_id: 'chat_1', session_title: 't',
          user_message: { id: 'u1', role: 'user', content: (body as { message: string }).message, created_at: '2026-10-18T00:00:00Z' },
          reply: { id: 'a1', role: 'assistant', content: 'On it.', created_at: '2026-10-18T00:00:01Z' },
          actions: [], tool_calls: [], usage: { input_tokens: 1, output_tokens: 1 },
        }],
      })
    )
    await openChat()
    await userEvent.click(screen.getByLabelText('Send automatically when I stop dictating'))
    await userEvent.click(screen.getByRole('button', { name: 'Start voice dictation' }))
    const rec = FakeRecognition.instances[0]
    act(() => rec.emit("what's on my calendar tomorrow", true))
    await userEvent.click(screen.getByRole('button', { name: 'Stop dictation' }))
    await waitFor(() => expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/chat'))).toBe(true))
    expect((calls.find((c) => c.method === 'POST')!.body as { message: string }).message).toBe("what's on my calendar tomorrow")
  })
})

describe('Agent actions in chat', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows a confirmation card and confirms the hash-bound action', async () => {
    const { calls } = mockFetch(
      routes({
        'POST /chat': () => [200, {
          session_id: 'chat_1', session_title: 't',
          user_message: { id: 'u1', role: 'user', content: 'Send a follow-up email to Asha', created_at: '2026-10-18T00:00:00Z' },
          reply: { id: 'a1', role: 'assistant', content: 'I drafted it. Please confirm below.', created_at: '2026-10-18T00:00:01Z',
            meta: { actions: [PROPOSAL.ref], tool_calls: [{ name: 'find_contacts', ok: true, summary: '1 result(s)' }, { name: 'draft_email', ok: true, summary: 'prepared' }] } },
          actions: [PROPOSAL],
          tool_calls: [],
          usage: { input_tokens: 1, output_tokens: 1 },
        }],
        [`POST /approvals/${PROPOSAL.ref}/decision`]: () => [200, { ref: PROPOSAL.ref, status: 'sent', receipt: null, message: 'Sent from jay@gmail.com via Gmail' }],
      })
    )
    const input = await openChat()
    await userEvent.type(input, 'Send a follow-up email to Asha{Enter}')

    expect(await screen.findByText('Following up')).toBeInTheDocument()
    expect(screen.getByText(/To Asha · asha@acme.example/)).toBeInTheDocument()
    expect(screen.getByText(/find contacts/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Confirm & send' }))
    // shown on the card and in the toast
    expect((await screen.findAllByText('Sent from jay@gmail.com via Gmail')).length).toBeGreaterThan(0)
    const decision = calls.find((c) => c.url.endsWith('/decision'))!
    expect(decision.body).toMatchObject({ decision: 'approve', rendered_hash: PROPOSAL.rendered_hash })
    expect(screen.queryByRole('button', { name: 'Confirm & send' })).not.toBeInTheDocument()
  })
})
