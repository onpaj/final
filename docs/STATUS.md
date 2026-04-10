# Finance Analyzer — Implementation Status

_Last updated: 2026-04-10_

---

## Current State

**M1 (Ingest Skeleton) — COMPLETE**

93 transactions imported, date range 2026-02-25 to 2026-03-31.
App is running locally (backend :8000, frontend :5173).

---

## What Is Built

### Backend

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI app + CORS | ✅ | `app/main.py` |
| Config (pydantic-settings) | ✅ | Reads `backend/.env` |
| SQLAlchemy async models | ✅ | Account, ImportBatch, Transaction |
| Alembic migrations | ✅ | Applied to Neon (`d0fbaa06862e`) |
| Accounts CRUD API | ✅ | GET/POST/PATCH/DELETE /api/accounts — soft-delete |
| Import API | ✅ | POST /api/imports (fire-and-forget, background task) |
| Batch history API | ✅ | GET /api/imports, GET /api/imports/{id} |
| Transactions API | ✅ | GET /api/transactions with filters (account, date, category, needs_review, is_transfer) |
| PartnersParser | ✅ | Parses Partners Bank CSV — header validation, BOM handling, robust error handling |
| ImportService | ✅ | Hash-key dedup (SHA-256), background batch processing |

### Frontend

| Component | Status | Notes |
|-----------|--------|-------|
| Vite + React + TypeScript | ✅ | |
| Tailwind CSS | ✅ | v3 |
| TanStack Query | ✅ | v5 |
| React Router | ✅ | v6 |
| NavBar + routing | ✅ | Analytics / Imports / Rules / Settings |
| Processing status indicator | ✅ | Polls latest batch, color-coded dot |
| Imports page | ✅ | Upload form + batch history table (auto-refresh) |
| Settings page | ✅ | Add / remove accounts |
| Analytics page | ⏳ | Placeholder only — M4 work |

### Infrastructure

| Item | Status | Notes |
|------|--------|-------|
| Neon Postgres | ✅ | Connected, schema applied |
| `.env` | ✅ | `backend/.env` (gitignored) |
| `.gitignore` | ✅ | data/, sample_data/, .env, .venv, node_modules |
| Git history | ✅ | 17 commits |

---

## What Is NOT Built Yet

### M2 — Categorization
- Category data model (categories table, FK on transactions.category_id)
- Rules engine (keyword/regex matching, pure function)
- LLM categorization via Anthropic (claude-haiku-4-5, escalate to claude-sonnet-4-6)
- Categorization service (rules-first, LLM fallback)
- Seed categories (Living, Transport, Leisure, Health, Income, Savings + subcategories)
- Categories API (CRUD)
- Rules API (CRUD)
- Frontend: category management in Settings
- Frontend: "Needs Review" chip to surface uncategorized transactions

### M3 — Multi-Account + Transfers
- Transfer detection (TransferMatcher — match cross-account pairs by amount + date window)
- `is_transfer` flag set on matched pairs
- `transfer_pair_id` linking the two sides
- Multi-account consolidation in analytics queries

### M4 — Analytics UI
- Monthly spending breakdown by Group → Category → Transaction
- Recharts bar/pie charts
- Month selector
- Account filter dimension
- "New data available" banner after background import
- Analytics service (DB queries: sum by group, by category, by month)
- Trends view (multi-month spending over time)

### M5 — Polish
- Bulk categorization (select many transactions, assign category)
- Import retry button for failed batches
- LLM cost dashboard (token usage per month)
- CSV export
- Import batch detail panel (expandable row showing transactions)
- README quickstart

---

## Known Gaps / Technical Debt

- **`category_id` has no FK constraint yet** — intentional, FK to be added in M2 migration alongside the categories table
- **GenericCsvParser not implemented** — bank type `generic` will fail on import; only `partners` works
- **No auth** — localhost only, by design (v1 scope)
- **`backend/.venv` uses Python 3.14** — hatchling editable install (`pip install -e .`) fails on 3.14; deps installed directly instead. Not a problem at runtime.
- **Alembic migration file committed** — `versions/d0fbaa06862e_m1_initial_schema.py` is in git; correct behavior

---

## Live DB State

| Table | Count |
|-------|-------|
| accounts | 2 |
| import_batches | 1 |
| transactions | 93 |

Date range of imported transactions: **2026-02-25 → 2026-03-31**

All 93 transactions have `category_id = NULL` (uncategorized — M2 not yet implemented).

---

## Next Steps (in order)

1. **M2: Categorization** — categories table + seed data, rules engine, LLM fallback, categorization API
2. **M4: Analytics** — monthly spending UI, charts, drilldown (can be done before M3 for single account)
3. **M3: Transfer detection** — cross-account transfer matching
4. **M5: Polish** — bulk categorize, export, retry, LLM cost panel
