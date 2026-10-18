import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginPage } from '../pages/LoginPage'
import { mockFetch, TEST_USER } from './fetchMock'

afterEach(() => vi.unstubAllGlobals())

async function fillRegistration(confirm = 'supersecret') {
  await userEvent.click(screen.getByRole('tab', { name: 'Create account' }))
  await userEvent.type(screen.getByLabelText('Full name'), 'Jay Founder')
  await userEvent.type(screen.getByLabelText(/Company/), 'Jay Labs')
  await userEvent.type(screen.getByLabelText('Email'), 'jay@example.com')
  await userEvent.type(screen.getByLabelText('Password'), 'supersecret')
  await userEvent.type(screen.getByLabelText('Confirm password'), confirm)
  await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
}

describe('LoginPage', () => {
  it('signs in with email and password', async () => {
    const { calls } = mockFetch({
      'POST /auth/login': () => [200, { session_id: 'tok_1', user: TEST_USER }],
    })
    const onSuccess = vi.fn()
    render(<LoginPage onLoginSuccess={onSuccess} />)

    await userEvent.type(screen.getByLabelText('Email'), 'jay@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'password123')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith({ session_id: 'tok_1', user: TEST_USER }))
    expect(calls[0].body).toEqual({ email: 'jay@example.com', password: 'password123' })
  })

  it('shows an error for invalid credentials', async () => {
    mockFetch({ 'POST /auth/login': () => [401, { detail: 'Invalid email or password' }] })
    render(<LoginPage onLoginSuccess={vi.fn()} />)
    await userEvent.type(screen.getByLabelText('Email'), 'jay@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-pass')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password')
  })

  it('does not offer demo credentials', () => {
    render(<LoginPage onLoginSuccess={vi.fn()} />)
    expect(screen.queryByText(/demo/i)).not.toBeInTheDocument()
  })

  it('registers a new account', async () => {
    const { calls } = mockFetch({
      'POST /auth/register': () => [201, { session_id: 'tok_2', user: TEST_USER }],
    })
    const onSuccess = vi.fn()
    render(<LoginPage onLoginSuccess={onSuccess} />)
    await fillRegistration()

    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
    expect(calls[0].body).toEqual({
      name: 'Jay Founder',
      email: 'jay@example.com',
      password: 'supersecret',
      business_name: 'Jay Labs',
    })
  })

  it('validates password confirmation before calling the API', async () => {
    const { fn } = mockFetch({})
    render(<LoginPage onLoginSuccess={vi.fn()} />)
    await fillRegistration('different1')
    expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match')
    expect(fn).not.toHaveBeenCalled()
  })

  it('reports duplicate registrations', async () => {
    mockFetch({ 'POST /auth/register': () => [409, { detail: 'exists' }] })
    render(<LoginPage onLoginSuccess={vi.fn()} />)
    await fillRegistration()
    expect(await screen.findByRole('alert')).toHaveTextContent('already exists')
  })
})
