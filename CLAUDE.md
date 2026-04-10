# Finance Analyzer — Claude Context

This file onboards Claude Code sessions into the Finance Analyzer project.

## What This Project Is

A personal local web application for analyzing household finances across multiple bank accounts. It ingests CSV bank exports, categorizes transactions using rules + Claude AI (Anthropic), detects cross-account transfers, and provides monthly spend/income/savings analytics.

See [`docs/overview.md`](docs/overview.md) for a full description including non-goals.

## Current Status

**Design phase.** All documentation and ADRs are written. No code exists yet.
The next step is implementing Milestone 1 (see [`docs/roadmap.md`](docs/roadmap.md)).

Before starting M1 implementation: **a real Partners Bank CSV export is needed.** The `PartnersParser` must be built against a real file, not guessed. Ask the user to provide `sample_data/partners_sample.csv` (gitignored).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI, `uvicorn` |
| ORM | SQLAlchemy (async), Alembic migrations |
| DB driver | `asyncpg` |
| Database | Neon (serverless Postgres, cloud) |
| LLM | Anthropic Python SDK; models: `claude-haiku-4-5` (default), `claude-sonnet-4-6` (escalation) |
| Frontend | React, TypeScript, Vite, TanStack Query, Recharts, Tailwind CSS |
| Runtime | Local Python venv + `npm run dev` (no Docker) |

## Project Structure (planned)

```
FinAl/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/           # FastAPI routers (thin; delegate to services)
│   │   ├── services/
│   │   │   ├── import_service.py
│   │   │   ├── parsers/   # partners.py, generic_csv.py
│   │   │   ├── categorization_service.py
│   │   │   ├── rules_engine.py      # pure function, no DB
│   │   │   ├── anthropic_client.py
│   │   │   ├── transfer_matcher.py
│   │   │   └── analytics_service.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── session.py
│   │   │   └── migrations/          # Alembic
│   │   └── config.py                # pydantic-settings, reads .env
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/   # Dashboard, Transactions, Trends, Rules, Import, Settings
│   │   ├── components/
│   │   └── api/
│   └── package.json
├── docs/                  # All design documentation
├── sample_data/           # gitignored — real bank exports for local dev
└── CLAUDE.md              # this file
```

## Key Design Decisions

All significant decisions are recorded as ADRs. See the index at [`docs/architecture/ADR/README.md`](docs/architecture/ADR/README.md).

Short summary of the most impactful ones:
- **No Docker** — plain Python venv + npm. Keep it simple.
- **Neon Postgres** — cloud-hosted; connect via `DATABASE_URL` in `.env`.
- **Anthropic, not OpenAI** — use `anthropic` SDK, `claude-haiku-4-5` / `claude-sonnet-4-6`.
- **Rules-first categorization** — rules are evaluated before the LLM; LLM is only called for unmatched transactions.
- **No auth in v1** — localhost only; no login system.
- **is_transfer flag** — all analytics queries filter `WHERE is_transfer = false`.

## Environment Variables

The backend reads from `backend/.env` (gitignored). See `backend/.env.example` (to be created in M1).

```
DATABASE_URL=postgresql+asyncpg://...  # Neon connection string
ANTHROPIC_API_KEY=sk-ant-...
```

## How to Run (once M1 is implemented)

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Browser: `http://localhost:5173`

## Coding Conventions

- **Thin routers** — FastAPI routes validate input and call services. No business logic in routers.
- **Pure service functions** — `RulesEngine` and parsers have no side effects and no DB access. Test them in isolation.
- **ADR-first for new decisions** — if you make a significant architectural choice that isn't covered by an existing ADR, write a new one. Small implementation decisions don't need ADRs.
- **No code comments for obvious things** — only comment where logic isn't self-evident.
- **Secrets in `.env`** — never hardcode API keys or connection strings.

## Open Questions

See [`docs/overview.md#open-questions`](docs/overview.md#open-questions) for the full list. Key ones:
1. Partners Bank CSV export format — user needs to provide a real sample.
2. Multi-currency handling (CZK primary; EUR/USD deferred to v1.5).
3. ABO/GPC parser — deferred until an export is available.
