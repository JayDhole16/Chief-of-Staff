/**
 * Tiny fetch router for tests: map "METHOD /path" to a handler returning [status, body].
 */

import { vi } from 'vitest'
import type { User } from '../api/types'

export type Handler = (body: unknown, url: string) => [number, unknown]

export function mockFetch(routes: Record<string, Handler>) {
  const calls: Array<{ method: string; url: string; body: unknown; headers: Record<string, string> }> = []
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = (init?.method || 'GET').toUpperCase()
    const path = url.replace(/^.*?\/api/, '').split('?')[0]
    const body = init?.body ? JSON.parse(String(init.body)) : undefined
    calls.push({ method, url, body, headers: (init?.headers || {}) as Record<string, string> })
    const handler = routes[`${method} ${path}`]
    const [status, payload] = handler ? handler(body, url) : [404, { detail: `No mock for ${method} ${path}` }]
    return new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fn)
  return { fn, calls }
}

export const TEST_USER: User = {
  id: 'usr_1',
  email: 'jay@example.com',
  name: 'Jay Founder',
  role: 'Founder & CEO',
  business_name: 'Jay Labs',
  timezone: 'Asia/Kolkata',
  signature: 'Jay',
  working_hours: '09:30 - 18:30',
  max_discount_pct: 5,
  quiet_days_threshold: 3,
  active_llm_provider: null,
  kill_switch_active: false,
  kill_switch_reason: null,
  sandbox_enabled: false,
  sandbox_emails: '',
  sandbox_phones: '',
  created_at: '2026-10-18T00:00:00Z',
}
