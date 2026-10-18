import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DashboardPage } from '../pages/DashboardPage'
import { mockFetch, TEST_USER, type Handler } from './fetchMock'

afterEach(() => vi.unstubAllGlobals())

const EMPTY_BRIEF = {
  generated_at: '2026-10-18T00:00:00Z',
  deal_count: 0,
  open_pipeline_inr: 0,
  won_inr: 0,
  stage_counts: {},
  quiet_deals: [],
  pending_approvals: 0,
  emails_sent: 0,
  recent_activity: [],
  kill_switch_active: false,
  ai_provider: null,
}

const BLANK_PROVIDER = {
  default_base_url: null,
  docs_url: null,
  configured: false,
  masked_key: null,
  model: null,
  base_url: null,
  updated_at: null,
  last_tested_at: null,
  last_test_ok: null,
  last_test_message: null,
}

const PROVIDERS = [
  { ...BLANK_PROVIDER, provider: 'anthropic', label: 'Anthropic (Claude)', default_model: 'claude-opus-5-5', key_hint: 'sk-ant-...' },
  { ...BLANK_PROVIDER, provider: 'openai', label: 'OpenAI', default_model: 'gpt-4o-mini', key_hint: 'sk-...', default_base_url: 'https://api.openai.com/v1' },
]

function baseRoutes(): Record<string, Handler> {
  return {
    'GET /brief': () => [200, EMPTY_BRIEF],
    'GET /settings/email': () => [200, { configured: false, settings: null }],
    'GET /approvals': () => [200, { approvals: [], count: 0 }],
    'GET /settings/api-keys': () => [200, { active_provider: null, providers: PROVIDERS }],
    'GET /settings/usage': () => [200, { by_model: [], total_requests: 0, total_input_tokens: 0, total_output_tokens: 0 }],
    'GET /deals': () => [200, { deals: [], count: 0, open_pipeline_inr: 0, won_inr: 0 }],
    'GET /chat/sessions': () => [200, { sessions: [] }],
    'GET /integrations/google': () => [200, GOOGLE_DISCONNECTED],
  }
}

const GOOGLE_DISCONNECTED = {
  configured: true,
  connected: false,
  email: null,
  connected_at: null,
  last_error: null,
  can_send_email: false,
  can_manage_calendar: false,
  redirect_uri: 'http://localhost:5173/api/integrations/google/callback',
}

const GOOGLE_CONNECTED = {
  ...GOOGLE_DISCONNECTED,
  connected: true,
  email: 'jay@gmail.com',
  connected_at: '2026-10-18T00:00:00Z',
  can_send_email: true,
  can_manage_calendar: true,
}

const DEAL = {
  id: 'D-1',
  company: 'Acme',
  title: 'Automation',
  contact_name: 'Asha',
  contact_email: 'asha@acme.example',
  stage: 'negotiating',
  value_inr: 250000,
  notes: '',
  do_not_contact: false,
  last_contact_at: '2026-10-10T00:00:00Z',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-10T00:00:00Z',
  days_quiet: 8,
  is_quiet: true,
}

describe('DashboardPage', () => {
  it('starts with an empty workspace and setup checklist (no demo data)', async () => {
    mockFetch(baseRoutes())
    render(<DashboardPage user={TEST_USER} onUserChange={vi.fn()} onLogout={vi.fn()} />)
    expect(await screen.findByText('Hello, Jay')).toBeInTheDocument()
    expect(await screen.findByText('Connect your AI provider')).toBeInTheDocument()
    expect(screen.getByText('Your workspace is empty')).toBeInTheDocument()
    expect(screen.queryByText(/Raju|Meera|Malhotra/)).not.toBeInTheDocument()
  })

  it('lets the user connect their own AI key from the home page', async () => {
    const onUserChange = vi.fn()
    let keyState: unknown = { active_provider: null, providers: PROVIDERS }
    const { calls } = mockFetch({
      ...baseRoutes(),
      'GET /settings/api-keys': () => [200, keyState],
      'PUT /settings/api-keys/openai': () => {
        keyState = {
          active_provider: 'openai',
          providers: [PROVIDERS[0], { ...PROVIDERS[1], configured: true, masked_key: '••••9999', last_test_ok: true }],
        }
        return [200, keyState]
      },
      'GET /profile': () => [200, { ...TEST_USER, active_llm_provider: 'openai' }],
      'POST /settings/api-keys/openai/test': () => [200, { ok: true, message: 'Connected to gpt-4o-mini', tested_at: '2026-10-18T00:00:00Z' }],
    })
    render(<DashboardPage user={TEST_USER} onUserChange={onUserChange} onLogout={vi.fn()} />)

    const form = await screen.findByRole('form', { name: 'Connect your AI provider' })
    await userEvent.selectOptions(within(form).getByLabelText('Provider'), 'openai')
    await userEvent.type(within(form).getByLabelText('API key'), 'sk-user-own-9999')
    await userEvent.click(within(form).getByRole('button', { name: 'Save & test key' }))

    expect(await screen.findByText(/AI provider: OpenAI/)).toBeInTheDocument()
    expect(await screen.findByText('connected')).toBeInTheDocument()
    expect(screen.getByText('••••9999')).toBeInTheDocument()
    const put = calls.find((c) => c.method === 'PUT')!
    expect(put.body).toMatchObject({ api_key: 'sk-user-own-9999', make_active: true })
    expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/settings/api-keys/openai/test'))).toBe(true)
    expect(onUserChange).toHaveBeenCalledWith(expect.objectContaining({ active_llm_provider: 'openai' }))
  })

  it('saves a user-provided API key from the API Keys section', async () => {
    const onUserChange = vi.fn()
    const { calls } = mockFetch({
      ...baseRoutes(),
      'PUT /settings/api-keys/anthropic': () => [
        200,
        {
          active_provider: 'anthropic',
          providers: [{ ...PROVIDERS[0], configured: true, masked_key: '••••WXYZ' }, PROVIDERS[1]],
        },
      ],
      'GET /profile': () => [200, { ...TEST_USER, active_llm_provider: 'anthropic' }],
    })
    render(<DashboardPage user={TEST_USER} onUserChange={onUserChange} onLogout={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'API Keys' }))
    expect(await screen.findByText('API Keys & Integrations')).toBeInTheDocument()

    const card = (await screen.findByText('Anthropic (Claude)')).closest('.cos-card') as HTMLElement
    await userEvent.click(within(card).getByRole('button', { name: 'Add key' }))
    await userEvent.type(within(card).getByLabelText(/API key/), 'sk-ant-test-WXYZ')
    await userEvent.click(within(card).getByRole('button', { name: 'Save key' }))

    await waitFor(() => expect(screen.getByText('••••WXYZ')).toBeInTheDocument())
    const put = calls.find((c) => c.method === 'PUT')!
    expect(put.body).toMatchObject({ api_key: 'sk-ant-test-WXYZ', make_active: true })
    await waitFor(() =>
      expect(onUserChange).toHaveBeenCalledWith(expect.objectContaining({ active_llm_provider: 'anthropic' }))
    )
  })

  it('starts Google OAuth from the API Keys page', async () => {
    const assign = vi.fn()
    const original = window.location
    Object.defineProperty(window, 'location', { configurable: true, value: { ...original, assign, search: '' } })
    try {
      mockFetch({
        ...baseRoutes(),
        'POST /integrations/google/connect': () => [200, { auth_url: 'https://accounts.google.com/o/oauth2/v2/auth?state=abc' }],
      })
      render(<DashboardPage user={TEST_USER} onUserChange={vi.fn()} onLogout={vi.fn()} />)
      await userEvent.click(screen.getByRole('button', { name: 'API Keys' }))
      await userEvent.click(await screen.findByRole('button', { name: /Connect Google account/ }))
      await waitFor(() => expect(assign).toHaveBeenCalledWith('https://accounts.google.com/o/oauth2/v2/auth?state=abc'))
    } finally {
      Object.defineProperty(window, 'location', { configurable: true, value: original })
    }
  })

  it('proposes a Google Calendar meeting from a deal', async () => {
    const { calls } = mockFetch({
      ...baseRoutes(),
      'GET /deals': () => [200, { deals: [DEAL], count: 1, open_pipeline_inr: 250000, won_inr: 0 }],
      'GET /integrations/google': () => [200, GOOGLE_CONNECTED],
      'POST /deals/D-1/meeting': () => [201, { ref: 'PA-1', contact_name: 'Asha', policy_verdict: 'ALLOW', status: 'pending' }],
    })
    render(<DashboardPage user={TEST_USER} onUserChange={vi.fn()} onLogout={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Deals' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Schedule meeting' }))
    const dialog = await screen.findByRole('dialog')
    await waitFor(() => expect(within(dialog).getByRole('button', { name: 'Propose meeting' })).toBeEnabled())
    await userEvent.selectOptions(within(dialog).getByLabelText('Duration'), '45')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Propose meeting' }))

    await waitFor(() => expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/deals/D-1/meeting'))).toBe(true))
    const post = calls.find((c) => c.method === 'POST')!
    const body = post.body as { start_utc: string; duration_minutes: number; with_meet: boolean; timezone: string }
    expect(body.duration_minutes).toBe(45)
    expect(body.with_meet).toBe(true)
    expect(new Date(body.start_utc).getTime()).toBeGreaterThan(Date.now())
    expect(body.timezone).toBeTruthy()
  })

  it('tells the user to add a key before chatting', async () => {
    mockFetch(baseRoutes())
    render(<DashboardPage user={TEST_USER} onUserChange={vi.fn()} onLogout={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Chat' }))
    expect(await screen.findByText(/Chat runs on your own AI provider key/)).toBeInTheDocument()
  })

  it('creates a deal from the Deals view', async () => {
    const { calls } = mockFetch({
      ...baseRoutes(),
      'POST /deals': (body) => [201, { ...(body as object), id: 'D-1' }],
    })
    render(<DashboardPage user={TEST_USER} onUserChange={vi.fn()} onLogout={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Deals' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Add your first deal' }))
    const dialog = screen.getByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText('Company *'), 'Acme')
    await userEvent.type(within(dialog).getByLabelText('Deal title *'), 'Automation')
    await userEvent.type(within(dialog).getByLabelText('Contact name *'), 'Asha')
    await userEvent.type(within(dialog).getByLabelText('Contact email'), 'asha@acme.example')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Add deal' }))
    await waitFor(() => expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/deals'))).toBe(true))
    const post = calls.find((c) => c.method === 'POST')!
    expect(post.body).toMatchObject({ company: 'Acme', contact_email: 'asha@acme.example', stage: 'lead' })
  })
})
