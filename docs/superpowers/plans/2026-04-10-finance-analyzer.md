# Finance Analyzer — High-Level Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local personal finance web application that ingests bank CSV exports, classifies transactions via rules + Claude AI, detects inter-account transfers, and displays spending analytics with drill-down from month → group → category → transactions.

**Architecture:** FastAPI backend (Python) with async SQLAlchemy on Neon Postgres; React + TypeScript frontend served by Vite dev server. Import is fire-and-forget (FastAPI BackgroundTasks); analytics always shows the last stable snapshot. No Docker, no auth.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy (async), asyncpg, Alembic, Anthropic SDK · React 18, TypeScript, Vite, TanStack Query, Recharts, Tailwind CSS · Neon Postgres (cloud)

---

## Milestone Overview

```
M1 ──► M2 ──► M3 ──► M4 ──► M5
```

Each milestone is independently deployable and adds a coherent slice. Later milestones build on earlier ones' database schema and services.

| Milestone | Goal | Detailed Plan |
|-----------|------|---------------|
| **M1** | Import a real bank export, see transactions in a list | [m1-ingest-skeleton.md](2026-04-10-m1-ingest-skeleton.md) |
| **M2** | Every transaction gets a category (rules + LLM) | [m2-categorization.md](2026-04-10-m2-categorization.md) |
| **M3** | Multiple accounts; inter-account transfers excluded | [m3-multi-account-transfers.md](2026-04-10-m3-multi-account-transfers.md) |
| **M4** | Analytics dashboard with full drilldown | [m4-analytics.md](2026-04-10-m4-analytics.md) |
| **M5** | Quality-of-life polish for regular monthly use | [m5-polish.md](2026-04-10-m5-polish.md) |

---

## Pre-Implementation Prerequisites

Before writing any code:

1. **Real Partners Bank CSV export** — provide `sample_data/partners_sample.csv` (gitignored). The `PartnersParser` in M1 must be built against a real file. Do not guess column names or encoding.
2. **Neon database** — create a free Neon project, copy the `postgresql+asyncpg://...` connection string.
3. **Anthropic API key** — needed for M2 only; can defer until M2 starts.
4. **Node.js 20+** and **Python 3.11+** must be installed locally.

---

## Full Project File Structure

```
FinAl/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                        # FastAPI app, CORS, router registration
│   │   ├── config.py                      # pydantic-settings, reads backend/.env
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── accounts.py                # Accounts CRUD router
│   │   │   ├── imports.py                 # Import upload + history router
│   │   │   ├── transactions.py            # Transaction list + detail router
│   │   │   ├── categories.py              # Category + group CRUD router (M2)
│   │   │   ├── rules.py                   # Rules CRUD router (M2)
│   │   │   ├── categorization.py          # Manual re-run endpoint (M2)
│   │   │   ├── analytics.py               # Analytics query endpoints (M4)
│   │   │   └── settings.py                # App settings + LLM cost (M5)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── import_service.py          # Orchestrates full import cycle
│   │   │   ├── parsers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py                # TransactionRow dataclass
│   │   │   │   ├── partners.py            # PartnersParser (M1)
│   │   │   │   └── generic_csv.py         # GenericCsvParser (M3)
│   │   │   ├── rules_engine.py            # Pure function: apply_rules() (M2)
│   │   │   ├── anthropic_client.py        # Anthropic SDK wrapper (M2)
│   │   │   ├── categorization_service.py  # Orchestrates rules + LLM (M2)
│   │   │   ├── transfer_matcher.py        # Cross-account pair detection (M3)
│   │   │   └── analytics_service.py       # Aggregation queries (M4)
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── models.py                  # All SQLAlchemy ORM models
│   │       ├── session.py                 # Engine + AsyncSession + get_db()
│   │       └── migrations/                # Alembic env + version files
│   │           ├── env.py
│   │           ├── script.py.mako
│   │           └── versions/
│   ├── tests/
│   │   ├── conftest.py                    # pytest fixtures, test DB setup
│   │   ├── test_partners_parser.py        # (M1)
│   │   ├── test_import_service.py         # (M1)
│   │   ├── test_accounts_api.py           # (M1)
│   │   ├── test_rules_engine.py           # (M2)
│   │   ├── test_categorization_service.py # (M2)
│   │   ├── test_transfer_matcher.py       # (M3)
│   │   └── test_analytics_service.py      # (M4)
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                        # Router + nav layout
│   │   ├── api/
│   │   │   ├── client.ts                  # axios instance, base URL
│   │   │   ├── accounts.ts                # account API calls
│   │   │   ├── imports.ts                 # import API calls
│   │   │   ├── transactions.ts            # transaction API calls
│   │   │   ├── categories.ts              # (M2)
│   │   │   ├── rules.ts                   # (M2)
│   │   │   ├── categorization.ts          # (M2)
│   │   │   └── analytics.ts               # (M4)
│   │   ├── components/
│   │   │   ├── NavBar.tsx                 # Top nav + processing status indicator
│   │   │   ├── ProcessingStatus.tsx       # Status dot in nav bar
│   │   │   └── NewDataBanner.tsx          # "New data available" banner (M4)
│   │   └── pages/
│   │       ├── Analytics/
│   │       │   ├── index.tsx              # Main analytics page
│   │       │   ├── MonthSummary.tsx        # Level 1: month totals + group breakdown
│   │       │   ├── GroupDetail.tsx         # Level 2: group → categories (M4)
│   │       │   ├── CategoryDetail.tsx      # Level 3: category → transactions (M4)
│   │       │   └── TransactionDetail.tsx   # Level 4: single transaction (M4)
│   │       ├── Imports/
│   │       │   ├── index.tsx              # Import management page
│   │       │   ├── UploadForm.tsx          # CSV upload widget
│   │       │   └── BatchHistory.tsx        # Import history table
│   │       ├── Rules/
│   │       │   ├── index.tsx              # Rules list page (M2)
│   │       │   └── RuleForm.tsx            # Create / edit rule (M2)
│   │       └── Settings/
│   │           └── index.tsx              # Accounts, categories, LLM cost
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── docs/
│   ├── superpowers/
│   │   ├── specs/
│   │   │   └── 2026-04-10-application-workflow-design.md
│   │   └── plans/
│   │       ├── 2026-04-10-finance-analyzer.md       ← this file
│   │       ├── 2026-04-10-m1-ingest-skeleton.md
│   │       ├── 2026-04-10-m2-categorization.md
│   │       ├── 2026-04-10-m3-multi-account-transfers.md
│   │       ├── 2026-04-10-m4-analytics.md
│   │       └── 2026-04-10-m5-polish.md
│   └── ... (existing design docs)
├── sample_data/          # gitignored — real bank exports
└── CLAUDE.md
```

---

## Milestone Dependency Map

```
M1: project scaffold
    ├── backend: FastAPI, models (accounts, transactions, import_batches), PartnersParser,
    │           ImportService (sync parse + insert, background categorization stub),
    │           Accounts CRUD API, Imports API, Transactions list API
    └── frontend: Vite+React+Tailwind, Nav, Analytics skeleton, Imports page,
                  processing status indicator

M2: categorization (depends on M1)
    ├── backend: DB tables (categories, rules, llm_classifications), seed taxonomy,
    │           RulesEngine, AnthropicClient, CategorizationService,
    │           Categories/Rules/Categorization APIs
    └── frontend: Categories UI (in Settings), Rules page, Needs Review filter

M3: multi-account + transfers (depends on M2)
    ├── backend: GenericCsvParser, TransferMatcher
    └── frontend: column mapper wizard, Accounts management (in Settings)

M4: analytics (depends on M3)
    ├── backend: AnalyticsService (monthly_summary, trends, anomalies), analytics APIs
    └── frontend: full drilldown (all 4 levels), Trends sub-view, New Data banner

M5: polish (depends on M4)
    ├── backend: CSV export endpoint, LLM cost query
    └── frontend: bulk categorization, import retry, LLM cost dashboard, import detail panel
```

---

## How to Run (after M1)

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
alembic upgrade head
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Browser: `http://localhost:5173`

---

## Cross-Milestone Conventions

- **Thin routers** — FastAPI routes validate input and call services. No business logic in routers.
- **Pure service functions** — `RulesEngine`, all parsers: no DB access, no side effects, unit-testable with fixtures.
- **TDD** — write the failing test first, then the implementation.
- **Frequent commits** — one logical change per commit.
- **Secrets in `.env`** — never hardcode connection strings or API keys.
- **No Docker in v1** — plain venv + npm.
- **`is_transfer = false` everywhere in analytics** — applied at the service layer, not in the router.
