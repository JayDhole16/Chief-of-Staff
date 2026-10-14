/**
 * MSW setup: only enable if VITE_USE_MSW=true.
 * Allows safe mocking in dev without shipping mock logic to production.
 */

import { setupServer } from 'msw/node'
import { handlers } from './handlers'

let server: ReturnType<typeof setupServer> | null = null

/**
 * Start MSW server (call once at app startup if USE_MSW is true).
 */
export function setupMSW(): void {
  if (import.meta.env.VITE_USE_MSW !== 'true') {
    console.info('[MSW] Disabled (set VITE_USE_MSW=true to enable)')
    return
  }

  if (server) return // Already started

  console.info('[MSW] Starting mock server handlers...')
  server = setupServer(...handlers)
  server.listen({ onUnhandledRequest: 'warn' })
}

/**
 * Stop MSW server (cleanup).
 */
export function stopMSW(): void {
  if (server) {
    server.close()
    server = null
  }
}
