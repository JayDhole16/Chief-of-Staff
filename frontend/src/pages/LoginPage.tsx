/**
 * Login page: form that posts to /auth/login (mocked or live).
 * Session stored in sessionStorage (in-memory for session, survives tab reload).
 */

import React, { useState } from 'react'
import { apiCall, setSession, APIClientError } from '../api/client'
import type { LoginRequest, LoginResponse } from '../api/types'

export interface LoginPageProps {
  onLoginSuccess: (response: LoginResponse) => void
}

export function LoginPage({ onLoginSuccess }: LoginPageProps): JSX.Element {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      const response = await apiCall<LoginResponse>('/auth/login', {
        method: 'POST',
        body: { email, password } as LoginRequest,
      })

      setSession(response.session_id)
      onLoginSuccess(response)
    } catch (err) {
      if (err instanceof APIClientError) {
        setError(
          err.code === 422 ? 'Invalid email or password' : `Error: ${err.message}`
        )
      } else {
        setError('An unexpected error occurred')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleFillDemo = () => {
    setEmail('meera@agency.in')
    setPassword('password123')
    setError(null)
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#07090C',
        color: '#F1F5F9',
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '410px',
          padding: '2.25rem',
          backgroundColor: '#10141C',
          borderRadius: '1.25rem',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 24px 48px -12px rgba(0, 0, 0, 0.7), 0 0 24px -8px rgba(0, 255, 135, 0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '14px',
              backgroundColor: '#091510',
              border: '1px solid rgba(16, 185, 129, 0.45)',
              color: '#00FF87',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 14px -2px rgba(0, 255, 135, 0.35)',
            }}
          >
            <svg style={{ width: '22px', height: '22px' }} viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0L14.6 9.4L24 12L14.6 14.6L12 24L9.4 14.6L0 12L9.4 9.4L12 0Z" />
            </svg>
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 800, color: '#FFFFFF' }}>
              Chief of Staff
            </h1>
            <div style={{ fontSize: '0.7rem', color: '#00FF87', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              Plan · Build · Execute
            </div>
          </div>
        </div>

        <p style={{ margin: '0 0 1.75rem 0', color: '#94A3B8', fontSize: '0.85rem', lineHeight: 1.5 }}>
          Sign in to your account to manage deals, review hash-bound approvals, and command your autonomous sales operations.
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label
              htmlFor="email"
              style={{
                display: 'block',
                marginBottom: '0.45rem',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: '#CBD5E1',
              }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              placeholder="name@example.com"
              style={{
                width: '100%',
                padding: '0.75rem 0.9rem',
                backgroundColor: '#080B0F',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '0.625rem',
                fontSize: '0.9375rem',
                color: '#FFFFFF',
                boxSizing: 'border-box',
                outline: 'none',
              }}
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label
              htmlFor="password"
              style={{
                display: 'block',
                marginBottom: '0.45rem',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: '#CBD5E1',
              }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              placeholder="••••••••"
              style={{
                width: '100%',
                padding: '0.75rem 0.9rem',
                backgroundColor: '#080B0F',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '0.625rem',
                fontSize: '0.9375rem',
                color: '#FFFFFF',
                boxSizing: 'border-box',
                outline: 'none',
              }}
            />
          </div>

          {error && (
            <div
              role="alert"
              style={{
                marginBottom: '1rem',
                padding: '0.75rem',
                backgroundColor: 'rgba(244, 63, 94, 0.12)',
                border: '1px solid rgba(244, 63, 94, 0.4)',
                borderRadius: '0.5rem',
                color: '#FDA4AF',
                fontSize: '0.8125rem',
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !email || !password}
            style={{
              width: '100%',
              padding: '0.8rem',
              backgroundColor: isLoading || !email || !password ? '#1E293B' : '#10B981',
              color: isLoading || !email || !password ? '#64748B' : '#050709',
              border: 'none',
              borderRadius: '0.625rem',
              fontSize: '0.9375rem',
              fontWeight: 700,
              cursor: isLoading || !email || !password ? 'not-allowed' : 'pointer',
              transition: 'all 0.18s ease',
            }}
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div
          style={{
            marginTop: '1.25rem',
            paddingTop: '1rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.07)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.75rem',
            color: '#94A3B8',
            textAlign: 'center',
          }}
        >
          <div>Demo credentials: test@example.com / password123</div>
          <button
            type="button"
            onClick={handleFillDemo}
            style={{
              background: 'rgba(0, 255, 135, 0.08)',
              border: '1px solid rgba(0, 255, 135, 0.25)',
              color: '#00FF87',
              padding: '0.3rem 0.75rem',
              borderRadius: '9999px',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            ⚡ Quick Fill Founder Credentials
          </button>
        </div>
      </div>
    </div>
  )
}
