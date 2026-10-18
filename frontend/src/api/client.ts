/**
 * Typed API client: single fetch wrapper with error mapping, timeouts and session header.
 * No direct fetch calls anywhere else in the codebase.
 */

import type { APIErrorCode } from './types'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const API_TIMEOUT_MS = 120000
const SESSION_KEY = 'session_id'

export const SESSION_EXPIRED_EVENT = 'cos:session-expired'

export class APIClientError extends Error {
  constructor(public code: APIErrorCode, message: string) {
    super(message)
    this.name = 'APIClientError'
  }
}

/**
 * Fetch wrapper with typed responses, error mapping and timeout.
 * @throws APIClientError on any failure
 */
export async function apiCall<T>(
  endpoint: string,
  options: {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
    body?: unknown
    headers?: Record<string, string>
  } = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    ...options.headers,
  }
  const sessionId = getSessionId()
  if (sessionId) {
    headers['X-Session-ID'] = sessionId
  }

  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null
  const timeout = controller ? setTimeout(() => controller.abort(), API_TIMEOUT_MS) : null

  try {
    const response = await fetch(url, {
      method: options.method || 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller?.signal,
    })
    if (timeout) clearTimeout(timeout)

    if (!response.ok) {
      const message = await parseErrorMessage(response)
      if (response.status === 401 && sessionId && !endpoint.startsWith('/auth/')) {
        clearSession()
        window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT))
      }
      throw new APIClientError(mapStatusToErrorCode(response.status), message)
    }
    return (await response.json()) as T
  } catch (error) {
    if (timeout) clearTimeout(timeout)
    if (error instanceof APIClientError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new APIClientError('TIMEOUT', `Request timed out after ${API_TIMEOUT_MS / 1000}s`)
    }
    if (error instanceof TypeError) {
      throw new APIClientError('NETWORK', 'Cannot reach the server. Is the backend running?')
    }
    throw new APIClientError('NETWORK', `Unknown error: ${String(error)}`)
  }
}

function mapStatusToErrorCode(status: number): APIErrorCode {
  if ([401, 403, 404, 409, 422, 423, 502, 503].includes(status)) return status as APIErrorCode
  if (status >= 500) return 500
  return 'NETWORK'
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      // FastAPI validation errors: [{loc: [...], msg: "..."}]
      return data.detail
        .map((d: { loc?: unknown[]; msg?: string }) => {
          const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : ''
          return field ? `${String(field).replace(/_/g, ' ')}: ${d.msg}` : d.msg
        })
        .join('; ')
    }
    if (typeof data?.message === 'string') return data.message
  } catch {
    // fall through
  }
  return response.statusText || `HTTP ${response.status}`
}

/** Human-readable message for any thrown error. */
export function errorMessage(err: unknown): string {
  if (err instanceof APIClientError) return err.message
  if (err instanceof Error) return err.message
  return 'Something went wrong'
}

export function getSessionId(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY)
  } catch {
    return null
  }
}

export function setSession(sessionId: string): void {
  try {
    localStorage.setItem(SESSION_KEY, sessionId)
  } catch {
    // storage unavailable (private mode); session lasts for this page only
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY)
  } catch {
    // ignore
  }
}

export function hasSession(): boolean {
  return getSessionId() !== null
}
