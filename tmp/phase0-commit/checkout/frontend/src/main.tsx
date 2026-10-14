/**
 * Application entry point: setup MSW (if enabled), mount React.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'
import { setupMSW } from './mocks/setup'
import './index.css'

// Setup MSW mock server if VITE_USE_MSW=true
setupMSW()

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
