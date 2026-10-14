/**
 * Tests for login flow: form submission, error handling, session storage.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginPage } from '../pages/LoginPage'

describe('Login Flow', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('renders login form', () => {
    const onLoginSuccess = vi.fn()
    render(<LoginPage onLoginSuccess={onLoginSuccess} />)

    expect(screen.getByText('Chief of Staff')).toBeInTheDocument()
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sign in/i })).toBeInTheDocument()
  })

  it('submits login form', async () => {
    const onLoginSuccess = vi.fn()
    render(<LoginPage onLoginSuccess={onLoginSuccess} />)

    const emailInput = screen.getByLabelText(/Email/i)
    const passwordInput = screen.getByLabelText(/Password/i)
    const submitButton = screen.getByRole('button', { name: /Sign in/i })

    await userEvent.type(emailInput, 'test@example.com')
    await userEvent.type(passwordInput, 'password123')
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(onLoginSuccess).toHaveBeenCalled()
    })
  })

  it('displays validation error on failed login', async () => {
    const onLoginSuccess = vi.fn()
    render(<LoginPage onLoginSuccess={onLoginSuccess} />)

    const emailInput = screen.getByLabelText(/Email/i)
    const passwordInput = screen.getByLabelText(/Password/i)
    const submitButton = screen.getByRole('button', { name: /Sign in/i })

    await userEvent.type(emailInput, 'test@example.com')
    await userEvent.type(passwordInput, 'short') // Too short
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/Invalid email or password/i)).toBeInTheDocument()
    })

    expect(onLoginSuccess).not.toHaveBeenCalled()
  })

  it('disables button during submission', async () => {
    const onLoginSuccess = vi.fn()
    render(<LoginPage onLoginSuccess={onLoginSuccess} />)

    const emailInput = screen.getByLabelText(/Email/i)
    const passwordInput = screen.getByLabelText(/Password/i)
    const submitButton = screen.getByRole('button', { name: /Sign in/i })

    await userEvent.type(emailInput, 'test@example.com')
    await userEvent.type(passwordInput, 'password123')
    await userEvent.click(submitButton)

    expect(submitButton).toBeDisabled()

    await waitFor(() => {
      expect(submitButton).not.toBeDisabled()
    })
  })

  it('stores session in sessionStorage', async () => {
    const onLoginSuccess = vi.fn()
    render(<LoginPage onLoginSuccess={onLoginSuccess} />)

    const emailInput = screen.getByLabelText(/Email/i)
    const passwordInput = screen.getByLabelText(/Password/i)
    const submitButton = screen.getByRole('button', { name: /Sign in/i })

    await userEvent.type(emailInput, 'test@example.com')
    await userEvent.type(passwordInput, 'password123')
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(sessionStorage.getItem('session_id')).toBeDefined()
    })
  })
})
