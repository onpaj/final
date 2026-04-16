# Run Classification Button — Design Spec

**Date:** 2026-04-16  
**Status:** Approved

## Summary

Replace the two separate "Run rules" and "Classify with LLM" buttons on the Review page with a single "Run classification" button. Three checkboxes control which steps execute. The button is always visible; when no rows are selected it runs on all uncategorized transactions.

---

## Backend

### API change: `POST /api/categorize/batch`

Replace the `mode: Literal["rules", "llm", "full"]` field with:

```python
steps: list[Literal["transfers", "rules", "llm"]] = ["transfers", "rules", "llm"]
```

Since the only consumer of this endpoint is the Review page frontend, `mode` is removed without a backward-compat shim.

### `CategorizationService.run_batch`

Signature changes from `mode: str` to `steps: list[str]`. Steps execute in fixed order:

1. **`"transfers"`** — calls `TransferMatcher.match_batch(ids)`. The matcher searches the full DB for counterpart matches; `ids` are the seed set. Transactions flagged `is_transfer=True` are then excluded from subsequent categorization steps.
2. **`"rules"`** — applies rules engine to remaining transactions.
3. **`"llm"`** — applies LLM classification to remaining transactions.

### Empty `transaction_ids`

Unchanged: when `transaction_ids` is `None` or `[]`, the endpoint queries all transactions with `category_id IS NULL`.

---

## Frontend

### Toolbar (always visible)

The action bar is moved out of the `selected.size > 0` guard and rendered unconditionally above the transaction table.

**Layout:**
```
[☑ Transfers] [☑ Rules] [☐ LLM]    [Run classification]    3 selected
```

- Three inline checkboxes (label + input) in a flex row
- "Run classification" button to the right
- Selection count shown only when `selected.size > 0`

### State

```ts
const [steps, setSteps] = useState({ transfers: true, rules: true, llm: false })
```

Default: transfers + rules checked, LLM unchecked.

### Mutation

Single `runClassificationMutation`:
- Computes `activeSteps = Object.entries(steps).filter(([,v]) => v).map(([k]) => k)`
- Calls `recategorizeBatch(Array.from(selected), activeSteps)`
- When `selected.size === 0`, passes `[]` — backend fetches all uncategorized
- Button disabled when `activeSteps.length === 0` or mutation is pending
- On success: clear selection, invalidate `["transactions", "needs_review"]` query

### API layer

`recategorizeBatch` signature changes:

```ts
// before
recategorizeBatch(transaction_ids: string[], mode: "rules" | "llm" | "full")

// after
recategorizeBatch(transaction_ids: string[], steps: string[])
```

### i18n keys

Remove: `review.runRules`, `review.runLlm`

Add (EN + CS):

| Key | EN | CS |
|-----|----|----|
| `review.runClassification` | Run classification | Spustit klasifikaci |
| `review.stepTransfers` | Transfers | Přesuny |
| `review.stepRules` | Rules | Pravidla |
| `review.stepLlm` | LLM | LLM |

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/api/categorization.py` | Replace `mode` with `steps` in `RecategorizeRequest` |
| `backend/app/services/categorization_service.py` | Update `run_batch` to accept `steps: list[str]`, add transfer detection step |
| `frontend/src/api/categorization.ts` | Update `recategorizeBatch` signature |
| `frontend/src/pages/Review/index.tsx` | Merge mutations, add checkboxes, move toolbar out of selection guard |
| `frontend/public/locales/en/translation.json` | Update i18n keys |
| `frontend/public/locales/cs/translation.json` | Update i18n keys |
