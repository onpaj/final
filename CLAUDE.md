# Finance Analyzer — Claude Context

This file onboards Claude Code sessions into the Finance Analyzer project.

## What This Project Is

A personal web application for analyzing household finances across multiple bank accounts. It ingests CSV bank exports, categorizes transactions using rules + Claude AI (Anthropic), detects cross-account transfers, and provides monthly spend/income/savings analytics.

The app is deployed to Azure (Docker + Azure Container Web App + Easy Auth via Entra ID) and used with real bank data.

See [`docs/overview.md`](docs/overview.md) for a full description including non-goals.

## Current Status

**Production-ready and actively used.** All milestones M1–M4 are complete:

- **M1** — CSV import pipeline (Partners Bank + generic CSV mapper), deduplication, background processing
- **M2** — Categorization: rules engine (rules-first) + LLM fallback (Haiku → Sonnet escalation), category/group CRUD, rule management
- **M3** — Transfer detection across accounts (`is_transfer` flag, paired transactions)
- **M4** — Analytics dashboard: monthly breakdown, trends over time, anomaly detection (2σ), LLM cost tracking

**M5 (UI polish)** is in progress: drag-and-drop category assignment, context menu on transactions, review page improvements.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, `uvicorn` |
| ORM | SQLAlchemy (async), Alembic migrations |
| DB driver | `asyncpg` |
| Database | Neon (serverless Postgres, cloud) |
| LLM | Anthropic Python SDK; `claude-haiku-4-5` (default), `claude-sonnet-4-6` (escalation) |
| Frontend | React 19, TypeScript, Vite, TanStack Query v5, Recharts, Tailwind CSS |
| i18n | i18next (Czech + English) |
| DnD | DnD Kit (drag-and-drop category assignment) |
| HTTP | Axios + React Router v7 |
| Deployment | Docker, GitHub Actions, Azure Container Web App, Azure Blob Storage |
| Auth | Azure Entra ID Easy Auth (infrastructure-level, no app code) |

## Project Structure

```
FinAl/
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI app + router includes
│   │   ├── config.py                      # pydantic-settings, reads .env
│   │   ├── api/                           # Thin FastAPI routers
│   │   │   ├── accounts.py
│   │   │   ├── imports.py
│   │   │   ├── transactions.py
│   │   │   ├── categories.py
│   │   │   ├── rules.py
│   │   │   ├── categorization.py
│   │   │   ├── analytics.py
│   │   │   └── settings.py                # LLM cost tracking
│   │   ├── services/
│   │   │   ├── import_service.py          # CSV parsing, dedup, background processing
│   │   │   ├── categorization_service.py  # Rules-first + LLM fallback
│   │   │   ├── rules_engine.py            # Pure function, no DB
│   │   │   ├── transfer_matcher.py        # Cross-account transfer detection
│   │   │   ├── analytics_service.py       # Monthly/trends/anomaly queries
│   │   │   ├── anthropic_client.py        # Tool-use classification, model escalation
│   │   │   ├── blob_storage.py            # Azure Blob + local fallback
│   │   │   └── parsers/
│   │   │       ├── base.py                # TransactionRow dataclass
│   │   │       ├── partners.py            # Partners Bank CSV
│   │   │       └── generic_csv.py         # Configurable column mapper
│   │   └── db/
│   │       ├── models.py                  # Account, ImportBatch, Transaction, Category, CategoryGroup, Rule, LlmClassification
│   │       ├── session.py                 # Async session factory
│   │       └── migrations/               # Alembic
│   ├── tests/                             # 13 test files (pytest + asyncpg)
│   ├── scripts/                           # One-off admin scripts
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx                        # Router setup
│   │   ├── i18n.ts                        # i18next config
│   │   ├── pages/
│   │   │   ├── Analytics/                 # Monthly breakdown, trends, anomalies, category drilldown
│   │   │   ├── Imports/                   # Upload + batch history
│   │   │   ├── Review/                    # Uncategorized transaction review
│   │   │   ├── Rules/                     # Rule CRUD with priority management
│   │   │   ├── Categories/                # Category + group management
│   │   │   └── Settings/                  # Account management
│   │   ├── components/
│   │   │   ├── NavBar.tsx
│   │   │   ├── ProcessingStatus.tsx       # Real-time batch polling
│   │   │   ├── SlideOverPanel.tsx
│   │   │   └── ContextMenu.tsx            # Right-click on transactions
│   │   └── api/                           # Axios clients per endpoint
│   └── package.json
├── docs/                                  # Design documentation + ADRs
├── sample_data/                           # gitignored — real bank exports
├── categories.csv, category_groups.csv    # Seed data
├── Dockerfile                             # Multi-stage build (frontend → backend)
├── .github/workflows/deploy.yml           # CI/CD: test → build → push → Azure deploy
└── CLAUDE.md                              # this file
```

## Key Design Decisions

All significant decisions are recorded as ADRs — see [`docs/architecture/ADR/README.md`](docs/architecture/ADR/README.md).

Short summary of the most impactful ones:
- **Categorization pipeline order: Transfer → Rules → LLM, first match wins** — `categorization_source` is set by the first strategy that matches; subsequent strategies must not overwrite it. The guard in `run_batch` skips any transaction with `categorization_source is not None`. Transfer detection always runs before rules and LLM; it must not be called again separately after the pipeline (doing so was a bug that caused double-processing).
- **Rules-first categorization** — rules are evaluated before the LLM; LLM is called only for unmatched transactions.
- **LLM model escalation** — Haiku classifies first; Sonnet re-classifies if confidence < 0.7.
- **is_transfer flag** — all analytics queries filter `WHERE is_transfer = false`.
- **is_ignored flag** — categories marked ignored are excluded from analytics (e.g. savings transfers).
- **Hash-key deduplication** — SHA-256 of account+date+amount+counterparty+description prevents duplicate imports.
- **Azure Easy Auth** — authentication is enforced at the infrastructure level; no auth code in the app.
- **Docker deployment** — multi-stage build serves frontend static files from FastAPI.
- **Neon Postgres** — cloud-hosted; connect via `DATABASE_URL` in `.env`.

## Environment Variables

The backend reads from `backend/.env` (gitignored). In production these are Azure App Service Application Settings.

```
DATABASE_URL=postgresql+asyncpg://...          # Neon connection string
ANTHROPIC_API_KEY=sk-ant-...
ENVIRONMENT=development                         # or production
AZURE_STORAGE_CONNECTION_STRING=...            # optional; falls back to local storage
AZURE_STORAGE_CONTAINER=uploads
```

## How to Run

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
alembic upgrade head
uvicorn app.main:app --reload --port 8300

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Browser: `http://localhost:5173` (dev) or `http://localhost:8300` (production Docker).

## Coding Conventions

- **Thin routers** — FastAPI routes validate input and call services. No business logic in routers.
- **Pure service functions** — `RulesEngine` and parsers have no side effects and no DB access. Test them in isolation.
- **ADR-first for new decisions** — if you make a significant architectural choice that isn't covered by an existing ADR, write a new one. Small implementation decisions don't need ADRs.
- **No code comments for obvious things** — only comment where logic isn't self-evident.
- **Secrets in `.env`** — never hardcode API keys or connection strings.

## Open Questions / Deferred

- **Multi-currency** — CZK primary; EUR/USD handling deferred to v1.5.
- **ABO/GPC parser** — deferred until an export is available.
- **Mobile responsiveness** — app is desktop-only for now.
