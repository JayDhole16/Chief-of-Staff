/**
 * Main dashboard with bottom tab navigation (390px mobile-first).
 * Tabs: Command, Approvals, Activity, Pipeline, Settings.
 */

import React, { useState, useEffect } from 'react'
import type {
  LoginResponse,
  ApprovalsResponse,
  ActivityFeedResponse,
  PipelineResponse,
  ProposedAction,
  Deal,
  ActivityEvent,
  SystemSettings,
  OperationsStatus,
  V1DailyBrief,
} from '../api/types'
import { apiCall } from '../api/client'
import { ApprovalCard } from '../components/ApprovalCard'
import { ActivityFeed } from '../components/ActivityFeed'
import { FounderBriefView } from '../components/FounderBriefView'
import { PipelineView } from '../components/PipelineView'
import { SettingsView } from '../components/SettingsView'

export interface DashboardPageProps {
  session: LoginResponse
  onLogout: () => void
}

type TabId = 'command' | 'approvals' | 'activity' | 'pipeline' | 'operations' | 'settings'

const TABS: Array<{ id: TabId; label: string; icon: string }> = [
  { id: 'command', label: 'Command', icon: '⚡' },
  { id: 'approvals', label: 'Approvals', icon: '✓' },
  { id: 'activity', label: 'Activity', icon: '📋' },
  { id: 'pipeline', label: 'Pipeline', icon: '📊' },
  { id: 'operations', label: 'Ops', icon: 'ℹ️' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
]

export function DashboardPage({ session, onLogout }: DashboardPageProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>('approvals')
  const [pendingCount, setPendingCount] = useState<number>(1)
  const [killSwitchActive, setKillSwitchActive] = useState<boolean>(false)

  const renderTabContent = () => {
    switch (activeTab) {
      case 'command':
        return <CommandTab killSwitchActive={killSwitchActive} />
      case 'approvals':
        return <ApprovalsTab onCountChange={setPendingCount} />
      case 'activity':
        return <ActivityTab />
      case 'pipeline':
        return <PipelineTab />
      case 'operations':
        return <OperationsTab />
      case 'settings':
        return (
          <SettingsTab
            session={session}
            onLogout={onLogout}
            onKillSwitchChange={setKillSwitchActive}
          />
        )
      default:
        return null
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        backgroundColor: '#f9fafb',
        maxWidth: '390px',
        margin: '0 auto',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '0.875rem 1rem',
          backgroundColor: 'white',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h1 style={{ margin: '0', fontSize: '1.125rem', color: '#111827', fontWeight: 700 }}>
          Chief of Staff
        </h1>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {killSwitchActive ? (
            <span
              style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                backgroundColor: '#fee2e2',
                color: '#dc2626',
                padding: '0.15rem 0.4rem',
                borderRadius: '0.25rem',
              }}
            >
              🛑 KILL SWITCH
            </span>
          ) : (
            <span
              style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                backgroundColor: '#ecfdf5',
                color: '#065f46',
                padding: '0.15rem 0.4rem',
                borderRadius: '0.25rem',
              }}
            >
              ● SYSTEM ACTIVE
            </span>
          )}
        </div>
      </div>

      {/* Tab content */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1rem',
        }}
      >
        {renderTabContent()}
      </div>

      {/* Bottom tab navigation */}
      <nav
        style={{
          display: 'flex',
          borderTop: '1px solid #e5e7eb',
          backgroundColor: 'white',
          boxShadow: '0 -1px 3px rgba(0,0,0,0.05)',
        }}
      >
        {TABS.map((tab) => {
          const isSelected = activeTab === tab.id
          const showBadge = tab.id === 'approvals' && pendingCount > 0

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1,
                padding: '0.625rem 0.25rem',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.2rem',
                border: 'none',
                backgroundColor: isSelected ? '#f0f4ff' : 'transparent',
                borderTop: isSelected ? '3px solid #3b82f6' : '3px solid transparent',
                cursor: 'pointer',
                color: isSelected ? '#3b82f6' : '#6b7280',
                fontSize: '0.7rem',
                fontWeight: isSelected ? 700 : 500,
                position: 'relative',
              }}
            >
              <span style={{ fontSize: '1.15rem' }}>{tab.icon}</span>
              <span>{tab.label}</span>
              {showBadge && (
                <span
                  data-testid="approvals-badge"
                  style={{
                    position: 'absolute',
                    top: '4px',
                    right: '18px',
                    backgroundColor: '#ef4444',
                    color: 'white',
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    borderRadius: '9999px',
                    width: '16px',
                    height: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {pendingCount}
                </span>
              )}
            </button>
          )
        })}
      </nav>
    </div>
  )
}

function CommandTab({ killSwitchActive }: { killSwitchActive: boolean }): JSX.Element {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <FounderBriefView />
      <div
        style={{
          padding: '1rem',
          backgroundColor: '#ffffff',
          borderRadius: '0.5rem',
          border: '1px solid #e5e7eb',
        }}
      >
        <div style={{ fontSize: '0.8125rem', color: '#4b5563', lineHeight: 1.5 }}>
          Autonomous Chief of Staff is monitoring your Gmail and Calendar. Quiet proposals are swept under active mandates.
        </div>
        <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#6b7280' }}>
          Status: {killSwitchActive ? '🛑 Autonomy Paused (Kill Switch Active)' : '⚡ Ready for text/voice mandate input'}
        </div>
      </div>
    </div>
  )
}

function ApprovalsTab({ onCountChange }: { onCountChange: (count: number) => void }): JSX.Element {
  const [proposals, setProposals] = useState<ProposedAction[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isActing, setIsActing] = useState(false)

  const fetchApprovals = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await apiCall<ApprovalsResponse>('/approvals/pending')
      const items = res.approvals
        .map((a) => a.proposal)
        .filter((p): p is ProposedAction => Boolean(p))
      setProposals(items)
      onCountChange(items.length)
    } catch (err) {
      setError((err as Error).message || 'Failed to load approvals')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchApprovals()
  }, [])

  const handleApprove = async (proposal: ProposedAction) => {
    setIsActing(true)
    try {
      await apiCall(`/approvals/${proposal.ref}/decision`, {
        method: 'POST',
        body: {
          decision: 'approve',
          rendered_hash: proposal.rendered_hash,
        },
      })
      // Success: decrease pending count
      onCountChange(Math.max(0, proposals.length - 1))
    } finally {
      setIsActing(false)
    }
  }

  const handleReject = async (proposal: ProposedAction, reason?: string) => {
    setIsActing(true)
    try {
      await apiCall(`/approvals/${proposal.ref}/decision`, {
        method: 'POST',
        body: {
          decision: 'reject',
          rendered_hash: proposal.rendered_hash,
          rejection_reason: reason,
        },
      })
      onCountChange(Math.max(0, proposals.length - 1))
    } finally {
      setIsActing(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Pending Approvals</h2>
        <button
          type="button"
          onClick={fetchApprovals}
          disabled={isLoading}
          style={{
            padding: '0.25rem 0.5rem',
            fontSize: '0.75rem',
            backgroundColor: '#f3f4f6',
            border: '1px solid #d1d5db',
            borderRadius: '0.25rem',
            cursor: 'pointer',
          }}
        >
          {isLoading ? '...' : '↻ Refresh'}
        </button>
      </div>

      {error && (
        <div
          style={{
            padding: '0.75rem',
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            borderRadius: '0.375rem',
            fontSize: '0.8125rem',
          }}
        >
          {error}
        </div>
      )}

      {isLoading && (
        <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280', fontSize: '0.875rem' }}>
          Loading pending proposals...
        </div>
      )}

      {!isLoading && proposals.length === 0 && (
        <div
          data-testid="no-approvals-empty"
          style={{
            padding: '2rem 1rem',
            textAlign: 'center',
            backgroundColor: '#ffffff',
            borderRadius: '0.5rem',
            border: '1px dashed #d1d5db',
            color: '#6b7280',
            fontSize: '0.875rem',
          }}
        >
          ✓ No pending approvals. All actions comply with active mandates or are queued.
        </div>
      )}

      {proposals.map((proposal) => (
        <ApprovalCard
          key={proposal.ref}
          proposal={proposal}
          onApprove={handleApprove}
          onReject={handleReject}
          onReload={fetchApprovals}
          isActing={isActing}
        />
      ))}
    </div>
  )
}

function ActivityTab(): JSX.Element {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchActivity = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await apiCall<ActivityFeedResponse>('/activity')
      setEvents(res.events || [])
    } catch (err) {
      setError(err as Error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchActivity()
  }, [])

  return (
    <ActivityFeed
      events={events}
      isLoading={isLoading}
      error={error}
      onRefresh={fetchActivity}
    />
  )
}

function PipelineTab(): JSX.Element {
  const [deals, setDeals] = useState<Deal[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchDeals = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await apiCall<PipelineResponse>('/pipeline/deals')
      setDeals(res.deals || [])
    } catch (err) {
      setError(err as Error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchDeals()
  }, [])

  return (
    <PipelineView
      deals={deals}
      isLoading={isLoading}
      error={error}
      onRefresh={fetchDeals}
    />
  )
}

function OperationsTab(): JSX.Element {
  const [status, setStatus] = useState<OperationsStatus | null>(null)
  const [brief, setBrief] = useState<V1DailyBrief | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refresh = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [operationsStatus, dailyBrief] = await Promise.all([
        apiCall<OperationsStatus>('/v1/ops/status'),
        apiCall<V1DailyBrief>('/v1/brief'),
      ])
      setStatus(operationsStatus)
      setBrief(dailyBrief)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Operations & Brief</h2>
        <button type="button" onClick={() => void refresh()} disabled={isLoading}>
          {isLoading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      <p style={{ margin: 0, fontSize: '0.75rem', color: '#92400e' }}>
        Provisional local/demo status. This is not evidence of live G4 or production readiness.
      </p>
      {error && (
        <p role="alert" style={{ color: '#991b1b', fontSize: '0.8125rem' }}>
          Could not load operations data: {error}
        </p>
      )}
      {status && (
        <div data-testid="operations-status">
          <h3 style={{ fontSize: '0.875rem' }}>
            System status: {status.status} · Kill switch: {status.kill_switch_active ? 'active' : 'off'}
          </h3>
          <ul style={{ paddingLeft: '1.25rem', fontSize: '0.75rem' }}>
            {Object.entries(status.components).map(([name, component]) => (
              <li key={name} style={{ marginBottom: '0.375rem' }}>
                <strong>{name}: {component.status}</strong> — {component.detail}
              </li>
            ))}
          </ul>
        </div>
      )}
      {brief && (
        <div data-testid="daily-brief">
          <h3 style={{ fontSize: '0.875rem' }}>Recent activity</h3>
          {brief.omitted_unlinked_events > 0 && (
            <p role="status" style={{ fontSize: '0.75rem' }}>
              {brief.omitted_unlinked_events} unlinked event(s) omitted from this brief.
            </p>
          )}
          {brief.items.length === 0 ? (
            <p style={{ fontSize: '0.75rem' }}>No linked activity is available.</p>
          ) : (
            <ul style={{ paddingLeft: '1.25rem', fontSize: '0.75rem' }}>
              {brief.items.map((item) => (
                <li key={item.event_id} style={{ marginBottom: '0.625rem' }}>
                  <strong>{item.title}</strong>
                  <p style={{ margin: '0.25rem 0' }}>{item.summary}</p>
                  <a href={item.link.href}>
                    View {item.link.kind}: {item.link.reference}
                  </a>
                </li>
              ))}
            </ul>
          )}
          <p style={{ fontSize: '0.6875rem', color: '#6b7280' }}>{brief.limitation}</p>
        </div>
      )}
    </section>
  )
}

function SettingsTab({
  session,
  onLogout,
  onKillSwitchChange,
}: {
  session: LoginResponse
  onLogout: () => void
  onKillSwitchChange: (active: boolean) => void
}): JSX.Element {
  const [settings, setSettings] = useState<SystemSettings | undefined>()

  useEffect(() => {
    apiCall<SystemSettings>('/settings')
      .then((s) => {
        setSettings(s)
        onKillSwitchChange(s.kill_switch.active)
      })
      .catch(() => {})
  }, [])

  const handleToggleKillSwitch = async (active: boolean) => {
    await apiCall('/settings/kill-switch', {
      method: 'POST',
      body: { active },
    })
    onKillSwitchChange(active)
  }

  return (
    <SettingsView
      session={session}
      settings={settings}
      onLogout={onLogout}
      onToggleKillSwitch={handleToggleKillSwitch}
    />
  )
}
