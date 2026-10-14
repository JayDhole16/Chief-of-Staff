/**
 * Typed API client: single fetch wrapper with error mapping, timeouts, CSRF support.
 * No direct fetch calls anywhere else in the codebase.
 */

import type { APIError, APIResponse, APIErrorCode } from './types'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'
const API_TIMEOUT_MS = 30000

export class APIClientError extends Error {
  constructor(public code: APIErrorCode, message: string) {
    super(message)
    this.name = 'APIClientError'
  }
}

/**
 * Fetch wrapper with typed requests/responses, error mapping, timeout, CSRF header.
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
  const method = options.method || 'GET'
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest', // CSRF token placeholder
    ...options.headers,
  }
  
  // Add CSRF header if available in session
  const sessionId = sessionStorage.getItem('session_id')
  if (sessionId) {
    headers['X-Session-ID'] = sessionId
  }

  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null
  const timeout = controller ? setTimeout(() => controller.abort(), API_TIMEOUT_MS) : null

  try {
    const fetchOptions: RequestInit = {
      method,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      credentials: 'include', // Send cookies with requests
    }
    let response: Response
    try {
      response = await fetch(url, { ...fetchOptions, signal: controller?.signal })
    } catch (fetchErr) {
      if (fetchErr instanceof TypeError && fetchErr.message.includes('AbortSignal')) {
        response = await fetch(url, fetchOptions)
      } else {
        throw fetchErr
      }
    }

    if (timeout) clearTimeout(timeout)



    // Map HTTP status to error code
    const errorCode = mapStatusToErrorCode(response.status)
    
    if (!response.ok) {
      const error = await parseErrorResponse(response)
      throw new APIClientError(errorCode, error.message || `HTTP ${response.status}`)
    }

    const data = await response.json()
    return data as T
  } catch (error) {
    if (timeout) clearTimeout(timeout)

    if (error instanceof APIClientError) {
      throw error
    }

    // Network or abort errors
    if (error instanceof TypeError) {
      throw new APIClientError('NETWORK', `Network error: ${error.message}`)
    }

    // Timeout (AbortError when aborted due to timeout)
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new APIClientError('TIMEOUT', `Request timeout after ${API_TIMEOUT_MS}ms`)
    }

    throw new APIClientError('NETWORK', `Unknown error: ${String(error)}`)
  }
}

function mapStatusToErrorCode(status: number): APIErrorCode {
  if (status === 401) return 401
  if (status === 403) return 403
  if (status === 409) return 409
  if (status === 422) return 422
  if (status >= 500 && status < 600) return 500
  return 'NETWORK'
}

async function parseErrorResponse(response: Response): Promise<{ message?: string }> {
  try {
    const data = await response.json()
    return data
  } catch {
    return { message: response.statusText }
  }
}

/**
 * Set session ID in sessionStorage after login.
 */
export function setSession(sessionId: string): void {
  sessionStorage.setItem('session_id', sessionId)
}

/**
 * Clear session on logout.
 */
export function clearSession(): void {
  sessionStorage.removeItem('session_id')
}

/**
 * Check if session is active.
 */
export function hasSession(): boolean {
  return sessionStorage.getItem('session_id') !== null
}
