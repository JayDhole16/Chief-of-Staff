/**
 * Test setup: jest-dom matchers and a clean localStorage per test.
 */

import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

afterEach(() => {
  cleanup()
  localStorage.clear()
})
