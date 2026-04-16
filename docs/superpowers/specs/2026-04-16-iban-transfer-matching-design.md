# IBAN-Validated Transfer Matching — Design Spec

**Date:** 2026-04-16
**Status:** Approved

## Problem

The current `TransferMatcher` identifies internal transfers between accounts using only amount (±0.01) and booking date (±2 days). This is imprecise:

- False positives: two unrelated transactions with the same amount in the same date window get wrongly paired.
- No use of account identity: the `counterparty_account` field on transactions is ignored entirely.

The app supports multiple bank formats. Partners Bank exports `counterparty_account` preferring IBAN, falling back to `account/bankcode`. Other banks may export only the local Czech format. When two internal accounts are imported from different banks, the formats may differ — both should still be recognized as the same account.

## Goal

When a user sets an IBAN on an account, transfers between that account and other IBAN-configured accounts should be detected precisely: by validating that each side's `counterparty_account` explicitly references the other account, with cross-format normalization.

Accounts without IBAN set are excluded from transfer detection entirely (no silent fallback to amount+date-only matching).

## Approach

**Strict IBAN-only matching.** Both accounts in a candidate pair must have IBAN set. Counterparty account fields must cross-reference. Amount and date remain as pre-filters.

## Components

### 1. `backend/app/services/iban_utils.py` (new)

Pure functions — no DB access, fully testable in isolation.

```
normalize_iban(s: str) -> str
```
Strips spaces and uppercases. `"CZ65 0800 0000 ..."` → `"CZ6508000000..."`.

```
iban_to_local_cz(iban: str) -> str | None
```
Derives Czech local account format from a Czech IBAN.

- Czech IBAN structure (24 chars): `CZ` + 2 check + 4 bank code + 6 prefix + 10 account number
- Strips leading zeros from prefix and account parts
- Returns `"{account}/{bank}"` if prefix is 0, else `"{prefix}-{account}/{bank}"`
- Returns `None` for non-Czech IBANs (country code ≠ `CZ`) or malformed input

```
normalize_local_cz(s: str) -> str | None
```
Normalizes a Czech local account string (`account/bank` or `prefix-account/bank`):
- Strips leading zeros from prefix and account parts
- Returns canonical form or `None` if unparseable

```
account_identifiers(iban: str) -> set[str]
```
Returns all canonical forms for a given IBAN. For Czech IBANs this is two entries: the normalized IBAN and the derived local format. Used as a lookup set during matching.

### 2. `backend/app/services/transfer_matcher.py` (modified)

**Initialization:**
- Load all `Account` rows that have a non-null `iban` at the start of `match_batch`
- Build `_account_identifiers: dict[uuid.UUID, set[str]]` mapping `account_id → account_identifiers(account.iban)`

**`_find_match` changes:**
1. Pre-filter candidates from DB: same amount+date window as today, `account_id != debit.account_id`, `is_transfer=False`
2. For each candidate credit:
   a. If `debit.account_id` not in `_account_identifiers` → skip
   b. If `credit.account_id` not in `_account_identifiers` → skip
   c. Normalize `debit.counterparty_account` → check against `_account_identifiers[credit.account_id]`
   d. Normalize `credit.counterparty_account` → check against `_account_identifiers[debit.account_id]`
   e. Both (c) and (d) must match → accept
3. Return first accepted candidate (same as today)

**Normalization for lookup:**
When checking a `counterparty_account` value against an account's identifier set:
- If the value looks like an IBAN (starts with 2 letters + 2 digits): `normalize_iban(value)`
- Otherwise: `normalize_local_cz(value)`
- If normalization returns `None` → no match

## Data Flow Example

Account A (IBAN: `CZ6508000000192000145399`) sends 5 000 CZK to Account B (IBAN: `CZ6503000000000001234567`).

| Transaction | `counterparty_account` as exported | Normalized |
|---|---|---|
| Debit from A | `CZ65 0300 0000 0000 0123 4567` | `CZ6503000000000001234567` |
| Credit to B | `19-2000145399/0800` | `19-2000145399/0800` |

Matcher checks:
- Debit's counterparty (`CZ6503000000000001234567`) ∈ B's identifiers (`{"CZ6503000000000001234567", "1234567/0300"}`) ✓
- Credit's counterparty (`19-2000145399/0800`) ∈ A's identifiers (`{"CZ6508000000192000145399", "19-2000145399/0800"}`) ✓
- → Transfer pair confirmed.

## Error Handling

- Account with no IBAN: silently excluded from transfer detection (no error, no fallback).
- Malformed `counterparty_account` (unparseable): treated as no match for that candidate; other candidates still evaluated.
- Non-Czech IBAN on account: `iban_to_local_cz` returns `None`; identifier set contains only the normalized IBAN. Matching still works if both sides export IBAN format.

## Testing

### `test_iban_utils.py` (new)
- `normalize_iban`: strips spaces, lowercases, handles already-normalized input
- `iban_to_local_cz`: with prefix, without prefix, non-CZ IBAN returns None, malformed returns None
- `normalize_local_cz`: strips leading zeros, prefix-account/bank, account/bank, unparseable returns None
- `account_identifiers`: returns both IBAN and local form for Czech IBAN

### `test_transfer_matcher.py` (extended)
- Match succeeds: IBAN ↔ IBAN (both sides export IBAN)
- Match succeeds: IBAN ↔ local (cross-format)
- Match succeeds: local ↔ local
- No match: one account has no IBAN set
- No match: counterparty_account doesn't reference the other account (wrong number)
- No match: counterparty_account is malformed/None
- Existing amount+date tests remain valid (update mocks to include IBAN and counterparty_account)

## Out of Scope

- Non-Czech IBAN local format derivation (only Czech IBANs get local form in identifier set)
- Storing a separate `account_number` field on `Account` — IBAN is the single source of truth
- Re-running transfer matching on historical transactions when IBAN is added to an account
- UI changes for IBAN input on accounts (field already exists in `AccountCreate`/`AccountUpdate`)
