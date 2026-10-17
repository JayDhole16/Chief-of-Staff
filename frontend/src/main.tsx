/**
 * Application entry point: setup MSW (if enabled), mount React.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'
import { setupMSW } from './mocks/setup'
import './index.css'

async function init() {
  if (import.meta.env.VITE_USE_MSW === 'true') {
    try {
      await setupMSW()
    } catch (err) {
      // A mock failure must never white-screen the app; log and render anyway.
      console.error('[MSW] Setup failed; continuing without mocks:', err)
    }
  }

  // Register service worker for PWA
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch((err) => {
        console.warn('[SW] Registration failed:', err)
      })
    })
  }

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
}

init()
