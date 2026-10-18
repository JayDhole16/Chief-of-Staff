import { describe, it, expect, vi, afterEach } from 'vitest'
import { apiCall, APIClientError, SESSION_EXPIRED_EVENT, setSession, hasSession } from '../api/client'
import { mockFetch } from './fetchMock'

afterEach(() => vi.unstubAllGlobals())

describe('apiCall', () => {
  it('sends the session header when signed in', async () => {
    setSession('tok_abc')
    const { calls } = mockFetch({ 'GET /deals': () => [200, { deals: [] }] })
    await apiCall('/deals')
    expect(calls[0].headers['X-Session-ID']).toBe('tok_abc')
  })

  it('surfaces FastAPI detail messages', async () => {
    mockFetch({ 'POST /chat': () => [409, { detail: 'No AI provider configured.' }] })
    await expect(apiCall('/chat', { method: 'POST', body: {} })).rejects.toMatchObject({
      code: 409,
      message: 'No AI provider configured.',
    })
  })

  it('formats validation error lists', async () => {
    mockFetch({ 'POST /deals': () => [422, { detail: [{ loc: ['body', 'contact_email'], msg: 'invalid' }] }] })
    await expect(apiCall('/deals', { method: 'POST', body: {} })).rejects.toThrow('contact email: invalid')
  })

  it('clears the session and emits an event on 401', async () => {
    setSession('tok_old')
    const listener = vi.fn()
    window.addEventListener(SESSION_EXPIRED_EVENT, listener)
    mockFetch({ 'GET /deals': () => [401, { detail: 'Session expired' }] })
    await expect(apiCall('/deals')).rejects.toBeInstanceOf(APIClientError)
    expect(hasSession()).toBe(false)
    expect(listener).toHaveBeenCalled()
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener)
  })

  it('maps network failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(apiCall('/deals')).rejects.toMatchObject({ code: 'NETWORK' })
  })
})
