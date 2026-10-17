# Chief-of-Staff

An AI chief-of-staff for founders: an inbound message is ingested, resolved against
your deal pipeline, run through deterministic guards and a pure policy engine, and
turned into a hash-bound proposal you approve with one tap; only then does the
executor act and issue a receipt.

**Honest status:** the demo runs on **fake adapters (deterministic)** — Gmail,
Calendar and the database are in-memory stand-ins. No live external write happens
anywhere in this repository, the live golden path reports its prerequisites as
blocked, and the benchmark result (84/84, 53/53 adversarial) is measured on the
deterministic fake runner, not on a model.

## Quickstart — the ten-line gate

```bash
git clone https://github.com/JayDhole16/Chief-of-Staff.git   # 1  clone
cd Chief-of-Staff                                            # 2
make setup                                                   # 3  pip install -e ".[dev]"
make demo-check                                              # 4  expect: VERDICT: PASS — 10/10 steps
make test                                                    # 5  expect: 200 passed, 4 skipped
cd frontend && npm ci && npm test -- --run && cd ..          # 6  expect: 38 passed (8 files)
cp .env.example .env                                         # 7  then set POSTGRES_PASSWORD in .env
make up                                                      # 8  web :3000, API :8080, worker :8081
python scripts/smoke_app.py                                  # 9  web, API proxy, readiness, worker
make down                                                    # 10 stop the stack
```

If those ten lines behave as commented, the fake-path claim is proven: proposal
render -> hash -> 409 on tamper -> approval -> execution -> receipt -> sweep -> kill
switch, with no network dependency beyond `npm ci`.

## What each gate proves

| Command | Passing output | Proves |
|---|---|---|
| `make demo-check` | `VERDICT: PASS — 10/10 steps verified` | The golden path end to end on fakes |
| `make test` | `200 passed, 4 skipped` | The backend suite (4 skips are the Postgres tests, which need `DATABASE_URL`) |
| `npm test -- --run` | `38 passed (8 files)` | The PWA contract, mocks and approval flows |
| `npm run build` | bundle emitted, 0 TypeScript errors | The frontend contract matches the API |

## Endpoints (development stack)

The frontend is at `http://localhost:3000`, the API at `http://localhost:8080`, and
the placeholder worker health at `http://localhost:8081/health`; PostgreSQL stays
private on the Compose network. `http://localhost:3000/api/healthz` checks the Vite
`/api` proxy end to end. The operations and brief endpoints are
`http://localhost:8080/api/v1/ops/status` and `http://localhost:8080/api/v1/brief`;
the ops response explicitly marks fake or unavailable integrations and returns
`degraded` (`data_mode: provisional`) until every local component is ready. After
`make up`, `python scripts/smoke_app.py` checks the web page, API proxy, API
readiness and worker health together.

## Known limits

- This is a development stack, not the production architecture: application state
  is mostly in memory, the worker only exposes placeholder health, and only
  provisional inbound tasks are persisted (Postgres when `DATABASE_URL` is set).
- Live prerequisites (database, Google, model, Evolus, vault) are uncredentialed;
  `python scripts/live_golden_path_check.py` reports them as blocked on purpose.
- Full-repo `ruff check backend tests` has pre-existing violations; CI lints a
  curated file list with `--select I,F` instead.

See [jay.md](jay.md) for provisional decisions and remaining gaps, [docs/](docs/)
for ADRs and demo material, and [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md)
for the submission state.
