# ADR-0006: Bank Ingestion Strategy

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

Finance Analyzer needs to import transaction data from multiple bank accounts. Each Czech bank exports in a slightly different CSV schema. The user's primary bank is Partners Bank; other accounts may be added later.

Two extremes exist: build a hard-coded parser for every bank, or build a generic CSV importer that requires manual column mapping. A hybrid approach handles both.

## Decision

**Strategy:** Per-bank parsers for known banks + generic CSV mapper for everything else.

**Priority for v1:**
1. `PartnersParser` — built against a real Partners Bank export (sample to be provided before implementation). Hard-coded column names, date format, and encoding. Zero user configuration needed.
2. `GenericCsvParser` — used when no matching bank parser exists. On first upload from an unknown account, the user is shown a column-mapping screen to identify which CSV column maps to `date`, `amount`, `counterparty`, `description`, `reference`. The mapping is stored in the `import_batches.column_mapping` JSONB field and reused for all future uploads from that account.

**Account detection:** The user selects the target account when initiating an upload. If the account's `bank` field matches a known parser key (e.g., `"partners"`), the dedicated parser is used. Otherwise, the generic mapper is used.

**Deduplication:** Each imported row is assigned a `hash_key` = `sha256(account_id || booking_date || amount || counterparty || description)`. Rows with an existing `hash_key` are silently skipped, allowing safe re-upload of overlapping export periods.

**Deferred:** ABO/GPC (Czech binary statement format) and XML (Fio API, camt.053) parsers are not in v1. They can be added as new parser modules with no changes to the import pipeline or UI.

## Consequences

- Partners Bank works immediately after providing the export sample; no configuration needed for the primary account.
- New banks can be supported without changing the pipeline — add a parser module, register it in the parser registry.
- The generic CSV mapper has a one-time setup cost per bank but then works automatically.
- Deduplication means users can safely re-export a date range that overlaps a previous import without creating duplicate transactions.
- The parser is isolated: `parse(file: bytes, account: Account) -> list[TransactionRow]`. It has no database access; unit-testable with fixture files.

## Alternatives Considered

- **Generic mapper only** — Handles all banks uniformly. Downside: the user must do manual column mapping even for their primary bank on first use. Eliminated for Partners Bank by having a dedicated parser.
- **Hard-coded parsers for all banks** — Maximally transparent but requires maintaining a parser for every Czech bank. Most users only have 2–3 accounts; the generic mapper covers the long tail without ongoing maintenance.
- **Direct API integration (Fio API, Open Banking)** — Would avoid file exports entirely. Out of scope for v1: requires OAuth flows, credential management, and bank-specific API contracts. Excellent v2 candidate.
