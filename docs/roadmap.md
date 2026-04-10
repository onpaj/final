# Roadmap

Finance Analyzer is developed in five milestones. Each milestone is independently deployable (the app works end-to-end after each one) and adds a coherent slice of functionality.

---

## M1 — Ingest Skeleton

**Goal:** Import a real bank export, see transactions in a list.

**Scope:**
- Project scaffold: `backend/` (FastAPI, SQLAlchemy, Alembic) + `frontend/` (Vite, React, Tailwind)
- Neon connection, Alembic migrations for: `accounts`, `transactions`, `import_batches`
- `PartnersParser` — built from a real Partners Bank CSV export (user provides sample)
- `ImportService` with dedup by `hash_key`
- `POST /api/imports` endpoint
- Accounts CRUD (`GET /api/accounts`, `POST`, `PATCH`, `DELETE`)
- Transactions list UI: paginated table, filter by account and date range

**Acceptance criteria:**
- Upload a real Partners Bank export → correct row count imported
- Re-upload the same file → zero new rows (dedup works)
- Transactions list shows all imported rows with date, amount, counterparty

---

## M2 — Categorization

**Goal:** Every transaction gets a category, automatically or manually.

**Scope:**
- DB tables: `category_groups`, `categories`, `rules`, `llm_classifications`
- Seed starter Czech household taxonomy (Groups: Living, Transport, Leisure, Health, Income, Savings, Transfers)
- `RulesEngine` (pure function, unit-tested)
- `AnthropicClient` wrapper (Haiku → Sonnet escalation, structured output, usage logging)
- `CategorizationService` orchestrating rules + LLM
- `POST /api/categorize/batch` — manual re-run endpoint
- Categories UI: CRUD for groups and categories
- Rules UI: CRUD for rules, priority ordering, "test on history" button (shows how many past transactions a rule would match without applying)
- Transactions list: inline re-categorize dropdown; "Needs Review" filter; create-rule-from-transaction button
- LLM cost summary in Settings (total tokens used this month)

**Acceptance criteria:**
- Create a rule `counterparty_contains: "ALBERT"` → all ALBERT transactions classified as Groceries
- Upload new transactions with no matching rule → LLM assigns categories with confidence shown
- Low-confidence transactions (< 0.7 after escalation) appear in "Needs Review"
- Manual re-categorization creates an entry with `categorization_source = 'manual'`

---

## M3 — Multi-Account and Transfer Detection

**Goal:** Handle multiple accounts; inter-account transfers are correctly excluded.

**Scope:**
- `GenericCsvParser` with column mapper UI (map columns on first upload, reuse stored mapping)
- Accounts management page: add/edit/delete accounts, set bank type
- `TransferMatcher` with cross-account pair detection (±2 days, ±0.01 CZK tolerance)
- Transactions list: "Internal Transfer" tag on matched pairs; manual un-match action
- Import page redesign: account selector, column mapper wizard for generic CSV

**Acceptance criteria:**
- Import a non-Partners CSV through the generic mapper → transactions imported and classified
- Import from two accounts where a known transfer exists → both rows marked `is_transfer=true`, linked via `transfer_pair_id`
- Analytics totals exclude the transfer amount (verify manually against expected totals)

---

## M4 — Analytics

**Goal:** Understand where money goes each month and over time.

**Scope:**
- `AnalyticsService` with three query functions: `monthly_summary`, `trends`, `anomalies`
- `GET /api/analytics/monthly`, `/trends`, `/anomalies` endpoints
- Dashboard page: income, expenses, savings rate cards; monthly spend by group (pie/donut); spend by category (bar); anomaly chips
- Trends page: line chart per category over a selectable date range (Recharts)
- Savings rate card with month-over-month delta

**Acceptance criteria:**
- Dashboard totals for a known month match hand-calculated spreadsheet values (within rounding)
- Trends page shows per-category monthly series for a 12-month range
- Anomaly chips appear when a category has a genuine spike; no false positives for a flat month
- All analytics exclude `is_transfer = true` transactions

---

## M5 — Polish

**Goal:** Quality-of-life improvements for regular monthly use.

**Scope:**
- Bulk categorization in Transactions page (select multiple → assign category)
- Keyboard shortcuts in the transactions table
- "Test rule on history" shows match preview before saving
- LLM cost dashboard in Settings: per-model token usage, cost estimate, monthly breakdown
- Import history page: list of all `import_batches` with stats and ability to delete a batch (and its transactions)
- Export transactions to CSV
- `README.md` quickstart for future setup

**Acceptance criteria:**
- Bulk categorize 20 transactions in 3 clicks
- "Test rule" shows accurate preview without modifying any data
- LLM cost page shows token counts per model per month

---

## Deferred (Not Planned)

| Feature | Reason |
|---------|---------|
| Multi-currency / FX rates | Needs ČNB API integration; deferred until EUR/USD transactions appear |
| ABO/GPC parser | Deferred until a real export is available |
| Direct bank API (Fio, Open Banking) | OAuth complexity; manual CSV export is sufficient for now |
| LLM monthly budget cap | Easy to add when LLM costs become a concern |
| Auth / multi-user | Explicitly out of scope for v1 (see ADR-0009) |
| Mobile UI | Not needed for a personal desktop tool |
| Budgeting / spending limits | Out of scope (analytics only, not prescriptive) |
