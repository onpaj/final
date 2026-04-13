# Import History Classification Badges — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show colored text badges on each transaction row in the import history expanded view, indicating whether the transaction was classified by a rule, LLM, manually, or is unclassified/a transfer.

**Architecture:** The backend `BatchTransactionOut` schema is extended with `categorization_source` and `is_transfer`; the frontend `BatchTransactions` component adds a classification column rendering colored badges from those fields.

**Tech Stack:** Python/FastAPI (Pydantic), React/TypeScript, Tailwind CSS, i18next

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/api/imports.py` | Add `categorization_source` and `is_transfer` to `BatchTransactionOut`; populate in endpoint |
| `backend/tests/test_imports_api.py` | Add test for `batch_transactions` endpoint returning new fields |
| `frontend/src/pages/Imports/BatchHistory.tsx` | Add `CategorizationBadge` component and classification column to `BatchTransactions` |
| `frontend/public/locales/cs/translation.json` | Add `imports.colClassification` key |
| `frontend/public/locales/en/translation.json` | Add `imports.colClassification` key |

---

### Task 1: Extend backend `BatchTransactionOut` with classification fields

**Files:**
- Modify: `backend/app/api/imports.py:37-45` (schema) and `:141-151` (endpoint)
- Modify: `backend/tests/test_imports_api.py`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/test_imports_api.py`. Note the file uses `mock_db` fixtures with `MagicMock` — follow the same pattern. Add the import for `Transaction` from `app.db.models` and `date` from `datetime` at the top if not present.

```python
from datetime import date
from app.db.models import Account, ImportBatch, Transaction

def _make_transaction(batch_id: uuid.UUID, categorization_source: str | None = "rule", is_transfer: bool = False) -> Transaction:
    tx = MagicMock(spec=Transaction)
    tx.id = uuid.uuid4()
    tx.import_batch_id = batch_id
    tx.booking_date = date(2026, 3, 15)
    tx.amount = -500.0
    tx.currency = "CZK"
    tx.counterparty_name = "Lidl"
    tx.description = None
    tx.category_id = uuid.uuid4()
    tx.categorization_source = categorization_source
    tx.is_transfer = is_transfer
    return tx


@pytest.mark.anyio
async def test_batch_transactions_returns_classification_fields(client, mock_db):
    batch_id = uuid.uuid4()
    tx = _make_transaction(batch_id, categorization_source="rule", is_transfer=False)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tx]
    mock_db.execute = AsyncMock(return_value=mock_result)

    async with client as c:
        resp = await c.get(f"/api/imports/{batch_id}/transactions")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["categorization_source"] == "rule"
    assert data[0]["is_transfer"] is False


@pytest.mark.anyio
async def test_batch_transactions_llm_and_transfer(client, mock_db):
    batch_id = uuid.uuid4()
    tx = _make_transaction(batch_id, categorization_source="llm", is_transfer=True)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tx]
    mock_db.execute = AsyncMock(return_value=mock_result)

    async with client as c:
        resp = await c.get(f"/api/imports/{batch_id}/transactions")

    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["categorization_source"] == "llm"
    assert data[0]["is_transfer"] is True
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend
pytest tests/test_imports_api.py::test_batch_transactions_returns_classification_fields tests/test_imports_api.py::test_batch_transactions_llm_and_transfer -v
```

Expected: FAIL — `categorization_source` and `is_transfer` not in response.

- [ ] **Step 3: Update `BatchTransactionOut` and the endpoint**

In `backend/app/api/imports.py`, update the schema (lines 37–45) and the endpoint list comprehension (lines 141–151):

```python
class BatchTransactionOut(BaseModel):
    id: uuid.UUID
    booking_date: date
    amount: float
    currency: str
    counterparty_name: str | None
    description: str | None
    category_id: uuid.UUID | None
    categorization_source: str | None
    is_transfer: bool
    model_config = {"from_attributes": False}
```

And update the endpoint list comprehension:

```python
    return [
        BatchTransactionOut(
            id=tx.id,
            booking_date=tx.booking_date,
            amount=float(tx.amount),
            currency=tx.currency,
            counterparty_name=tx.counterparty_name,
            description=tx.description,
            category_id=tx.category_id,
            categorization_source=tx.categorization_source,
            is_transfer=tx.is_transfer,
        )
        for tx in txs
    ]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend
pytest tests/test_imports_api.py::test_batch_transactions_returns_classification_fields tests/test_imports_api.py::test_batch_transactions_llm_and_transfer -v
```

Expected: PASS

- [ ] **Step 5: Run all backend tests to check for regressions**

```bash
cd backend
pytest --tb=short -q
```

Expected: all tests pass (or only pre-existing failures).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/imports.py backend/tests/test_imports_api.py
git commit -m "feat: expose categorization_source and is_transfer in batch transactions endpoint"
```

---

### Task 2: Add classification badge column to import history frontend

**Files:**
- Modify: `frontend/src/pages/Imports/BatchHistory.tsx`
- Modify: `frontend/public/locales/cs/translation.json`
- Modify: `frontend/public/locales/en/translation.json`

- [ ] **Step 1: Add translation keys**

In `frontend/public/locales/cs/translation.json`, inside the `"imports"` object (after `"historyColDuplicates"`):

```json
"historyColDuplicates": "Duplikáty",
"colClassification": "Klasifikace"
```

In `frontend/public/locales/en/translation.json`, same location:

```json
"historyColDuplicates": "Duplicates",
"colClassification": "Classification"
```

- [ ] **Step 2: Add `CategorizationBadge` component and update `BatchTransactions` in `BatchHistory.tsx`**

Replace the `BatchTransactions` function (lines 14–48 of `frontend/src/pages/Imports/BatchHistory.tsx`) with:

```tsx
interface BatchTx {
  id: string;
  booking_date: string;
  amount: number;
  currency: string;
  counterparty_name: string | null;
  description: string | null;
  category_id: string | null;
  categorization_source: string | null;
  is_transfer: boolean;
}

function CategorizationBadge({ tx }: { tx: BatchTx }) {
  if (tx.is_transfer) {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
        transfer
      </span>
    );
  }
  if (tx.categorization_source === "rule") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
        rule
      </span>
    );
  }
  if (tx.categorization_source === "llm") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
        llm
      </span>
    );
  }
  if (tx.categorization_source === "manual") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
        manual
      </span>
    );
  }
  return <span className="text-gray-400 text-xs">—</span>;
}

function BatchTransactions({ batchId }: { batchId: string }) {
  const { t } = useTranslation();
  const { data: txs = [], isLoading } = useQuery<BatchTx[]>({
    queryKey: ["batch-transactions", batchId],
    queryFn: async () => (await client.get(`/api/imports/${batchId}/transactions`)).data,
  });

  if (isLoading) return <p className="text-xs text-gray-400">{t("imports.loadingTx")}</p>;
  if (txs.length === 0) return <p className="text-xs text-gray-400">{t("imports.noTxFound")}</p>;

  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="text-gray-400 uppercase text-xs">
          <th className="pr-4 py-1 text-left">{t("common.date")}</th>
          <th className="pr-4 py-1 text-left">{t("analytics.txCounterparty")}</th>
          <th className="pr-4 py-1 text-right">{t("analytics.txAmount")}</th>
          <th className="pr-4 py-1 text-left">{t("common.currency")}</th>
          <th className="pr-4 py-1 text-left">{t("imports.colClassification")}</th>
        </tr>
      </thead>
      <tbody>
        {txs.map((tx) => (
          <tr key={tx.id} className="border-t border-gray-100">
            <td className="pr-4 py-1 text-gray-500">{tx.booking_date}</td>
            <td className="pr-4 py-1">{tx.counterparty_name || "—"}</td>
            <td className={`pr-4 py-1 text-right font-medium ${tx.amount < 0 ? "text-red-500" : "text-green-600"}`}>
              {tx.amount.toLocaleString("cs-CZ")}
            </td>
            <td className="pr-4 py-1 text-gray-400">{tx.currency}</td>
            <td className="pr-4 py-1"><CategorizationBadge tx={tx} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 3: Verify the app compiles without TypeScript errors**

```bash
cd frontend
npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors, build succeeds.

- [ ] **Step 4: Manual smoke test**

Start the app and navigate to the Imports page. Expand an import batch. Confirm:
- Each row shows a colored badge (`rule`, `llm`, `manual`, `transfer`, or `—`)
- Colors match: green=rule, purple=llm, blue=manual, amber=transfer, gray dash=unclassified
- Column header shows "Klasifikace" (CS) / "Classification" (EN)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Imports/BatchHistory.tsx \
        frontend/public/locales/cs/translation.json \
        frontend/public/locales/en/translation.json
git commit -m "feat: add classification badges to import history transaction rows"
```
