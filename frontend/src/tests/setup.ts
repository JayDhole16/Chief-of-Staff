/**
 * Test setup: enable MSW for all tests.
 */

import { setupServer } from 'msw/node'
import { beforeAll, afterEach, afterAll } from 'vitest'
import { handlers } from '../mocks/handlers'
import '@testing-library/jest-dom/vitest'


// Ensure window.AbortController and window.AbortSignal are node's global built-in classes
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'AbortController', {
    value: globalThis.AbortController,
    writable: true,
    configurable: true,
  })
  Object.defineProperty(window, 'AbortSignal', {
    value: globalThis.AbortSignal,
    writable: true,
    configurable: true,
  })
}



const server = setupServer(...handlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
