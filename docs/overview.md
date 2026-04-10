# Finance Analyzer — Overview

## What It Is

Finance Analyzer is a personal local web application for analyzing household finances across multiple bank accounts. It ingests bank export files (CSV and similar), categorizes every transaction using a combination of user-defined rules and AI classification, and presents monthly spending analytics broken down by category.

It was built because Czech banking apps provide inadequate transaction categorization — they cannot use custom categories, cannot merge data from multiple accounts, and cannot identify patterns across months.

## Who It Is For

A single person or household managing finances across multiple Czech bank accounts. The user wants to understand where money goes each month, track trends over time, and see an accurate income/expense/savings picture — with custom categories that reflect their actual life.

## What It Does

- **Imports** bank export files (Partners Bank CSV natively; other banks via a configurable column mapper).
- **Categorizes** transactions automatically: deterministic rules first, then Claude AI (Anthropic) for unrecognized payees.
- **Detects transfers** between own accounts and excludes them from spend/income totals.
- **Provides analytics:** monthly spending by category, trends over time, income vs. expenses, savings rate, and simple anomaly detection for unusual spend spikes.
- **Lets you manage** the category taxonomy, categorization rules, and accounts through a browser UI.

## What It Does NOT Do (Non-Goals)

- **No budgeting or spending limits** — Finance Analyzer is analytical (what happened?), not prescriptive (stay under X).
- **No forecasting or predictions** — no projected future spending.
- **No bill reminders or notifications** — not a reminder app.
- **No bank API integration** — you import CSV files manually; no OAuth/bank credentials.
- **No multi-user support** — single household only; no login system in v1.
- **No mobile app** — browser UI on desktop only.
- **No automatic scheduling** — imports are initiated manually.
- **No investment / portfolio tracking** — only cash transactions (debits and credits from bank accounts).

## Key Concepts

See [docs/glossary.md](glossary.md) for full definitions. In brief:

| Term | Meaning |
|------|---------|
| Account | One bank account (e.g., "Partners – Checking") |
| Transaction | A single debit or credit on an account |
| Category | Leaf-level label, e.g., "Groceries" |
| Group | Parent of categories, e.g., "Living" |
| Rule | Deterministic pattern → category mapping |
| Transfer pair | Two matched transactions representing movement between own accounts |
| Import batch | One upload of one bank export file |
| Categorization source | How a transaction was categorized: `rule`, `llm`, or `manual` |

## Open Questions

The following are not yet resolved and will be addressed before or during implementation:

1. **Multi-currency** — Partners Bank is CZK-primary. If EUR or USD transactions appear, FX rate handling (source: ČNB?) is needed for accurate CZK-equivalent totals. Deferred to v1.5.
2. **ABO/GPC parser** — A binary Czech bank statement format used by some banks. Deferred until a real export is available.
3. **LLM monthly cost cap** — An optional guardrail: refuse LLM calls once a monthly token budget is exceeded. Simple to add; not included in v1.
4. **Partners Bank export format** — A real Partners Bank CSV export must be provided before the `PartnersParser` can be implemented. The parser is designed to be built against a real file, not guessed.
