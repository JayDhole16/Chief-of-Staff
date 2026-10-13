# Chief of Staff PWA Frontend

Mobile-first PWA built with React + TypeScript + Vite, using MSW for mocking API calls during development.

## Quick Start

### Install dependencies
```bash
npm install
```

### Run with MSW mocks (development)
```bash
npm run dev
```

This starts the dev server with MSW mocks **enabled** (VITE_USE_MSW=true). All API calls are intercepted and mocked:
- **Login**: POST /auth/login (any email, password ≥6 chars)
- **Session**: GET /session (requires X-Session-ID header)
- **Activity**: GET /activity (mocked events)
- **Approvals**: GET /approvals/pending (1 pending deal)
- **Pipeline**: GET /pipeline/deals (2 deals)

**Demo credentials**:
- Email: `test@example.com`
- Password: `password123`

### Run tests
```bash
npm test              # Watch mode
npm test -- --run    # Single run
npm test:ui          # UI dashboard
```

### Build for production
```bash
npm run build
```

This disables MSW (VITE_USE_MSW=false) and points to live API at `/api`.

## Project Structure

```
src/
├── api/                 # API client, types, error handling
│   ├── client.ts       # Fetch wrapper (only place fetch is called)
│   └── types.ts        # Request/response types
├── mocks/              # MSW request handlers (dev-only)
│   ├── handlers.ts     # Login, session, activity, etc.
│   └── setup.ts        # MSW initialization
├── hooks/              # React hooks
│   └── usePolling.ts   # Interval polling with backoff + visibility
├── components/         # UI components
│   ├── LoadingSkeletons.tsx
│   └── ErrorBoundary.tsx
├── pages/              # Page components
│   ├── LoginPage.tsx
│   └── DashboardPage.tsx
├── tests/              # Vitest + Testing Library
├── App.tsx             # Main app component
├── main.tsx            # App entry point (MSW setup)
└── index.css           # Global styles (mobile-first, 390px)

public/
├── manifest.json       # PWA manifest
├── sw.js              # Service worker (caches static assets, NOT API)
├── icon-192.png       # Placeholder
└── icon-512.png       # Placeholder
```

## Key Features

### 1. Typed API Client
- Single fetch wrapper (`apiCall`) with error mapping
- Typed requests/response (no `any`)
- Error codes: 401, 403, 409, 422, 500, NETWORK, TIMEOUT
- CSRF header support (X-Requested-With)
- Session ID stored in sessionStorage (cleared on tab close)

### 2. MSW Mocks (Dev-Only)
- Gated by `VITE_USE_MSW` environment variable
- Handlers in `src/mocks/handlers.ts` (never shipped to prod)
- Mock data stored in memory during dev
- Simulates network latency (300ms)

### 3. usePolling Hook
- Configurable interval
- Pauses when tab is hidden (visibility API)
- Exponential backoff on error (1x, 2x, 4x, ..., capped at 10x)
- Retry button to reset backoff
- Cleans up timers on unmount

### 4. Global States
- Loading skeletons (for content placeholders)
- Empty state (no data message)
- Error state (with retry button)
- Offline banner (shows when navigator.onLine = false)

### 5. PWA Basics
- Manifest file (192x512px icon placeholders)
- Service worker that:
  - **Caches static assets** (HTML, CSS, JS)
  - **Does NOT cache API responses** (always fetch fresh)
  - **Returns offline response** on network error
- Installable on mobile/desktop

### 6. Mobile-First Layout
- Default: 390px viewport (common mobile size)
- Bottom tab navigation: Command, Approvals, Activity, Pipeline, Settings
- Responsive typography (scales on larger screens)

## Environment Variables

### Development (.env.development)
```
VITE_USE_MSW=true              # Enable MSW
VITE_API_BASE=http://localhost:8000/api
```

### Production (.env.production)
```
VITE_USE_MSW=false             # Disable MSW (safe to remove from bundle)
VITE_API_BASE=/api             # Relative API path
```

## Running MSW in Tests

Tests automatically enable MSW via `src/tests/setup.ts`. The MSW server is started before all tests and stopped after.

Example test:
```typescript
it('successful login', async () => {
  const response = await apiCall<LoginResponse>('/auth/login', {
    method: 'POST',
    body: { email: 'test@example.com', password: 'password123' },
  })
  expect(response.session_id).toBeDefined()
})
```

## Design Principles

1. **Pure API client**: All fetch calls go through `apiCall()`. No direct `fetch()` anywhere.
2. **Session in-memory**: sessionStorage is cleared on tab close (no persistent tokens).
3. **Type safety**: Request/response types defined in `src/api/types.ts`. Use them everywhere.
4. **MSW isolation**: Mock handlers live in `src/mocks/`, gated by env flag. Never shipped to production.
5. **Deterministic**: All hooks have cleanup (timers, event listeners). Tests are repeatable.
6. **Mobile-first**: Layout designed for 390px, scales up gracefully.

## Common Tasks

### Add a new API endpoint

1. Add type in `src/api/types.ts`:
   ```typescript
   export interface NewThingResponse {
     items: Array<{ id: string }>
   }
   ```

2. Add MSW handler in `src/mocks/handlers.ts`:
   ```typescript
   http.get(`${API_BASE}/new-thing`, () => {
     return HttpResponse.json({ items: [] })
   })
   ```

3. Call it in a component:
   ```typescript
   const data = await apiCall<NewThingResponse>('/new-thing')
   ```

### Switch to live API

1. Set `VITE_USE_MSW=false` in `.env`
2. Set `VITE_API_BASE=https://api.example.com` (or your backend URL)
3. Rebuild: `npm run build`

### Debug MSW

MSW logs to console when requests don't match any handler. Search for `[MSW]` in browser console.

To disable MSW warnings:
```typescript
setupServer(...handlers).listen({ onUnhandledRequest: 'bypass' })
```

## Troubleshooting

### Q: API calls always return 401
A: Check that sessionStorage has `session_id`. After login, it should be set automatically.

### Q: Service worker not updating
A: Clear site data in DevTools, then reload. SW updates on next reload after code change.

### Q: Tests failing with "Unhandled request"
A: Add the handler to `src/mocks/handlers.ts` and make sure setup.ts is running.

## Performance Tips

- Service worker caches static assets (2-3 sec faster on reload)
- usePolling pauses when tab is hidden (saves battery on mobile)
- Exponential backoff prevents hammering API on errors
- Image placeholders (icon-192.png, icon-512.png) keep manifest size small

---

Built with React, TypeScript, Vite, MSW, Vitest, and Testing Library.
