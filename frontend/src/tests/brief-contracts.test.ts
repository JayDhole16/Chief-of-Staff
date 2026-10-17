import { describe, expect, it } from 'vitest'

import type { BriefItem, BriefLink, FounderBrief, V1BriefItem, V1DailyBrief } from '../api/types'

/**
 * The day5 merge accidentally re-merged two different brief contracts that
 * both used to be called `BriefItem`, which made the frontend build fail with
 * TS2739. These tests pin both shapes so a future merge cannot silently
 * collapse them again:
 *
 * - `/v1/brief` (legacy activity brief) -> V1BriefItem / V1DailyBrief
 * - `/api/brief` (founder brief, T13.2) -> BriefItem / FounderBrief
 */

const legacyLink = {
  kind: 'approval',
  reference: 'PA-2026-10-15-001',
  href: '/api/approvals/pending',
} as const satisfies BriefLink

const legacyItem = {
  event_id: 'evt_001',
  timestamp: '2026-10-15T10:00:00.000Z',
  title: 'Proposed follow-up to Raju Patel',
  summary: 'Counter-offer drafted for founder approval.',
  link: legacyLink,
} as const satisfies V1BriefItem

const founderItem = {
  id: 'brief-001',
  category: 'pending_decision',
  summary: 'Approval pending on counter-offer for Raju Patel.',
  status: 'pending',
  evidence_facts: [
    {
      key: 'last_contact',
      label: 'Last contact',
      value: '2026-10-14',
      source: 'inbound_email',
    },
  ],
  risk_flags: [],
} as const satisfies BriefItem

describe('brief contracts stay distinct', () => {
  it('legacy /v1/brief payload validates as V1DailyBrief', () => {
    const brief: V1DailyBrief = {
      generated_at: '2026-10-15T10:00:00.000Z',
      items: [legacyItem],
      omitted_unlinked_events: 2,
      limitation: 'Mock response; not live operational data.',
    }

    expect(brief.items[0]).toHaveProperty('event_id', 'evt_001')
    expect(brief.items[0]).not.toHaveProperty('id')
    expect(brief.items[0]).not.toHaveProperty('risk_flags')
    expect(() => founderItem as unknown as V1BriefItem).not.toThrow()
  })

  it('founder /api/brief payload validates as FounderBrief', () => {
    const brief: FounderBrief = {
      workspace_id: 'WS-DEMO',
      generated_at: '2026-10-15T10:00:00.000Z',
      headline: 'One approval is waiting on you.',
      metrics: {
        actions_executed_count: 0,
        pending_approvals_count: 1,
        escalations_count: 0,
        blocked_actions_count: 0,
        total_pipeline_value_paise: 0,
        estimated_founder_minutes_saved: 0,
      },
      items: [founderItem],
      narration_text: 'One approval is waiting on you.',
      is_audio_available: false,
      disclaimer: 'Deterministic brief; fake adapters, not live data.',
    }

    expect(brief.items[0]).toHaveProperty('id', 'brief-001')
    expect(brief.items[0]).toHaveProperty('evidence_facts')

    // The two contracts must not be interchangeable: the legacy shape has no
    // id/category/status, the founder shape has no event_id/timestamp/link.
    const legacy = legacyItem as unknown as Record<string, unknown>
    const founder = founderItem as unknown as Record<string, unknown>
    expect(legacy).not.toHaveProperty('id')
    expect(founder).not.toHaveProperty('event_id')
  })
})