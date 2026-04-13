# Design: Run Rules / Run LLM on Selected Items in Review Tab

**Date:** 2026-04-12  
**Status:** Approved

## Summary

Add two action buttons to the "Ke kontrole" (Review) page that operate on selected transactions:
- **Spustit pravidla** — apply the rules engine only; categorize matches, leave unmatched as-is (no LLM)
- **Klasifikovat LLM** — skip rules, call the LLM directly; categorize if confidence ≥ threshold, else leave in review

## Backend

### API change — `POST /api/categorize/batch`

`RecategorizeRequest` gains a `mode` field:

```python
class RecategorizeRequest(BaseModel):
    transaction_ids: list[uuid.UUID] | None = None
    mode: Literal["rules", "llm", "full"] = "full"
```

Default is `"full"`, so the Settings page calling the endpoint without `mode` is unaffected.

### Service changes — `CategorizationService`

Two new internal methods:

**`_categorize_one_rules_only(tx, rules)`**
- Calls `RulesEngine.apply(row, rules)`
- If match: sets `category_id`, `categorization_source = "rule"`, `confidence = 1.0`, increments `rule.hit_count`
- If no match: no-op (transaction remains uncategorized)
- Does not call LLM, does not write `LlmClassification`

**`_categorize_one_llm_only(tx, categories)`**
- Skips rules entirely
- Calls `AnthropicClient.classify()` directly
- Writes `LlmClassification` log (same as current LLM path in `_categorize_one`)
- If confidence ≥ threshold: sets `category_id`, `categorization_source = "llm"`, `confidence`
- On `AnthropicClassificationError`: logs error record, transaction stays uncategorized

`run_batch` dispatches based on `mode`:
- `"rules"` → `_categorize_one_rules_only`
- `"llm"` → `_categorize_one_llm_only`
- `"full"` → existing `_categorize_one` (rules → LLM fallback)

The `category_id is not None` guard in `run_batch` stays — review items always have null category.

## Frontend

### `frontend/src/api/categorization.ts`

Add a new exported function alongside the existing `runBatchClassification`:

```typescript
export async function recategorizeBatch(
  transaction_ids: string[],
  mode: "rules" | "llm" | "full",
): Promise<BatchClassificationResult> {
  const { data } = await client.post<BatchClassificationResult>(
    "/api/categorize/batch",
    { transaction_ids, mode },
  );
  return data;
}
```

### `frontend/src/pages/Review/index.tsx`

Add two mutations:

```typescript
const runRulesMutation = useMutation({
  mutationFn: () => recategorizeBatch(Array.from(selected), "rules"),
  onSuccess: invalidateAndClear,
});

const runLlmMutation = useMutation({
  mutationFn: () => recategorizeBatch(Array.from(selected), "llm"),
  onSuccess: invalidateAndClear,
});
```

Add a toolbar that renders only when `selected.size > 0`, placed between the page heading and the DnD area:

```
[ Spustit pravidla ]  [ Klasifikovat LLM ]   (X vybráno)
```

- Both buttons disabled while either mutation is in-flight
- Active button shows spinner
- On error: brief inline error text below the toolbar (clears on next action)

### i18n keys

Add to `review` section in both `cs/translation.json` and `en/translation.json`:

| Key | CS | EN |
|-----|----|----|
| `review.runRules` | `Spustit pravidla` | `Run rules` |
| `review.runLlm` | `Klasifikovat LLM` | `Classify with LLM` |
| `review.selectedCount` | `{{count}} vybráno` | `{{count}} selected` |
| `review.runError` | `Akce selhala` | `Action failed` |

## Error handling

Both mutations surface errors inline (text below toolbar). No toast/modal needed — these are non-destructive operations; if they fail the user can simply retry.

## Out of scope

- Progress indicator for large batches (LLM calls can be slow; deferred)
- "Full" mode button in the Review UI (Settings page already covers classify-all)
