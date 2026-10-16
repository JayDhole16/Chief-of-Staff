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

// Verified Fact & Risk Flag Models
export interface FactEvidence {
  key: string
  label: string
  value: string
  source: string
}

export interface RiskFlag {
  code: string
  severity: 'warning' | 'critical'
  reason: string
  customer_claim?: string
}

// Proposed Actions & Approvals (T09.4)
export interface ProposedAction {
  ref: string
  kind: 'email' | 'calendar'
  deal_id: string
  deal_title: string
  contact_name: string
  contact_email: string
  subject: string
  rendered_body: string
  rendered_hash: string
  facts_used: FactEvidence[]
  risk_flags: RiskFlag[]
  policy_verdict: 'ALLOW' | 'ASK' | 'BLOCK'
  policy_reasons: string[]
  created_at: string
  expires_at: string
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'scheduled' | 'executing'
  execute_after?: string
}

export interface ApprovalDecisionRequest {
  decision: 'approve' | 'reject'
  rendered_hash: string
  rejection_reason?: string
}

export interface ApprovalDecisionResponse {
  ref: string
  status: 'approved' | 'rejected' | 'scheduled'
  rendered_hash: string
  execute_after?: string
  message: string
}

// Legacy Approval interface (extended for backwards compatibility)
export interface Approval {
  id: string
  ref?: string
  title: string
  description: string
  state: 'pending' | 'approved' | 'rejected'
  created_at: string
  expires_at: string
  proposal?: ProposedAction
}

export interface ApprovalsResponse {
  approvals: Approval[]
  count: number
}

// Action Receipts (T09.5)
export interface ActionReceipt {
  receipt_id: string
  action_ref: string
  action_kind: 'email' | 'calendar'
  status: 'executed' | 'cancelled' | 'blocked'
  authority_clause: string
  recipient_email?: string
  meeting_time?: string
  external_id?: string
  rendered_hash: string
  checks_passed: string[]
  facts_used: FactEvidence[]
  executed_at?: string
  cancelled_at?: string
  undo_window_seconds?: number
  timeline: Array<{
    timestamp: string
    event: string
  }>
}

export interface CancelActionResponse {
  ref: string
  status: 'cancelled'
  cancelled_at: string
  receipt_id: string
  message: string
}

// Activity Feed (T09.5)
export interface ActivityEvent {
  id: string
  timestamp: string
  type: 'approval' | 'execution' | 'error' | 'proposed' | 'cancelled' | 'blocked'
  title: string
  description: string
  user_id: string
  action_ref?: string
  receipt_id?: string
  escalation_id?: string
  rendered_hash?: string
  execute_after?: string
  can_undo?: boolean
}

export interface ActivityFeedResponse {
  events: ActivityEvent[]
  count: number
}

export interface OperationsComponent {
  status: 'ready' | 'degraded' | 'unavailable' | 'not_configured'
  detail: string
}

export interface OperationsStatus {
  status: 'ready' | 'degraded'
  checked_at: string
  data_mode: 'provisional'
  kill_switch_active: boolean
  components: Record<string, OperationsComponent>
}

export interface BriefLink {
  kind: 'receipt' | 'approval' | 'escalation'
  reference: string
  href: string
}

export interface BriefItem {
  event_id: string
  timestamp: string
  title: string
  summary: string
  link: BriefLink
}

export interface DailyBrief {
  generated_at: string
  items: BriefItem[]
  omitted_unlinked_events: number
  limitation: string
}

// Pipeline (T09.5)
export interface Deal {
  id: string
  title: string
  contact_name?: string
  contact_email?: string
  stage: 'lead' | 'negotiation' | 'approved' | 'active' | 'meeting_scheduled' | 'won'
  value_paise: number
  created_at: string
  days_quiet?: number
  is_quiet?: boolean
  last_interaction?: string
}

export interface PipelineResponse {
  deals: Deal[]
  count: number
}

// Settings & Ops (T09.5)
export interface SystemSettings {
  founder: {
    name: string
    email: string
    business_name: string
    timezone: string
  }
  google_account: {
    connected: boolean
    email: string
    token_status: 'valid' | 'expiring_soon' | 'expired'
    expires_at: string
    scopes: string[]
  }
  kill_switch: {
    active: boolean
    triggered_at?: string
    reason?: string
  }
}

// Founder Brief (T13.2)
export interface BriefFactEvidence {
  key: string
  label: string
  value: string
  source: string
}

export interface BriefItem {
  id: string
  category: 'executed_action' | 'pending_decision' | 'escalation' | 'pipeline_quiet' | 'blocked_action'
  deal_id?: string
  deal_title?: string
  contact_name?: string
  contact_email?: string
  summary: string
  status: string
  authority_clause?: string
  evidence_receipt_id?: string
  evidence_action_ref?: string
  evidence_facts: BriefFactEvidence[]
  risk_flags: string[]
  recommended_followup?: string
}

export interface BriefMetrics {
  actions_executed_count: number
  pending_approvals_count: number
  escalations_count: number
  blocked_actions_count: number
  total_pipeline_value_paise: number
  estimated_founder_minutes_saved: number
}

export interface FounderBrief {
  workspace_id: string
  generated_at: string
  headline: string
  metrics: BriefMetrics
  items: BriefItem[]
  narration_text: string
  is_audio_available: boolean
  disclaimer: string
}
