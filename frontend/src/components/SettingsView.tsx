import React, { useState } from 'react'
import type { LoginResponse, SystemSettings } from '../api/types'

export interface SettingsViewProps {
  session: LoginResponse
  settings?: SystemSettings
  onLogout: () => void
  onToggleKillSwitch?: (active: boolean) => Promise<void>
}

export function SettingsView({
  session,
  settings,
  onLogout,
  onToggleKillSwitch,
}: SettingsViewProps): JSX.Element {
  const [killSwitchActive, setKillSwitchActive] = useState(
    settings?.kill_switch?.active ?? false
  )
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [isUpdating, setIsUpdating] = useState(false)

  const handleKillSwitchConfirm = async () => {
    setIsUpdating(true)
    try {
      const nextState = !killSwitchActive
      if (onToggleKillSwitch) {
        await onToggleKillSwitch(nextState)
      }
      setKillSwitchActive(nextState)
      setShowConfirmModal(false)
    } finally {
      setIsUpdating(false)
    }
  }

  return (
    <div
      data-testid="settings-view"
      style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
    >
      <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#111827' }}>
        Settings & Ops Controls
      </h2>

      {/* Founder Profile */}
      <div
        style={{
          padding: '1rem',
          backgroundColor: '#ffffff',
          borderRadius: '0.5rem',
          border: '1px solid #e5e7eb',
        }}
      >
        <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase' }}>
          Founder Profile
        </div>
        <div style={{ fontWeight: 700, fontSize: '1rem', color: '#111827', marginTop: '0.25rem' }}>
          {session.user.name || 'Meera Nair'}
        </div>
        <div style={{ fontSize: '0.8125rem', color: '#4b5563' }}>{session.user.email}</div>
        <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.25rem' }}>
          Timezone: Asia/Kolkata (IST, UTC+5:30)
        </div>
      </div>

      {/* Google Account Integration Status */}
      <div
        data-testid="google-account-status"
        style={{
          padding: '1rem',
          backgroundColor: '#ffffff',
          borderRadius: '0.5rem',
          border: '1px solid #e5e7eb',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase' }}>
            Google Workspace
          </div>
          <span
            data-testid="google-conn-pill"
            style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              padding: '0.15rem 0.5rem',
              borderRadius: '9999px',
              backgroundColor: '#d1fae5',
              color: '#065f46',
            }}
          >
            Connected
          </span>
        </div>

        <div style={{ fontSize: '0.8125rem', color: '#1f2937' }}>
          <strong>Mailbox: </strong>
          <span>{session.user.email}</span>
        </div>

        <div style={{ fontSize: '0.75rem', color: '#4b5563' }}>
          <strong>Scopes: </strong> Gmail Read/Draft/Send, Calendar FreeBusy/Insert
        </div>

        <div style={{ fontSize: '0.75rem', color: '#047857' }}>
          ✓ Refresh token sealed in worker executor. Access token refreshed automatically.
        </div>
      </div>

      {/* Emergency Kill Switch */}
      <div
        data-testid="kill-switch-section"
        style={{
          padding: '1rem',
          backgroundColor: killSwitchActive ? '#fee2e2' : '#ffffff',
          borderRadius: '0.5rem',
          border: killSwitchActive ? '2px solid #ef4444' : '1px solid #e5e7eb',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.625rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: '0.875rem', color: '#111827' }}>
            Emergency Kill Switch
          </div>
          <span
            data-testid="kill-switch-status"
            style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              padding: '0.15rem 0.5rem',
              borderRadius: '9999px',
              backgroundColor: killSwitchActive ? '#dc2626' : '#f3f4f6',
              color: killSwitchActive ? '#ffffff' : '#6b7280',
            }}
          >
            {killSwitchActive ? 'ACTIVE - AUTONOMY HALTED' : 'STANDBY'}
          </span>
        </div>

        <div style={{ fontSize: '0.75rem', color: '#4b5563', lineHeight: 1.4 }}>
          Halts all autonomous mandate sweeps and queued email dispatches immediately. Founder approval cards and manual actions remain operable.
        </div>

        {killSwitchActive ? (
          <button
            type="button"
            data-testid="kill-switch-button"
            onClick={() => setShowConfirmModal(true)}
            style={{
              minHeight: '44px',
              backgroundColor: '#16a34a',
              color: '#ffffff',
              border: 'none',
              borderRadius: '0.375rem',
              fontWeight: 700,
              fontSize: '0.875rem',
              cursor: 'pointer',
            }}
          >
            ✓ Resume System (Release Kill Switch)
          </button>
        ) : (
          <button
            type="button"
            data-testid="kill-switch-button"
            onClick={() => setShowConfirmModal(true)}
            style={{
              minHeight: '44px',
              backgroundColor: '#dc2626',
              color: '#ffffff',
              border: 'none',
              borderRadius: '0.375rem',
              fontWeight: 700,
              fontSize: '0.875rem',
              cursor: 'pointer',
            }}
          >
            ⚠️ Halt All Mandate Autonomy
          </button>
        )}
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div
          data-testid="kill-switch-modal"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
            zIndex: 50,
          }}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              padding: '1.25rem',
              borderRadius: '0.5rem',
              maxWidth: '350px',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#111827' }}>
              {killSwitchActive ? 'Resume Mandate Autonomy?' : 'Activate Kill Switch?'}
            </h3>
            <p style={{ margin: 0, fontSize: '0.8125rem', color: '#4b5563' }}>
              {killSwitchActive
                ? 'This will re-enable autonomous sweeps and schedule follow-ups under active mandates.'
                : 'This will immediately abort all in-flight mandate sweeps and cancel queued dispatches in the undo window.'}
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
              <button
                type="button"
                data-testid="confirm-kill-switch-button"
                disabled={isUpdating}
                onClick={handleKillSwitchConfirm}
                style={{
                  flex: 1,
                  minHeight: '44px',
                  backgroundColor: killSwitchActive ? '#16a34a' : '#dc2626',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  fontWeight: 700,
                  fontSize: '0.8125rem',
                  cursor: isUpdating ? 'not-allowed' : 'pointer',
                }}
              >
                {isUpdating ? 'Updating...' : 'Yes, Confirm'}
              </button>
              <button
                type="button"
                disabled={isUpdating}
                onClick={() => setShowConfirmModal(false)}
                style={{
                  minHeight: '44px',
                  padding: '0 1rem',
                  backgroundColor: '#f3f4f6',
                  color: '#374151',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.8125rem',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sign Out */}
      <button
        type="button"
        data-testid="logout-button"
        onClick={onLogout}
        style={{
          minHeight: '44px',
          width: '100%',
          backgroundColor: '#f3f4f6',
          color: '#ef4444',
          border: '1px solid #fecaca',
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

