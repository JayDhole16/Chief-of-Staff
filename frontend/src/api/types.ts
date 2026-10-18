/**
 * Typed API contract shared with backend/api/app.py.
 * Pure types, no I/O.
 */

export type APIErrorCode = 401 | 403 | 404 | 409 | 422 | 423 | 500 | 502 | 503 | 'NETWORK' | 'TIMEOUT'

// ---------------------------------------------------------------- auth & profile
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  name: string
  email: string
  password: string
  business_name?: string
}

export interface User {
  id: string
  email: string
  name: string
  role: string
  business_name: string
  timezone: string
  signature: string
  working_hours: string
  max_discount_pct: number
  quiet_days_threshold: number
  active_llm_provider: string | null
  kill_switch_active: boolean
  kill_switch_reason: string | null
  created_at: string
}

export interface LoginResponse {
  session_id: string
  user: User
}

export type ProfileUpdate = Partial<
  Pick<
    User,
    | 'name'
    | 'role'
    | 'business_name'
    | 'timezone'
    | 'signature'
    | 'working_hours'
    | 'max_discount_pct'
    | 'quiet_days_threshold'
  >
>

// ---------------------------------------------------------------- deals
export type DealStage = 'lead' | 'qualified' | 'proposal_sent' | 'negotiating' | 'won' | 'lost'

export interface Deal {
  id: string
  company: string
  title: string
  contact_name: string
  contact_email: string
  stage: DealStage
  value_inr: number
  notes: string
  do_not_contact: boolean
  last_contact_at: string | null
  created_at: string
  updated_at: string
  days_quiet: number | null
  is_quiet?: boolean
}

export interface DealInput {
  company: string
  title: string
  contact_name: string
  contact_email: string
  stage: DealStage
  value_inr: number
  notes: string
  do_not_contact: boolean
  last_contact_at?: string | null
}

export interface DealsResponse {
  deals: Deal[]
  count: number
  open_pipeline_inr: number
  won_inr: number
}

export interface SweepResponse {
  scanned: number
  threshold_days: number
  drafted: string[]
  skipped: Array<{ deal: string; reason: string }>
}

// ---------------------------------------------------------------- approvals & receipts
export type ProposalStatus = 'pending' | 'blocked' | 'approved' | 'sent' | 'rejected' | 'expired'

export interface FactUsed {
  label: string
  value: string
  source: string
}

export interface Proposal {
  ref: string
  deal_id: string | null
  kind: string
  deal_title: string
  contact_name: string
  contact_email: string
  subject: string
  rendered_body: string
  rendered_hash: string
  policy_verdict: 'ALLOW' | 'ASK' | 'BLOCK'
  policy_reasons: string[]
  guards_checked: string[]
  facts_used: FactUsed[]
  status: ProposalStatus
  created_at: string
  expires_at: string
  decided_at: string | null
  receipt_id: string | null
}

export interface ApprovalsResponse {
  approvals: Proposal[]
  count: number
}

export interface Receipt {
  receipt_id: string
  action_ref: string
  action_kind: string
  status: 'sent' | 'approved_manual' | 'failed'
  recipient_email: string | null
  subject: string | null
  rendered_hash: string
  external_id: string | null
  detail: string
  guards_checked: string[]
  timeline: Array<{ timestamp: string; event: string }>
  created_at: string
}

export interface DecisionResponse {
  ref: string
  status: 'approved' | 'sent' | 'rejected'
  receipt: Receipt | null
  message: string
}

// ---------------------------------------------------------------- activity & brief
export interface ActivityEvent {
  id: string
  type: string
  title: string
  description: string
  action_ref: string | null
  receipt_id: string | null
  deal_id: string | null
  created_at: string
}

export interface ActivityResponse {
  events: ActivityEvent[]
  count: number
}

export interface Brief {
  generated_at: string
  deal_count: number
  open_pipeline_inr: number
  won_inr: number
  stage_counts: Partial<Record<DealStage, number>>
  quiet_deals: Array<{ id: string; company: string; contact_name: string; days_quiet: number | null }>
  pending_approvals: number
  emails_sent: number
  recent_activity: ActivityEvent[]
  kill_switch_active: boolean
  ai_provider: string | null
}

// ---------------------------------------------------------------- chat
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  provider?: string | null
  model?: string | null
  created_at: string
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count?: number
}

export interface ChatResponse {
  session_id: string
  session_title: string
  user_message: ChatMessage
  reply: ChatMessage
  usage: { input_tokens: number; output_tokens: number }
}

// ---------------------------------------------------------------- settings
export interface ProviderKey {
  provider: string
  label: string
  default_model: string
  default_base_url: string | null
  key_hint: string
  docs_url: string | null
  configured: boolean
  masked_key: string | null
  model: string | null
  base_url: string | null
  updated_at: string | null
  last_tested_at: string | null
  last_test_ok: boolean | null
  last_test_message: string | null
}

export interface ApiKeysResponse {
  active_provider: string | null
  providers: ProviderKey[]
}

export interface TestResult {
  ok: boolean
  message: string
  tested_at: string
}

export interface UsageResponse {
  by_model: Array<{
    provider: string
    model: string
    requests: number
    input_tokens: number
    output_tokens: number
    last_used_at: string
  }>
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
}

export interface EmailSettings {
  host: string
  port: number
  username: string
  from_email: string
  use_ssl: boolean
  has_password: boolean
  masked_password: string | null
  updated_at: string
  last_tested_at: string | null
  last_test_ok: boolean | null
  last_test_message: string | null
}

export interface EmailSettingsResponse {
  configured: boolean
  settings: EmailSettings | null
}

export interface OpsStatus {
  status: 'ready' | 'degraded'
  checked_at: string
  components: Record<string, { status: 'ready' | 'degraded' | 'unavailable' | 'not_configured'; detail: string }>
}
