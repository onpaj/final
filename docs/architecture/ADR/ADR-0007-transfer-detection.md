# ADR-0007: Transfer Detection — Auto-Match Cross-Account Pairs

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

When a user moves money between their own accounts (e.g., Partners Bank → savings account), both accounts record the transaction: a debit on one side and a credit on the other. If both accounts are imported into Finance Analyzer, this internal transfer would appear twice — once as an outflow and once as an inflow — distorting spend totals, income totals, and savings rate.

## Decision

**Strategy:** Automatic transfer detection with cross-account pair matching.

After each import batch is processed, `TransferMatcher` scans for pairs:
1. For every transaction with a negative amount in account A, search for a transaction in any other owned account B with:
   - Amount equal in magnitude (within a small rounding tolerance, e.g., ±0.01 CZK)
   - Booking date within a configurable window (default ±2 calendar days; cross-day settlement is common)
2. If a match is found, both transactions are linked via `transfer_pair_id` (a shared UUID) and both have `is_transfer` set to `true`.
3. All analytics queries filter `WHERE is_transfer = false` by default. Transfers are visible in the transaction list with a distinct "Internal Transfer" tag but do not count toward income, spend, or savings rate.

If no suitable category rule exists for the matched transactions, they are automatically assigned to the `Transfers → Internal Transfer` system category (created during database seeding).

**Edge case — unmatched transfers:** If only one account's export is available, a transfer appears as a regular debit (from the exported account). It will be LLM-classified as `Transfers → Internal Transfer` if the counterparty or description contains the user's own account reference. The user can also create a rule. Unmatched transfers are flagged in the UI for review.

## Consequences

- Savings rate and net cashflow calculations are correct even when importing from multiple accounts simultaneously.
- The matching algorithm is deterministic and runs entirely in SQL/Python without LLM involvement — fast and free.
- The ±2-day matching window may occasionally produce false positives if two coincidentally equal-amount transactions exist across accounts within the window. The probability is low for personal finance volumes; the user can manually un-match pairs in the UI if needed.
- The `transfer_pair_id` + `is_transfer` fields on `transactions` must be created as part of the schema (covered by the data model doc).

## Alternatives Considered

- **Manual tagging** — User confirms flagged pairs in the UI. More accurate (no false positives) but requires attention after every import. Chosen against for the routine case; manual un-matching is still available as an override.
- **Ignore / treat as regular transactions** — Simplest implementation. Results in double-counted amounts and a meaningless savings rate. Unacceptable for the stated goal.
- **Single-account mode** — Restrict to one account so the problem doesn't arise. Eliminates a stated requirement (multi-account support).
