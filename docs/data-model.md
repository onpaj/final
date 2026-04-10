# Data Model

All tables live in Neon Postgres. Managed via SQLAlchemy (async) + Alembic migrations.

---

## `accounts`

One row per bank account owned by the user.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `name` | TEXT NOT NULL | Display name, e.g., "Partners – Checking" |
| `bank` | TEXT NOT NULL | Parser key, e.g., `"partners"`, `"generic"` |
| `iban` | TEXT | Optional; stored locally only, never sent to LLM |
| `currency` | TEXT NOT NULL | Default `"CZK"` |
| `is_active` | BOOL NOT NULL | Soft-delete / hide from UI |
| `created_at` | TIMESTAMPTZ | |

---

## `transactions`

One row per bank transaction.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `account_id` | UUID FK → `accounts.id` | |
| `booking_date` | DATE NOT NULL | When the transaction settled |
| `value_date` | DATE | Interest/value date (may differ from booking_date) |
| `amount` | NUMERIC(14,2) NOT NULL | Negative = debit, positive = credit |
| `currency` | TEXT NOT NULL | |
| `counterparty_name` | TEXT | Name of the other party |
| `counterparty_account` | TEXT | Their IBAN/account — stored but never sent to LLM |
| `description` | TEXT | Transaction note / reference |
| `raw_reference` | TEXT | Original bank reference string (for audit) |
| `import_batch_id` | UUID FK → `import_batches.id` | |
| `category_id` | UUID FK → `categories.id` | NULL = uncategorized / needs review |
| `categorization_source` | TEXT | `'rule'` \| `'llm'` \| `'manual'` \| NULL |
| `confidence` | NUMERIC(3,2) | 0.00–1.00; NULL for rules (always 1.0) and manual |
| `is_transfer` | BOOL NOT NULL DEFAULT false | True if matched as cross-account transfer |
| `transfer_pair_id` | UUID | Shared UUID linking the two sides of a transfer pair |
| `hash_key` | TEXT UNIQUE NOT NULL | SHA-256 of `account_id \|\| booking_date \|\| amount \|\| counterparty_name \|\| description`. Used for dedup. |
| `notes` | TEXT | Optional user note on the transaction |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Indexes:**
- `(account_id, booking_date)` — analytics range queries
- `hash_key` UNIQUE — deduplication on import
- `(category_id, booking_date)` — category drill-down
- `is_transfer` — filter in analytics queries

---

## `import_batches`

One row per file upload.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `account_id` | UUID FK → `accounts.id` | |
| `filename` | TEXT | Original filename |
| `parser_used` | TEXT | `"partners"` or `"generic"` |
| `column_mapping` | JSONB | Stored mapping for generic CSV; NULL for known parsers |
| `row_count` | INT | Total rows parsed |
| `imported_count` | INT | Rows actually inserted (after dedup) |
| `duplicate_count` | INT | Rows skipped as duplicates |
| `imported_at` | TIMESTAMPTZ | |

---

## `category_groups`

Top-level grouping of categories.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `name` | TEXT NOT NULL | e.g., `"Living"`, `"Transport"` |
| `sort_order` | INT NOT NULL DEFAULT 0 | Display order in UI |
| `color` | TEXT | Hex color for charts, e.g., `"#4CAF50"` |

---

## `categories`

Leaf-level labels assigned to transactions.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `group_id` | UUID FK → `category_groups.id` | |
| `name` | TEXT NOT NULL | e.g., `"Groceries"`, `"Utilities"` |
| `is_income` | BOOL NOT NULL DEFAULT false | True for salary, freelance income, etc. |
| `color` | TEXT | Override hex color; falls back to group color |
| `sort_order` | INT NOT NULL DEFAULT 0 | |
| `is_system` | BOOL NOT NULL DEFAULT false | System-managed categories (e.g., Internal Transfer) cannot be deleted |

---

## `rules`

Deterministic categorization rules. Evaluated in priority order (DESC) before LLM.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `name` | TEXT NOT NULL | Human-readable name, e.g., "ALBERT → Groceries" |
| `priority` | INT NOT NULL DEFAULT 100 | Higher = evaluated first |
| `match_type` | TEXT NOT NULL | `'counterparty_contains'` \| `'counterparty_regex'` \| `'description_contains'` \| `'amount_range'` \| `'composite'` |
| `match_value` | JSONB NOT NULL | Type-specific match spec (see below) |
| `category_id` | UUID FK → `categories.id` | Target category when rule matches |
| `enabled` | BOOL NOT NULL DEFAULT true | Disabled rules are skipped |
| `hit_count` | INT NOT NULL DEFAULT 0 | How many transactions this rule has matched |
| `last_hit_at` | TIMESTAMPTZ | |
| `created_at` | TIMESTAMPTZ | |

**`match_value` shapes by `match_type`:**
```jsonc
// counterparty_contains
{ "value": "ALBERT" }

// counterparty_regex
{ "pattern": "^ALBERT.*CZ$" }

// description_contains
{ "value": "nájem" }

// amount_range
{ "min": 14000, "max": 16000 }

// composite (AND of sub-rules)
{ "conditions": [ { "type": "counterparty_contains", "value": "SBERBANK" }, { "type": "amount_range", "min": 14000, "max": 16000 } ] }
```

---

## `llm_classifications`

Audit log for every LLM classification call.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `transaction_id` | UUID FK → `transactions.id` | |
| `model` | TEXT | e.g., `"claude-haiku-4-5"` |
| `suggested_category_id` | UUID FK → `categories.id` | Category the model suggested |
| `accepted` | BOOL | Whether the suggestion was applied |
| `confidence` | NUMERIC(3,2) | Model's reported confidence |
| `reasoning` | TEXT | Model's explanation |
| `prompt_tokens` | INT | |
| `completion_tokens` | INT | |
| `created_at` | TIMESTAMPTZ | |

This table supports cost monitoring and quality review. It is never deleted (append-only).

---

## Entity Relationship Summary

```
accounts ──< import_batches
accounts ──< transactions
transactions >── categories >── category_groups
transactions >── rules (via categorization_source, not FK)
transactions ──< llm_classifications
transactions ──< transactions (self-ref via transfer_pair_id)
```
