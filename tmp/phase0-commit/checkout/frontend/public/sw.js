/**
 * Service Worker: handles offline support, app shell caching.
 * DOES NOT cache API responses (keep them fresh).
 */

const CACHE_NAME = 'chief-of-staff-v1'
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/src/index.css',
  '/manifest.json',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        console.warn('[SW] Failed to cache some assets')
      })
    })
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // API requests: always fetch fresh (network first, no cache)
  if (url.pathname.startsWith('/api')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Don't cache API responses
          return response
        })
        .catch(() => {
          // Network error: return offline response
          return new Response(
            JSON.stringify({ error: { code: 'NETWORK', message: 'Offline' } }),
            { status: 503, headers: { 'Content-Type': 'application/json' } }
          )
        })
    )
    return
  }

  // Static assets: cache first
  event.respondWith(
    caches.match(request).then((response) => {
      if (response) {
        return response
      }

      return fetch(request)
        .then((response) => {
          // Only cache successful responses
          if (!response || response.status !== 200 || response.type === 'error') {
            return response
          }

          const responseToCache = response.clone()
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseToCache)
          })

          return response
        })
        .catch(() => {
          // Return offline page or error response
          return new Response('Offline - page not cached', {
            status: 503,
            statusText: 'Service Unavailable',
          })
        })
    })
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => cacheName !== CACHE_NAME)
          .map((cacheName) => caches.delete(cacheName))
      )
    })
  )
})
