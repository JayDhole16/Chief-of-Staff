/**
 * Main dashboard with bottom tab navigation (390px mobile-first).
 * Tabs: Command, Approvals, Activity, Pipeline, Settings.
 */

import React, { useState } from 'react'
import type { LoginResponse } from '../api/types'

export interface DashboardPageProps {
  session: LoginResponse
  onLogout: () => void
}

type TabId = 'command' | 'approvals' | 'activity' | 'pipeline' | 'settings'

const TABS: Array<{ id: TabId; label: string; icon: string }> = [
  { id: 'command', label: 'Command', icon: '⚡' },
  { id: 'approvals', label: 'Approvals', icon: '✓' },
  { id: 'activity', label: 'Activity', icon: '📋' },
  { id: 'pipeline', label: 'Pipeline', icon: '📊' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
]

export function DashboardPage({ session, onLogout }: DashboardPageProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>('command')

  const renderTabContent = () => {
    switch (activeTab) {
      case 'command':
        return <CommandTab />
      case 'approvals':
        return <ApprovalsTab />
      case 'activity':
        return <ActivityTab />
      case 'pipeline':
        return <PipelineTab />
      case 'settings':
        return <SettingsTab session={session} onLogout={onLogout} />
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
          padding: '1rem',
          backgroundColor: 'white',
          borderBottom: '1px solid #e5e7eb',
        }}
      >
        <h1 style={{ margin: '0', fontSize: '1.25rem', color: '#111827' }}>
          Chief of Staff
        </h1>
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
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1,
              padding: '0.75rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '0.25rem',
              border: 'none',
              backgroundColor: activeTab === tab.id ? '#f0f4ff' : 'transparent',
              borderTop: activeTab === tab.id ? '3px solid #3b82f6' : 'none',
              cursor: 'pointer',
              color: activeTab === tab.id ? '#3b82f6' : '#6b7280',
              fontSize: '0.75rem',
              fontWeight: 500,
            }}
          >
            <span style={{ fontSize: '1.25rem' }}>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  )
}

function CommandTab(): JSX.Element {
  return (
    <div>
      <h2 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Quick Commands</h2>
      <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
        Coming soon: trigger actions via natural language
      </p>
    </div>
  )
}

function ApprovalsTab(): JSX.Element {
  return (
    <div>
      <h2 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Pending Approvals</h2>
      <div
        style={{
          padding: '1rem',
          border: '1px solid #e5e7eb',
          borderRadius: '0.5rem',
          backgroundColor: 'white',
        }}
      >
        <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem' }}>
          Summer Clearance Deal
        </h3>
        <p style={{ margin: '0.5rem 0', fontSize: '0.75rem', color: '#6b7280' }}>
          ₹12,50,000 offer requires approval
        </p>
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
          <button
            style={{
              flex: 1,
              padding: '0.5rem',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              cursor: 'pointer',
            }}
          >
            Approve
          </button>
          <button
            style={{
              flex: 1,
              padding: '0.5rem',
              backgroundColor: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              cursor: 'pointer',
            }}
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  )
}

function ActivityTab(): JSX.Element {
  return (
    <div>
      <h2 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Activity Feed</h2>
      <div
        style={{
          padding: '1rem',
          border: '1px solid #e5e7eb',
          borderRadius: '0.5rem',
          backgroundColor: 'white',
          marginBottom: '0.75rem',
        }}
      >
        <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 600 }}>
          Deal approved
        </p>
        <p style={{ margin: '0', fontSize: '0.75rem', color: '#6b7280' }}>
          Summer clearance deal approved
        </p>
      </div>
      <div
        style={{
          padding: '1rem',
          border: '1px solid #e5e7eb',
          borderRadius: '0.5rem',
          backgroundColor: 'white',
        }}
      >
        <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 600 }}>
          Email sent
        </p>
        <p style={{ margin: '0', fontSize: '0.75rem', color: '#6b7280' }}>
          Approval notification sent to customer
        </p>
      </div>
    </div>
  )
}

function PipelineTab(): JSX.Element {
  return (
    <div>
      <h2 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Sales Pipeline</h2>
      <div
        style={{
          padding: '1rem',
          border: '1px solid #e5e7eb',
          borderRadius: '0.5rem',
          backgroundColor: 'white',
          marginBottom: '0.75rem',
        }}
      >
        <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 600 }}>
          Summer Clearance
        </p>
        <p style={{ margin: '0', fontSize: '0.75rem', color: '#6b7280' }}>
          Stage: Negotiation | Value: ₹12,50,000
        </p>
      </div>
      <div
        style={{
          padding: '1rem',
          border: '1px solid #e5e7eb',
          borderRadius: '0.5rem',
          backgroundColor: 'white',
        }}
      >
        <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 600 }}>
          B2B Partnership
        </p>
        <p style={{ margin: '0', fontSize: '0.75rem', color: '#6b7280' }}>
          Stage: Lead | Value: ₹25,00,000
        </p>
      </div>
    </div>
  )
}

interface SettingsTabProps {
  session: LoginResponse
  onLogout: () => void
}

function SettingsTab({ session, onLogout }: SettingsTabProps): JSX.Element {
  return (
    <div>
      <h2 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Settings</h2>
      <div
        style={{
          padding: '1rem',
          border: '1px solid #e5e7eb',
          borderRadius: '0.5rem',
          backgroundColor: 'white',
          marginBottom: '1rem',
        }}
      >
        <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 600 }}>
          {session.user.name}
        </p>
        <p style={{ margin: '0', fontSize: '0.75rem', color: '#6b7280' }}>
          {session.user.email}
        </p>
      </div>
      <button
        onClick={onLogout}
        style={{
          width: '100%',
          padding: '0.75rem',
          backgroundColor: '#ef4444',
          color: 'white',
          border: 'none',
          borderRadius: '0.375rem',
          fontSize: '0.875rem',
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        Sign out
      </button>
    </div>
  )
}
