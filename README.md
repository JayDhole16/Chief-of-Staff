# Chief-of-Staff

## Provisional local containers

The Docker Compose stack runs the existing FastAPI API and Vite development server:

In PowerShell, make a local env file and set a local database password before starting:

```powershell
Copy-Item .env.example .env
# Edit .env and set POSTGRES_PASSWORD to a private local value.
docker compose up --build
```

Open the frontend at `http://localhost:3000`; the API is also available at
`http://localhost:8080`. PostgreSQL stays private on the Compose network. The Vite
`/api` proxy targets the API container, and
`http://localhost:3000/api/healthz` checks that route end to end. The worker health
endpoint is at `http://localhost:8081/health`. Stop the stack with `docker compose down`.
After startup, `python scripts/smoke_app.py` checks the web page, API proxy, API
readiness, and worker health. It reports that the worker is only a placeholder until
the durable executor is implemented.

The provisional operations and brief endpoints are available at
`http://localhost:8080/api/v1/ops/status` and `http://localhost:8080/api/v1/brief`;
the dashboard's **Ops** tab displays them. The operations response explicitly marks
fake or unavailable integrations and returns `degraded` until every required local
component is ready. The brief omits events without a resolvable receipt, approval, or
escalation link and reports the omission count. These endpoints describe local demo
state only and are not live G4 or production evidence.

This is a development stack, not the planned production architecture. PostgreSQL
stores provisional inbound tasks only; other application state remains in memory.
The worker only exposes placeholder health and does not execute jobs.

See [jay.md](jay.md) for the provisional decisions, remaining gaps, and replacement
steps for the canonical contracts.