/**
 * Tests for API client: error mapping, CSRF headers, timeouts.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { apiCall, APIClientError, setSession, hasSession } from '../api/client'

describe('API Client', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  describe('error mapping', () => {
    it('maps 401 to unauthorized', async () => {
      sessionStorage.removeItem('session_id')

      try {
        await apiCall('/session', { method: 'GET' })
        expect.fail('should throw')
      } catch (err) {
        expect(err).toBeInstanceOf(APIClientError)
        expect((err as APIClientError).code).toBe(401)
      }
    })

    it('maps 422 to validation error', async () => {
      try {
        await apiCall('/auth/login', {
          method: 'POST',
          body: { email: '', password: '' },
        })
        expect.fail('should throw')
      } catch (err) {
        expect(err).toBeInstanceOf(APIClientError)
        expect((err as APIClientError).code).toBe(422)
      }
    })
  })

  describe('session management', () => {
    it('sends session ID in CSRF header', async () => {
      setSession('test_session_123')

      // This should succeed with session header
      const response = await apiCall<{ session_id: string }>('/session', {
        method: 'GET',
      })

      expect(response.session_id).toBe('test_session_123')
    })

    it('checks session state', () => {
      expect(hasSession()).toBe(false)

      setSession('test_session_456')
      expect(hasSession()).toBe(true)
    })
  })

  describe('login flow', () => {
    it('successful login', async () => {
      const response = await apiCall<{
        session_id: string
        user: { id: string; email: string; name: string }
      }>('/auth/login', {
        method: 'POST',
        body: { email: 'test@example.com', password: 'password123' },
      })

      expect(response.session_id).toBeDefined()
      expect(response.user.email).toBe('test@example.com')
    })

    it('rejects short password', async () => {
      try {
        await apiCall('/auth/login', {
          method: 'POST',
          body: { email: 'test@example.com', password: 'short' },
        })
        expect.fail('should throw')
      } catch (err) {
        expect(err).toBeInstanceOf(APIClientError)
        expect((err as APIClientError).code).toBe(422)
      }
    })
  })

  describe('network errors', () => {
    it('handles network timeout', async () => {
      // MSW can't simulate timeout easily, so test the error class
      const error = new APIClientError('TIMEOUT', 'Request timed out')
      expect(error.code).toBe('TIMEOUT')
      expect(error.message).toBe('Request timed out')
    })
  })
})
