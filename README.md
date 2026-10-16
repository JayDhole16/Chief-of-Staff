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

This is a development stack, not the planned production architecture. PostgreSQL
stores provisional inbound tasks only; other application state remains in memory.
The worker only exposes placeholder health and does not execute jobs.

See [jay.md](jay.md) for the provisional decisions, remaining gaps, and replacement
steps for the canonical contracts.