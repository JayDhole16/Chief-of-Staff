# Chief-of-Staff

An AI chief of staff for founders. Track your deals, see which ones are going quiet,
and let the assistant draft grounded follow-up emails. Every draft is bound to a
SHA-256 hash of its exact text and checked by 15 deterministic policy guards. Nothing
is sent until you approve that exact text.

- **Accounts:** register and sign in (PBKDF2-hashed passwords, expiring server-side sessions).
- **Private workspaces:** every deal, draft, receipt, chat and key is scoped to its owner.
  A new account starts empty; there is no demo data.
- **Bring your own AI key:** each user adds their own Anthropic, OpenAI, Gemini, Groq,
  OpenRouter or any OpenAI-compatible key in **API Keys**. Keys are encrypted at rest
  (Fernet), shown only masked, and every request's token usage is recorded per
  provider and model so users can see what they spend.
- **Sends from your mailbox:** connect your own SMTP account (Gmail app password,
  Outlook, Zoho...). Without SMTP, approved drafts are recorded for manual sending.
- **Safety:** policy guards (discount ceiling, opt-out, currency, sensitive data,
  grounding of amounts), hash-bound approvals with 409 on stale or tampered drafts,
  and a per-user kill switch that pauses all drafting and sending.

## Live deployment (Vercel)

| Part | URL | Vercel project |
|---|---|---|
| Web app | https://chief-of-staff-app-kappa.vercel.app | `chief-of-staff-app` (from `frontend/`) |
| API | https://chief-of-staff-eight-sigma.vercel.app ([/docs](https://chief-of-staff-eight-sigma.vercel.app/docs)) | `chief-of-staff` (repo root, FastAPI function) |
| Database | Neon Postgres (free, via the Vercel Marketplace) | attached to `chief-of-staff` |

The browser calls the API directly (`VITE_API_BASE`), and the API allows that origin
through `CORS_ORIGINS`. Production environment variables:

- **API (`chief-of-staff`):** `DATABASE_URL` (set by Neon), `APP_ENCRYPTION_KEY`,
  `CORS_ORIGINS` and `APP_BASE_URL` (the web app URL), `PUBLIC_API_URL` (the API URL),
  `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
- **Web (`chief-of-staff-app`):** `VITE_API_BASE=https://chief-of-staff-eight-sigma.vercel.app/api`

Redeploy after changes: `vercel deploy --prod` from the repo root (API) and from
`frontend/` (web). Config lives in `vercel.json`, `.vercelignore`,
`frontend/vercel.json` and `[tool.vercel]` in `pyproject.toml`; the API function may
run for up to 300 s, which covers slow AI calls.

For Google sign-in on the live site, also register this redirect URI in Google Cloud:
`https://chief-of-staff-eight-sigma.vercel.app/api/integrations/google/callback`

## Run it with Docker (PostgreSQL)

```bash
cp .env.example .env          # set POSTGRES_PASSWORD and APP_ENCRYPTION_KEY (see comments)
docker compose up -d --build  # db (Postgres 16), API :8080, web :3000, worker :8081
python scripts/smoke_app.py   # probes web, API proxy, readiness and worker
```

Open http://localhost:3000. Postgres data lives on the `postgres_data` volume; the
database is also published on `127.0.0.1:5433` (5432 is often taken by a local install).

## Run it locally (hot reload)

Requirements: Python 3.10+, Node 22, and Docker for the database.

```bash
cp .env.example .env                                          # once
docker compose up -d db                                       # Postgres on 127.0.0.1:5433
python -m pip install -e ".[dev]"
python -m uvicorn backend.main:app --port 8000 --reload      # or: make dev-api (reads .env)

cd frontend && npm ci && npm run dev                          # or: make dev-web → http://localhost:5173
```

The API reads `DATABASE_URL` from `.env`. Use `127.0.0.1`, not `localhost`: on Windows,
`localhost` tries IPv6 first and every connection stalls for seconds. Leave
`DATABASE_URL` empty to fall back to SQLite at `data/app.db`.

## Google sign-in (Gmail + Calendar)

Optional. When it's enabled, each user can click **Connect Google** (API Keys page) to send
approved follow-ups from their own Gmail and book meetings with Google Meet links on
their calendar. Only two permissions are requested: `gmail.send` and `calendar.events`.
The app never reads the inbox. Setup is a one-time job for the app owner:

1. In [Google Cloud Console](https://console.cloud.google.com/), create or select a project.
2. **APIs & Services → Library**: enable **Gmail API** and **Google Calendar API**.
3. **Google Auth Platform** (OAuth consent screen): choose *External*, set the app name
   and support email, and under **Audience** add every Google account that will connect
   as a *test user*.
4. **Credentials → Create credentials → OAuth client ID → Web application**, with these
   authorized redirect URIs:
   - `http://localhost:5173/api/integrations/google/callback` (local dev)
   - `http://localhost:3000/api/integrations/google/callback` (Docker)
5. Put the client ID and secret in `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`,
   then restart the API (`docker compose up -d api`, or restart uvicorn).

While the app is in *Testing* mode, Google shows an "unverified app" warning (choose
*Continue*) and refresh tokens expire after 7 days, so users reconnect weekly. Publishing
the app requires Google's verification for these scopes.

Sending order on approval: **Gmail** if connected, otherwise **SMTP** if configured,
otherwise the draft is recorded for manual sending. Meetings need Google. Before you
approve, the calendar is checked for conflicts, and the event's time and attendee are
part of the approval hash.

## Using the app

No AI keys are configured on the server. Each user brings their own:

1. Create an account. The **Overview** page shows a *Connect your AI provider* card:
   pick Anthropic, OpenAI, Gemini, Groq, OpenRouter or any OpenAI-compatible endpoint,
   paste your key, and press *Save & test key*. Usage is billed to your own provider
   account, and **API Keys** shows the tokens each model has used.
2. **Deals** → add deals with contact name, email, value and last-contact date.
3. **Deals → Draft follow-up** (or *Draft for all quiet deals*) → review the draft in
   **Approvals**, edit if needed, then *Approve & send*.
4. **Chat** → ask about your pipeline; answers are grounded in your own data.
5. *(Optional)* **API Keys → Connect Google** (Gmail + Calendar) or **Email sending (SMTP)** so
   approvals send real email; with Google, **Deals → Schedule meeting** books calendar invites.

Saved API keys and SMTP passwords are encrypted with `APP_ENCRYPTION_KEY` (or a key
generated once at `APP_KEY_FILE`). The Docker API and a locally run API share one
database, so keep the same key in `.env` for both. Losing the key makes saved keys
unreadable.

## Tests

```bash
python -m pytest -q                       # backend on SQLite; Postgres variants skip
# Same suite on PostgreSQL too (uses a separate database; tables in it are dropped):
docker compose exec db createdb -U chief_of_staff chief_of_staff_test
DATABASE_URL=postgresql://chief_of_staff:<password>@127.0.0.1:5433/chief_of_staff_test python -m backend.db.migrate
POSTGRES_TEST_DATABASE_URL=postgresql://chief_of_staff:<password>@127.0.0.1:5433/chief_of_staff_test python -m pytest -q
cd frontend && npm test -- --run          # frontend
cd frontend && npm run build              # type-check + production bundle
```

LLM and SMTP calls are faked in the tests, so no network or keys are needed.

## API overview

All routes except auth and health require the `X-Session-ID` header (or
`Authorization: Bearer <session>`).

| Area | Routes |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/session` |
| Profile | `GET/PUT /api/profile` |
| Deals | `GET/POST /api/deals`, `GET/PUT/DELETE /api/deals/{id}`, `POST /api/deals/{id}/draft-followup`, `POST /api/sweep` |
| Approvals | `GET /api/approvals?status=pending\|blocked\|all`, `PUT /api/approvals/{ref}`, `POST /api/approvals/{ref}/decision` |
| Records | `GET /api/receipts`, `GET /api/receipts/{id}`, `GET /api/activity`, `GET /api/brief` |
| Chat | `POST /api/chat`, `GET /api/chat/sessions`, `GET/PUT/DELETE /api/chat/sessions/{id}` |
| API keys | `GET /api/settings/api-keys`, `PUT/DELETE /api/settings/api-keys/{provider}`, `POST /api/settings/api-keys/{provider}/test`, `PUT /api/settings/active-provider`, `GET /api/settings/usage` |
| Email | `GET/PUT/DELETE /api/settings/email`, `POST /api/settings/email/test` |
| Google | `GET/DELETE /api/integrations/google`, `POST /api/integrations/google/connect`, `GET /api/integrations/google/callback`, `POST /api/integrations/google/test`, `POST /api/deals/{id}/meeting` |
| Ops | `POST /api/settings/kill-switch`, `GET /api/v1/ops/status`, `GET /healthz`, `GET /readyz` |

Interactive docs: http://localhost:8000/docs

## Known limits

- Each API process holds one database connection; scale with more workers or a pool if needed.
- Emails are plain text. Incoming mail is not read (that needs a restricted Gmail scope and Google's security review).
- The worker container exposes health only; drafting and sending happen in the API request.
- The benchmark harness under `bench/` runs on the deterministic fake runner, not on a model.
