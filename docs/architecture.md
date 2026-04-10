# Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────────┐
│  Browser (React + Vite, localhost:5173)                  │
│  Pages: Dashboard | Transactions | Trends | Rules |      │
│         Import | Settings                                 │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP (TanStack Query)
┌─────────────────────▼───────────────────────────────────┐
│  FastAPI backend (localhost:8000)                         │
│                                                           │
│  Routers (thin HTTP layer):                               │
│    /api/imports        /api/transactions                  │
│    /api/rules          /api/categories                    │
│    /api/analytics      /api/accounts                      │
│    /api/settings                                          │
│                                                           │
│  Services (business logic):                               │
│    ImportService       CategorizationService              │
│    RulesEngine         TransferMatcher                    │
│    AnalyticsService    AnthropicClient                    │
│                                                           │
│  DB layer:                                                │
│    SQLAlchemy (async)  Alembic migrations                 │
└───────────┬─────────────────────────┬────────────────────┘
            │ asyncpg                  │ HTTPS
┌───────────▼──────────┐  ┌───────────▼──────────────────┐
│  Neon Postgres        │  │  Anthropic API                │
│  (cloud)              │  │  claude-haiku-4-5             │
│                       │  │  claude-sonnet-4-6            │
└───────────────────────┘  └───────────────────────────────┘
```

## Services

### ImportService
Coordinates a full import cycle: select parser → parse → deduplicate → persist raw transactions → trigger categorization + transfer matching. Returns an `ImportResult` summary.

### Parsers (under `services/parsers/`)
Pure functions: `parse(file_bytes: bytes, account: Account) -> list[TransactionRow]`.
- `PartnersParser` — hard-coded against Partners Bank CSV schema.
- `GenericCsvParser` — reads a stored `column_mapping`; shows mapping UI on first use.
No parser has database access; all are unit-testable with fixture files.

### RulesEngine
Pure function: `apply_rules(tx: TransactionRow, rules: list[Rule]) -> Match | None`.
Evaluates rules in priority order (highest first); returns the first match. No side effects; no database access. Testable in complete isolation.

### CategorizationService
Orchestrates the categorization pipeline:
1. Load active rules from DB.
2. For each uncategorized transaction, run `RulesEngine`.
3. For misses, call `AnthropicClient`.
4. Persist results, update `categorization_source` and `confidence`.

### AnthropicClient
Thin wrapper around the Anthropic Python SDK. Handles:
- Prompt construction (counterparty, description, amount, date, category list → JSON schema response).
- Model routing: Haiku → Sonnet escalation on low confidence.
- Usage logging to `llm_classifications`.
- Retry on transient API errors (exponential backoff, max 3 retries).

### TransferMatcher
Scans a list of newly imported transaction IDs and searches for cross-account pair candidates. Runs after each import batch. Marks matched pairs with a shared `transfer_pair_id` and `is_transfer=true`.

### AnalyticsService
Executes parameterized SQL aggregation queries against the Neon database:
- `monthly_summary(year, month)` → totals per group/category.
- `trends(from_date, to_date, group_by)` → monthly series.
- `anomalies(year, month)` → z-score calculation vs. trailing 6 months.

## Request Flow: Import a Bank Export

```
1. User uploads CSV in Import page
   → POST /api/imports { account_id, file }

2. Router calls ImportService.import_file(account_id, file_bytes)

3. ImportService:
   a. Select parser (Partners or generic)
   b. Parse → list[TransactionRow]
   c. Compute hash_key per row
   d. INSERT rows (skip duplicates by hash_key)
   e. Create ImportBatch record
   f. Call CategorizationService.run_batch(batch_id)
   g. Call TransferMatcher.match_batch(batch_id)

4. CategorizationService:
   a. Load active rules
   b. For each transaction: RulesEngine.apply → assign if match
   c. Remaining: AnthropicClient.classify_batch(transactions)
   d. UPDATE transactions SET category_id, categorization_source, confidence

5. TransferMatcher:
   a. For each debit in batch, query for matching credit in other accounts (±2 days, same amount)
   b. UPDATE matched pairs: is_transfer=true, transfer_pair_id=shared_uuid

6. Response: { batch_id, imported: N, duplicates: M, categorized: K, transfers: T }
```

## Request Flow: Monthly Analytics

```
1. User opens Dashboard for April 2026
   → GET /api/analytics/monthly?year=2026&month=4

2. AnalyticsService.monthly_summary(2026, 4):
   - SELECT SUM(amount) WHERE is_transfer=false AND booking_date BETWEEN ...
     GROUP BY category_id
   - Enrich with group/category names
   - Compute totals: income_total, expense_total, savings_rate

3. Response: { groups: [...], income: X, expenses: Y, savings_rate: Z% }
```

## Design Principles

- **Thin routers:** FastAPI routes only validate input and delegate to services. No business logic in routers.
- **Pure service functions where possible:** `RulesEngine` and parsers have no side effects; they are easy to test and reason about.
- **One responsibility per service:** `TransferMatcher` only matches transfers; it does not categorize.
- **LLM as a last resort:** `AnthropicClient` is only called from `CategorizationService`; no other code path talks to Anthropic.
