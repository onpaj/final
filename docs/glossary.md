# Glossary

Terms used throughout Finance Analyzer documentation and code.

---

**Account**
A single bank account owned by the user. Examples: "Partners – Checking", "Raiffeisen – Savings". Each account has a `bank` field that determines which parser is used on import.

**Amount**
The monetary value of a transaction. Stored as a signed decimal (`NUMERIC(14,2)`) in the transaction's own currency. Negative = debit (money leaving the account); positive = credit (money arriving).

**Anomaly**
A spend spike detected by the analytics engine: a category group where the current month's total is more than 2 standard deviations above its trailing 6-month mean. Displayed as warning chips on the Dashboard.

**Booking date**
The date on which a transaction settled and was recorded on the account. Distinct from `value_date`, which is the interest/value date (used in some accounting contexts). Finance Analyzer uses `booking_date` for all analytics.

**Categorization source**
How a transaction was assigned its category. One of:
- `rule` — matched by a deterministic rule in the rules engine
- `llm` — assigned by the Claude AI model
- `manual` — assigned by the user in the UI
- `NULL` — not yet categorized (in the "Needs Review" queue)

**Category**
A leaf-level label applied to a transaction. Each category belongs to one Group. Examples: "Groceries", "Utilities", "Salary". Rules and LLM classification both produce a category assignment.

**Column mapping**
A JSON record stored per account that maps generic CSV column names to Finance Analyzer fields (`date`, `amount`, `counterparty`, `description`, `reference`). Created by the user on first upload from an unknown bank; reused automatically on subsequent uploads.

**Composite rule**
A rule whose `match_type = 'composite'` that combines multiple sub-conditions with AND logic. Example: "counterparty contains SBERBANK AND amount between 14,000–16,000 CZK → Rent".

**Confidence**
A numeric score (0.00–1.00) indicating how certain the LLM was about a category assignment. Scores below 0.70 after both model tiers (Haiku + Sonnet) result in the transaction being left uncategorized for manual review.

**Deduplication / hash_key**
Each transaction has a `hash_key` computed as `SHA-256(account_id || booking_date || amount || counterparty || description)`. On import, rows whose `hash_key` already exists in the database are silently skipped. This allows safe re-upload of overlapping export periods.

**Group**
The top-level category in the two-level taxonomy. Examples: "Living", "Transport", "Leisure", "Income". A group contains multiple categories and is used for roll-up totals in analytics.

**Import batch**
A single file upload event. One record in `import_batches` per upload, tracking: filename, parser used, total rows, imported rows, duplicate rows, and timestamp.

**Internal Transfer**
A system-managed category (`is_system = true`) assigned to transactions that are detected as movement between the user's own accounts. Transactions in this category are excluded from income, expense, and savings-rate totals.

**is_income**
A boolean flag on `categories`. Categories with `is_income = true` contribute to the income total in analytics (e.g., Salary, Freelance). All other categories contribute to the expense total.

**Needs Review queue**
The set of transactions with `category_id IS NULL` after the categorization pipeline has run. Surfaced in the Transactions UI with a dedicated filter. Requires manual user action to resolve.

**Parser**
A module that converts a raw bank export file (bytes) into a list of `TransactionRow` dataclasses. Parsers have no side effects and no database access. Current parsers: `PartnersParser`, `GenericCsvParser`.

**Rule**
A deterministic pattern-to-category mapping. Evaluated before the LLM. Rules have a `priority` (higher = evaluated first), a `match_type`, and a `match_value` JSON spec. On a match, `hit_count` is incremented and `last_hit_at` is updated.

**Savings rate**
`(income_total - abs(expense_total)) / income_total`, expressed as a percentage. Calculated per month. Excludes all `is_transfer = true` transactions from both sides.

**Transfer pair**
Two transactions — a debit in one account and a credit in another — that represent the same movement of money between the user's own accounts. Detected automatically by `TransferMatcher` and linked via a shared `transfer_pair_id` UUID. Both transactions have `is_transfer = true`.

**Value date**
The interest / valuation date of a transaction as reported by the bank. May differ from `booking_date` by one or more days. Stored but not used in analytics (which always use `booking_date`).
