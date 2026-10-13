/**
 * Typed API client: request/response types and error models.
 * Pure types, no I/O.
 */

export type APIErrorCode = 401 | 403 | 409 | 422 | 500 | 502 | 503 | 'NETWORK' | 'TIMEOUT'

export interface APIError {
  code: APIErrorCode
  message: string
  details?: Record<string, unknown>
}

export interface APIResponse<T> {
  data?: T
  error?: APIError
}

// Auth
export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  session_id: string
  user: {
    id: string
    email: string
    name: string
  }
}

export interface SessionResponse {
  session_id: string
  user: {
    id: string
    email: string
    name: string
  }
}

// Activity
export interface ActivityEvent {
  id: string
  timestamp: string
  type: 'approval' | 'execution' | 'error'
  title: string
  description: string
  user_id: string
}

export interface ActivityFeedResponse {
  events: ActivityEvent[]
  count: number
}

// Approvals
export interface Approval {
  id: string
  title: string
  description: string
  state: 'pending' | 'approved' | 'rejected'
  created_at: string
  expires_at: string
}

export interface ApprovalsResponse {
  approvals: Approval[]
  count: number
}

// Pipeline
export interface Deal {
  id: string
  title: string
  stage: 'lead' | 'negotiation' | 'approved' | 'active'
  value_paise: number
  created_at: string
}

export interface PipelineResponse {
  deals: Deal[]
  count: number
}
