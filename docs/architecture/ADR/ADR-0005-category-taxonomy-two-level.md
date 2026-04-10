# ADR-0005: Category Taxonomy — Two-Level Hierarchy

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

Transactions must be assigned to categories. The taxonomy structure determines how categories are organized, how reports roll up, and how much cognitive overhead the user faces when classifying.

Three structural options were considered: flat list, two-level hierarchy, and free-form multi-tags.

## Decision

**Structure:** Two-level hierarchy — **Group → Category**.

Examples:
- `Living` → `Groceries`, `Utilities`, `Rent`, `Household`
- `Transport` → `Fuel`, `Public Transit`, `Parking`, `Car Insurance`
- `Leisure` → `Dining`, `Entertainment`, `Travel`, `Sport`
- `Health` → `Pharmacy`, `Doctor`, `Fitness`
- `Income` → `Salary`, `Freelance`, `Other Income`
- `Transfers` → `Internal Transfer` (system-managed; see ADR-0007)

Both Groups and Categories are stored in the database (`category_groups` and `categories` tables) and are fully user-editable in the UI. A starter taxonomy seeded from Czech household spending norms is provided at first run.

Each category has an `is_income` boolean flag. This drives the income vs. expense split in analytics without requiring a separate concept.

## Consequences

- Reports can show data at either level: "I spent 8,000 CZK on Living" (group) or "3,200 CZK on Groceries" (category). Both are useful; the hierarchy enables both without duplication.
- The starter taxonomy reduces bootstrapping effort; users can rename, add, or delete to fit their needs.
- Two levels is sufficient for personal finance. A third level (sub-sub-category) would add complexity without proportional benefit.
- The `is_income` flag on categories cleanly distinguishes income transactions (salary, invoices) from expenses without needing a separate "income" vs "expense" dimension.
- Rules and LLM output reference categories (leaf level), not groups. Groups are only used for display and aggregation.

## Alternatives Considered

- **Flat list** — Simplest. Monthly summary by category works fine. Lost: roll-up totals by theme (e.g., "all Living costs"). Would require the user to mentally group categories.
- **Free-form multi-tags** — Most flexible. Transactions can be tagged `groceries` + `family` + `weekly`. Downside: double-counting in aggregations (a transaction tagged twice appears in two totals). Aggregation logic becomes complex and confusing. Rejected.
- **Three levels** — Too granular for personal finance. Adds friction when creating rules and categories without meaningful analytical benefit.
