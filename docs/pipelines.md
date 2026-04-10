# Pipelines

This document describes the three main processing pipelines in Finance Analyzer.

---

## 1. Import Pipeline

Triggered when a user uploads a bank export file.

```
User uploads file
      │
      ▼
ImportService.import_file(account_id, file_bytes, filename)
      │
      ├─ 1. Select parser
      │       Account.bank == "partners"  →  PartnersParser
      │       Account.bank == "generic"   →  GenericCsvParser
      │         (uses stored column_mapping, or prompts user to map on first use)
      │
      ├─ 2. Parse
      │       parser.parse(file_bytes) → list[TransactionRow]
      │       (TransactionRow is a pure dataclass; no DB access in parsers)
      │
      ├─ 3. Compute hash_key per row
      │       sha256(account_id || booking_date || amount || counterparty || description)
      │
      ├─ 4. Deduplicate
      │       SELECT hash_key FROM transactions WHERE hash_key IN (...)
      │       Skip rows whose hash_key already exists
      │
      ├─ 5. Insert rows
      │       Batch INSERT new rows with category_id=NULL, categorization_source=NULL
      │       Create ImportBatch record (row_count, imported_count, duplicate_count)
      │
      ├─ 6. Run Categorization Pipeline on new transaction IDs
      │
      └─ 7. Run Transfer Matcher on new transaction IDs
```

**Output:** `ImportResult { batch_id, imported, duplicates, categorized, transfers_detected }`

---

## 2. Categorization Pipeline

Triggered after import, and also available as a manual "re-run" action on existing transactions.

```
CategorizationService.run_batch(transaction_ids)
      │
      ├─ 1. Load active rules from DB (ordered by priority DESC)
      │
      ├─ 2. For each uncategorized transaction:
      │
      │       RulesEngine.apply(transaction, rules)
      │         ├─ Evaluate each rule in priority order
      │         │   match_type handlers:
      │         │     counterparty_contains → tx.counterparty_name.lower() in value.lower()
      │         │     counterparty_regex    → re.search(pattern, tx.counterparty_name)
      │         │     description_contains  → tx.description.lower() in value.lower()
      │         │     amount_range          → min <= abs(tx.amount) <= max
      │         │     composite             → AND of all sub-conditions
      │         └─ Return first match or None
      │
      │       If match found:
      │         UPDATE transaction SET category_id=..., categorization_source='rule',
      │                                confidence=1.0
      │         INCREMENT rules.hit_count, SET rules.last_hit_at
      │
      ├─ 3. Collect transactions still uncategorized after rules pass
      │
      ├─ 4. LLM classification (AnthropicClient):
      │
      │       Build prompt:
      │         - Counterparty name
      │         - Description
      │         - Amount + currency
      │         - Booking date
      │         - Full category list (group → category, one per line)
      │
      │       Call claude-haiku-4-5 with structured output schema:
      │         { "category": "<category name>", "confidence": 0.00-1.00,
      │           "reasoning": "<short explanation>" }
      │
      │       If confidence >= 0.7:
      │         Accept → UPDATE categorization_source='llm', confidence=...
      │         Log to llm_classifications
      │
      │       If confidence < 0.7 (first attempt):
      │         Escalate → retry with claude-sonnet-4-6
      │         If confidence >= 0.7: accept
      │         Else: leave transaction uncategorized (add to "Needs Review")
      │         Log both calls to llm_classifications
      │
      └─ 5. Return categorization summary
```

**Needs Review queue:** Any transaction with `category_id IS NULL` after the pipeline runs appears in a dedicated UI section. The user can manually assign a category and optionally create a rule from the assignment.

---

## 3. Transfer Matching Pipeline

Triggered after import, runs on newly imported transaction IDs.

```
TransferMatcher.match_batch(transaction_ids)
      │
      ├─ 1. For each debit transaction (amount < 0) in the batch:
      │
      │       Search for a matching credit in any OTHER owned account:
      │         - amount == abs(debit.amount) ± 0.01
      │         - booking_date BETWEEN debit.booking_date - 2 days
      │                             AND debit.booking_date + 2 days
      │         - is_transfer = false  (not already matched)
      │         - account_id != debit.account_id
      │
      ├─ 2. For each matched pair:
      │       shared_uuid = new UUID
      │       UPDATE debit:  is_transfer=true, transfer_pair_id=shared_uuid
      │       UPDATE credit: is_transfer=true, transfer_pair_id=shared_uuid
      │       Assign category "Internal Transfer" (system category) to both
      │
      └─ 3. Return count of pairs matched
```

**Edge cases:**
- If the matching credit is in an account that hasn't been imported yet, the debit remains as a regular transaction. It may be picked up on the next import that includes the other account.
- If the user's own account reference appears in the counterparty name or description, the LLM categorization pipeline may assign "Internal Transfer" as a category anyway, which is still correct.
- Users can manually un-match a falsely detected pair in the Transactions UI; this sets `is_transfer=false` on both rows and clears `transfer_pair_id`.

---

## Analytics Pipeline

Not a background pipeline — runs on-demand per analytics request.

All analytics queries filter `WHERE is_transfer = false` by default.

| Endpoint | Logic |
|----------|-------|
| `monthly_summary` | `SUM(amount) GROUP BY category_id` for a single calendar month. Joined with group/category names. Totals: `income` = sum of `is_income=true` categories; `expenses` = sum of `is_income=false`; `savings_rate` = `(income - abs(expenses)) / income`. |
| `trends` | Same aggregation as `monthly_summary` but iterated over each month in a date range. Returns a series per category suitable for a line chart. |
| `anomalies` | For the requested month, compute `mean` and `stddev` of spend per category group over the trailing 6 months. Flag any group where current month spend > `mean + 2 * stddev`. Returns flagged groups with `current`, `mean`, `stddev`. |
