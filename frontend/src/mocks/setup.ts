/**
 * MSW setup: only enable if VITE_USE_MSW=true.
 * Uses setupWorker for browser dev without shipping Node dependencies to production.
 */

import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

let worker: ReturnType<typeof setupWorker> | null = null

/**
 * Start MSW worker (call once at app startup if USE_MSW is true).
 */
export async function setupMSW(): Promise<void> {
  if (import.meta.env.VITE_USE_MSW !== 'true') {
    return
  }

  if (worker) return // Already started

  console.info('[MSW] Starting mock worker handlers...')
  worker = setupWorker(...handlers)
  await worker.start({ onUnhandledRequest: 'bypass' })
}

/**
 * Stop MSW worker (cleanup).
 */
export function stopMSW(): void {
  if (worker) {
    worker.stop()
    worker = null
  }
}
