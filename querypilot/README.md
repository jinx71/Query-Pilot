# QueryPilot — a natural-language data analyst agent

Ask a database questions in plain English and get back an answer **plus the
exact, read-only SQL that produced it.** QueryPilot is a conversational agent
that inspects a live PostgreSQL schema, writes SQL using Anthropic tool calling,
runs it safely, and explains the result — keeping a full, auditable trail of
every query it ran.

It ships with a sample **pharmaceutical manufacturing** database (batches, QC
tests, deviations, equipment) so the demo questions feel real, but it points at
any PostgreSQL database.

> **The signature idea — the "auditable answer".** Every reply renders the SQL
> that was executed, the row count, and the wall-clock time in a monospace lab
> readout. You never have to take the model's word for it: the evidence is on
> screen. That bias toward verifiability comes straight from a GMP / regulated
> manufacturing background, where "show your work" isn't optional.

---

## What it can answer

The sample database supports questions like:

- *How many batches were rejected in 2024?*
- *Which equipment had the most critical deviations?*
- *What is the QC failure rate by product?*
- *Show the top 5 operators by number of batches run.*

Follow-up questions work too — the agent keeps conversation memory, so *"and how
many of those were in oncology?"* resolves against the previous turn.

---

## How it works

```
                         ┌──────────────────────────────────────────────┐
   "How many batches      │                  Agent loop                  │
    were rejected         │                                              │
    in 2024?"             │   1. send messages + run_sql tool to Claude  │
        │                 │   2. Claude returns a tool_use (a SELECT)    │
        ▼                 │   3. SQL guard ── validates ──> read-only DB  │
   React UI ──► FastAPI ──►   4. rows fed back to Claude as tool_result  │
        ▲                 │   5. repeat until Claude answers in prose     │
        │                 │                                              │
   answer + every         └──────────────────────────────────────────────┘
   SQL step + timing
```

The loop is **hand-rolled** against the Anthropic Messages API — no agent
framework. For a single-tool, security-critical task that was the right call
(see the talking points below). The model client is injected, so the whole loop
is unit-tested against a fake client with zero network calls.

### Three layers of SQL safety

A natural-language-to-SQL tool is only as good as its blast radius is small.
QueryPilot defends in depth so that **even a maliciously-crafted prompt cannot
mutate or exfiltrate data**:

| Layer | Where | What it stops |
| --- | --- | --- |
| **1. Statement guard** | `app/sql_guard.py` (application) | Strips comments, rejects anything that isn't a *single* `SELECT`/`WITH`, blocks write keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `GRANT`, `COPY`, `CALL`, …) and dangerous functions (`pg_read_file`, `pg_sleep`, `lo_export`, `dblink`). |
| **2. Read-only transaction** | `app/database.py` (session) | Runs every query with `default_transaction_read_only = on`, so PostgreSQL itself refuses any write the guard might somehow miss. |
| **3. Resource limits** | `app/database.py` + `app/tools.py` | A database-enforced `statement_timeout` kills slow queries; a hard row cap bounds payload and token cost; only the first N rows are ever sent back to the model. |

> **Why three layers and not one?** Layer 1 gives fast, friendly errors the
> model can read and self-correct from. Layer 2 is the real backstop — a defense
> that holds even if the guard has a bug, because it's enforced by Postgres, not
> by my code. Layer 3 keeps a "valid but expensive" query from becoming an
> availability or cost problem. In production you'd also connect with a database
> role that only has `SELECT` grants — a fourth, infrastructure-level layer.

### Schema-aware generation

On startup the agent introspects the database (`app/schema_inspector.py`) and
builds a compact text description of every table, its columns and foreign keys,
plus the distinct values of low-cardinality text columns (e.g. it learns that
`batches.status` is one of `released`, `rejected`, `quarantine`). That schema is
embedded in the system prompt, which is why the model writes correct joins and
filters on the *actual* enumerated values instead of guessing.

### Self-correction

When a generated query errors, the failure is returned to the model as a
`tool_result` rather than thrown. The model reads the database error, rewrites
the query, and tries again — all within the same turn, bounded by a step cap so
it can never loop forever. There's a dedicated test that injects a bad first
query and asserts the agent recovers.

### Conversation memory

Each session keeps a trimmed message history in a thread-safe in-memory store
(`app/memory.py`), enabling natural follow-ups. **Why in-memory?** It keeps the
demo dependency-free. The store is deliberately a single small class behind a
clear interface, so swapping it for Redis in production is a contained change —
the rest of the app doesn't know or care where history lives.

---

## Tech stack

**Backend** — Python 3.12, FastAPI, the Anthropic SDK (native tool calling),
SQLAlchemy Core + psycopg 3, sqlparse, pydantic-settings.

**Frontend** — React 18 + TypeScript, Vite, Tailwind CSS, Recharts (code-split
and lazy-loaded), lucide-react, axios.

**Infra** — Docker + docker-compose (Postgres 16, FastAPI, and an
nginx-served production build of the UI), with the sample database auto-seeded
on first boot.

---

## Project structure

```
querypilot/
├── docker-compose.yml         # db + backend + frontend, one command
├── backend/
│   ├── app/
│   │   ├── agent.py           # the tool-calling loop (the brain)
│   │   ├── sql_guard.py       # safety layer 1: statement validation
│   │   ├── database.py        # safety layers 2 & 3: read-only + limits
│   │   ├── schema_inspector.py# introspection → schema prompt + UI tree
│   │   ├── tools.py           # the run_sql tool definition + executor
│   │   ├── memory.py          # per-session conversation store
│   │   ├── routes.py          # /health /api/session /api/schema /api/chat
│   │   ├── models.py          # pydantic request/response models
│   │   ├── config.py          # env-driven settings
│   │   └── main.py            # app factory + CORS
│   ├── seed/                  # schema.sql + deterministic data generator
│   ├── tests/                 # 52 tests (pytest)
│   └── requirements.txt
└── frontend/
    └── src/
        ├── components/
        │   ├── ChatPanel.tsx      # conversation + input + examples
        │   ├── MessageBubble.tsx  # answer + per-step results
        │   ├── SqlBlock.tsx       # the auditable "lab readout"
        │   ├── ResultTable.tsx    # tabular results, status-aware cells
        │   ├── ChartView.tsx      # lazy-loaded bar chart
        │   └── SchemaSidebar.tsx  # live schema browser
        ├── hooks/useChat.ts       # session + message state
        ├── api/client.ts          # typed API client
        └── types/index.ts         # mirrors the backend models
```

---

## Getting started

### Option A — Docker (recommended)

Requires Docker. The database is created and seeded automatically.

```bash
cd querypilot
ANTHROPIC_API_KEY=sk-ant-your-key docker compose up --build
```

Then open **http://localhost:8080**. (The API is on `:8000`.)

### Option B — run the pieces manually

**1. Database.** Point `DATABASE_URL` at any PostgreSQL instance, then load the
schema and seed:

```bash
cd backend
python seed/run.py            # applies schema.sql + seed_data.sql
```

**2. Backend.**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload # http://localhost:8000
```

**3. Frontend.**

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173 (proxies /api to :8000)
```

To regenerate the seed data deterministically: `python backend/seed/generate_seed.py`.

---

## Configuration

All settings are environment variables (see `backend/.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — | Required for `/api/chat`. The app still starts and serves `/health` + `/api/schema` without it. |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | SQL generation + answering. Swap to Haiku for cheaper runs, Opus for the hardest questions. |
| `DATABASE_URL` | local querypilot DB | SQLAlchemy URL (`postgresql+psycopg://…`). |
| `MAX_RESULT_ROWS` | `200` | Hard ceiling on rows returned to the model and UI. |
| `STATEMENT_TIMEOUT_MS` | `5000` | Database-enforced per-query timeout. |
| `MAX_AGENT_STEPS` | `6` | Max tool round-trips before the agent must answer. |
| `MAX_HISTORY_TURNS` | `12` | Conversation turns kept in memory. |
| `CLIENT_URL` | `http://localhost:5173` | CORS origin (exact match, no trailing slash). |

---

## API reference

All responses use a consistent `{ success, data, message }` envelope.

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| `GET` | `/health` | — | `{ status: "ok" }` |
| `POST` | `/api/session` | — | `{ session_id }` |
| `POST` | `/api/session/{id}/reset` | — | `{ session_id }` (clears history) |
| `GET` | `/api/schema` | — | `{ tables: [{ name, columns: [...] }] }` |
| `POST` | `/api/chat` | `{ message, session_id? }` | `{ session_id, answer, steps: [...] }` |

Each item in `steps` is one executed query: `{ purpose, sql, ok, error,
columns, rows, row_count, truncated, elapsed_ms }` — exactly what the UI renders
in the lab readout.

---

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest                        # 52 tests
```

The suite (**52 tests, all passing** against a live PostgreSQL) covers:

- **SQL guard (38 tests):** legitimate reads pass; every write verb is rejected;
  injection attempts (stacked statements, comment tricks, CTE-wrapped writes,
  dangerous functions) are blocked; the row-limit injector behaves.
- **Database layer:** results round-trip correctly; the read-only transaction
  actually rejects writes; truncation and `statement_timeout` fire; non-JSON
  types (Decimal, date, UUID) are serialized.
- **Schema inspector:** tables, foreign-key references and sample values are
  discovered.
- **Agent loop:** a single tool call resolves; a deliberately bad first query is
  recovered from via self-correction; history is preserved across turns; the
  step cap forces a final answer. These run against an injected fake client, so
  they're fast and need no API key.

> **Why the app/server split.** `main.py` exposes an app factory, so tests drive
> the real ASGI app in-process with no port binding, and the agent's model
> client is injectable — the loop is fully testable without ever hitting the
> network.

---

## Talking points (for interviews)

- **Why hand-rolled tool calling instead of LangGraph?** I have a separate
  multi-agent project where a graph framework genuinely earns its keep —
  multiple agents, branching, a reflection loop. This is the opposite case: one
  tool, one security-critical step, a need for total control over how SQL is
  validated and how errors are fed back. A framework would have *hidden* the most
  important code behind an abstraction. Choosing the framework-free path here,
  and the framework path there, is the actual engineering judgment.
- **Defense in depth on the SQL boundary.** The headline risk in NL-to-SQL is a
  prompt that coaxes the model into a destructive query. I don't rely on the
  model behaving — I make misbehavior impossible: an application guard, a Postgres
  read-only transaction, resource limits, and (in prod) a `SELECT`-only DB role.
- **Schema-aware prompting beats prompt-tweaking.** Feeding the model the real
  schema — including the distinct values of enum-like columns — is what makes the
  generated SQL correct. The model filters on `status = 'rejected'` because it was
  told those are the values, not because I hand-tuned the wording.
- **Self-correction as a first-class behavior.** Returning DB errors to the model
  as tool results (instead of failing the request) turns a dead end into a retry,
  bounded by a hard step cap. There's a test that proves the recovery path.
- **Built to scale past the demo.** Conversation memory sits behind a small
  interface (→ Redis), the model is env-swappable per cost/quality, and the whole
  thing is containerized. The in-memory choices are deliberate demo simplicity,
  not architectural dead ends.
- **The pharma framing is the differentiator.** The auditable-answer UI, the
  read-only guarantees, and the QC/deviation sample data all come from 8+ years in
  GMP manufacturing. It's an AI agent built the way a regulated industry would
  want one built: verifiable, bounded, and honest about what it did.

---

## The sample database

A deterministic generator (`backend/seed/generate_seed.py`, fixed RNG seed)
produces a small but join-rich operations database: **12 products, 15 pieces of
equipment, 20 operators, 320 manufacturing batches, ~923 QC tests, and 90
deviations**, all wired together with foreign keys so the agent has interesting
aggregations and joins to write. Swap in your own database via `DATABASE_URL`
and the schema browser and agent adapt automatically.
