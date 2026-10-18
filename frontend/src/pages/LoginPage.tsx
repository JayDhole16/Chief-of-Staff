/**
 * Auth page: sign in and registration, styled with the dashboard's emerald theme.
 */

import React, { useState } from 'react'
import { apiCall, APIClientError } from '../api/client'
import type { LoginRequest, LoginResponse, RegisterRequest } from '../api/types'
import { ApprovalIcon, KeyIcon, LogoStar, MailIcon, ShieldIcon } from '../components/Icons'

export interface LoginPageProps {
  onLoginSuccess: (response: LoginResponse) => void
}

type Mode = 'login' | 'register'

const FEATURES = [
  { icon: <ApprovalIcon size={18} />, title: 'Hash-bound approvals', text: 'Every outbound email is drafted, guard-checked and sent only after you approve the exact text.' },
  { icon: <ShieldIcon size={18} />, title: '15 deterministic guards', text: 'Discount ceilings, opt-outs, currency and sensitive-data checks run before anything leaves.' },
  { icon: <KeyIcon size={18} />, title: 'Your own AI keys', text: 'Bring your Anthropic, OpenAI, Gemini, Groq or OpenRouter key. See every token you spend.' },
  { icon: <MailIcon size={18} />, title: 'Sends from your inbox', text: 'Connect your own SMTP account so follow-ups go out from your address.' },
]

export function LoginPage({ onLoginSuccess }: LoginPageProps): JSX.Element {
  const [mode, setMode] = useState<Mode>('login')
  const [name, setName] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const isRegistering = mode === 'register'
  const canSubmit =
    !isLoading && email.trim() !== '' && password !== '' && (!isRegistering || (name.trim() !== '' && confirmPassword !== ''))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (isRegistering) {
      if (password.length < 8) {
        setError('Password must be at least 8 characters')
        return
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match')
        return
      }
    }
    setIsLoading(true)
    try {
      const response = await apiCall<LoginResponse>(isRegistering ? '/auth/register' : '/auth/login', {
        method: 'POST',
        body: isRegistering
          ? ({ name: name.trim(), email: email.trim(), password, business_name: businessName.trim() } satisfies RegisterRequest)
          : ({ email: email.trim(), password } satisfies LoginRequest),
      })
      onLoginSuccess(response)
    } catch (err) {
      if (err instanceof APIClientError) {
        if (err.code === 401) setError('Invalid email or password')
        else if (err.code === 409) setError('An account with this email already exists. Sign in instead.')
        else setError(err.message)
      } else {
        setError('An unexpected error occurred')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const switchMode = (next: Mode) => {
    setMode(next)
    setError(null)
    setPassword('')
    setConfirmPassword('')
  }

  return (
    <div className="cos-auth-shell">
      <section className="cos-auth-brand">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '16px',
              backgroundColor: '#091510',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: 'var(--emerald-glow)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            className="glow-emerald-sm"
          >
            <LogoStar size={24} />
          </div>
          <div>
            <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#FFFFFF' }}>Chief of Staff</div>
            <div style={{ fontSize: '0.68rem', color: 'var(--emerald-glow)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              Plan · Build · Execute
            </div>
          </div>
        </div>

        <div style={{ maxWidth: '460px' }}>
          <h2 style={{ fontSize: '2rem', lineHeight: 1.2, fontWeight: 800, color: '#FFFFFF', marginBottom: '0.75rem' }}>
            Your AI chief of staff for <span style={{ color: 'var(--emerald-glow)' }}>sales follow-ups</span>.
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', lineHeight: 1.6, marginBottom: '2rem' }}>
            Track your pipeline, catch deals going quiet, and send grounded follow-ups. Nothing goes out without your approval.
          </p>
          <div style={{ display: 'grid', gap: '1rem' }}>
            {FEATURES.map((f) => (
              <div key={f.title} style={{ display: 'flex', gap: '0.85rem', alignItems: 'flex-start' }}>
                <div
                  style={{
                    flexShrink: 0,
                    width: '34px',
                    height: '34px',
                    borderRadius: '10px',
                    backgroundColor: 'var(--emerald-tint)',
                    border: '1px solid var(--border-emerald)',
                    color: 'var(--emerald-glow)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {f.icon}
                </div>
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#FFFFFF' }}>{f.title}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>{f.text}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
          Passwords are salted and hashed (PBKDF2). API keys are encrypted at rest.
        </div>
      </section>

      <section className="cos-auth-form-wrap">
        <div
          style={{
            width: '100%',
            maxWidth: '420px',
            padding: '2.25rem',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: '1.25rem',
            border: '1px solid var(--border-hairline)',
            boxShadow: '0 24px 48px -12px rgba(0, 0, 0, 0.7), 0 0 24px -8px rgba(0, 255, 135, 0.15)',
          }}
        >
          <div
            role="tablist"
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              padding: '4px',
              backgroundColor: 'var(--bg-console)',
              border: '1px solid var(--border-hairline)',
              borderRadius: '12px',
              marginBottom: '1.5rem',
            }}
          >
            {(['login', 'register'] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={mode === m}
                onClick={() => switchMode(m)}
                disabled={isLoading}
                style={{
                  padding: '0.55rem',
                  borderRadius: '9px',
                  border: mode === m ? '1px solid rgba(16, 185, 129, 0.35)' : '1px solid transparent',
                  backgroundColor: mode === m ? '#0C1A14' : 'transparent',
                  color: mode === m ? 'var(--emerald-glow)' : 'var(--text-muted)',
                  fontWeight: 700,
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                {m === 'login' ? 'Sign in' : 'Create account'}
              </button>
            ))}
          </div>

          <h1 style={{ fontSize: '1.3rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '0.35rem' }}>
            {isRegistering ? 'Create your workspace' : 'Welcome back'}
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem', lineHeight: 1.5, marginBottom: '1.5rem' }}>
            {isRegistering
              ? 'Start with an empty, private workspace. Add your deals and your own AI key after signing up.'
              : 'Sign in to review approvals, manage deals and talk to your chief of staff.'}
          </p>

          <form onSubmit={handleSubmit} noValidate>
            {isRegistering && (
              <>
                <div style={{ marginBottom: '0.9rem' }}>
                  <label htmlFor="name" className="cos-label">Full name</label>
                  <input id="name" className="cos-input" type="text" value={name} onChange={(e) => setName(e.target.value)} disabled={isLoading} placeholder="Your name" autoComplete="name" required />
                </div>
                <div style={{ marginBottom: '0.9rem' }}>
                  <label htmlFor="business" className="cos-label">
                    Company <span className="cos-dim" style={{ fontWeight: 400 }}>(optional)</span>
                  </label>
                  <input id="business" className="cos-input" type="text" value={businessName} onChange={(e) => setBusinessName(e.target.value)} disabled={isLoading} placeholder="Your company" autoComplete="organization" />
                </div>
              </>
            )}

            <div style={{ marginBottom: '0.9rem' }}>
              <label htmlFor="email" className="cos-label">Email</label>
              <input id="email" className="cos-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={isLoading} placeholder="name@company.com" autoComplete="email" required />
            </div>

            <div style={{ marginBottom: isRegistering ? '0.9rem' : '1.4rem' }}>
              <label htmlFor="password" className="cos-label">Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  id="password"
                  className="cos-input"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  placeholder={isRegistering ? 'At least 8 characters' : '••••••••'}
                  autoComplete={isRegistering ? 'new-password' : 'current-password'}
                  required
                  style={{ paddingRight: '3.5rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  style={{ position: 'absolute', right: '0.6rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer' }}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            {isRegistering && (
              <div style={{ marginBottom: '1.4rem' }}>
                <label htmlFor="confirm-password" className="cos-label">Confirm password</label>
                <input id="confirm-password" className="cos-input" type={showPassword ? 'text' : 'password'} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} disabled={isLoading} placeholder="Re-enter your password" autoComplete="new-password" required />
              </div>
            )}

            {error && (
              <div role="alert" className="cos-alert cos-alert-error" style={{ marginBottom: '1rem' }}>
                {error}
              </div>
            )}

            <button type="submit" className="cos-btn cos-btn-primary" disabled={!canSubmit} style={{ width: '100%', padding: '0.8rem', fontSize: '0.92rem' }}>
              {isLoading ? (isRegistering ? 'Creating account...' : 'Signing in...') : isRegistering ? 'Create account' : 'Sign in'}
            </button>
          </form>

          <div style={{ marginTop: '1.1rem', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {isRegistering ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              type="button"
              onClick={() => switchMode(isRegistering ? 'login' : 'register')}
              disabled={isLoading}
              style={{ padding: 0, background: 'none', border: 'none', color: 'var(--emerald-glow)', font: 'inherit', fontWeight: 600, cursor: 'pointer' }}
            >
              {isRegistering ? 'Sign in' : 'Create one'}
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
