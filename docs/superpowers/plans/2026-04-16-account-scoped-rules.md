# Account-Scoped Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow a rule to be optionally restricted to a specific account, so the same counterparty can map to different categories depending on which account the transaction belongs to.

**Architecture:** Add a nullable `account_id` FK column to the `rules` table. Filtering happens in `categorization_service.py` before the rules list reaches `RulesEngine.apply()` — the engine stays pure. A rule with `account_id = None` applies to all accounts (current behavior); a rule with a specific account UUID applies only to that account.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), Alembic (migration), React/TypeScript/TanStack Query (frontend), i18next (translations)

---

## File Map

| File | Change |
|------|--------|
| `backend/app/db/models.py` | Add nullable `account_id` FK + relationship to `Rule` |
| `backend/app/db/migrations/versions/<rev>_add_account_id_to_rules.py` | New migration |
| `backend/app/api/rules.py` | Add `account_id` to schemas + include in `_load_rules` dict |
| `backend/app/services/categorization_service.py` | Filter rules by account before engine call |
| `backend/tests/test_rules_engine.py` | Tests for account-scoped filtering via engine |
| `frontend/src/api/rules.ts` | Add `account_id?: string \| null` to `Rule` type |
| `frontend/src/pages/Rules/RuleForm.tsx` | Add account selector dropdown |
| `frontend/src/pages/Rules/index.tsx` | Add "Account" column to table |
| `frontend/public/locales/en/translation.json` | Add `fieldAccount` + `colAccount` keys |
| `frontend/public/locales/cs/translation.json` | Same keys in Czech |

---

### Task 1: Database migration — add account_id to rules

**Files:**
- Modify: `backend/app/db/models.py`
- Create: `backend/app/db/migrations/versions/<rev>_add_account_id_to_rules.py`

- [ ] **Step 1: Add field to the Rule model**

In `backend/app/db/models.py`, add after the `created_at` field inside `class Rule`:

```python
account_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True
)
account: Mapped["Account | None"] = relationship()
```

- [ ] **Step 2: Write failing test to confirm the field exists**

```python
# backend/tests/test_rules_engine.py — add at the bottom

def make_rule_with_account(match_type, match_value, account_id, category_id=None, priority=100):
    return {
        "id": uuid.uuid4(),
        "match_type": match_type,
        "match_value": match_value,
        "category_id": category_id or uuid.uuid4(),
        "priority": priority,
        "enabled": True,
        "account_id": account_id,
    }

def test_account_scoped_rule_matches_correct_account():
    """A rule with account_id only matches transactions from that account."""
    account_a = uuid.uuid4()
    account_b = uuid.uuid4()
    tx = make_tx(counterparty_name="ALBERT")
    rule = make_rule_with_account("counterparty_contains", {"value": "albert"}, account_id=account_a)

    # filter mimics what categorization_service does
    filtered_for_a = [r for r in [rule] if r.get("account_id") is None or r["account_id"] == account_a]
    filtered_for_b = [r for r in [rule] if r.get("account_id") is None or r["account_id"] == account_b]

    assert RulesEngine.apply(tx, filtered_for_a) is not None
    assert RulesEngine.apply(tx, filtered_for_b) is None

def test_global_rule_matches_any_account():
    """A rule with account_id=None applies to all accounts."""
    account_a = uuid.uuid4()
    account_b = uuid.uuid4()
    tx = make_tx(counterparty_name="ALBERT")
    rule = make_rule("counterparty_contains", {"value": "albert"})  # no account_id

    for acct in [account_a, account_b]:
        filtered = [r for r in [rule] if r.get("account_id") is None or r["account_id"] == acct]
        assert RulesEngine.apply(tx, filtered) is not None

def test_account_scoped_rule_higher_priority_wins():
    """Account-specific rule wins over global rule when priorities conflict."""
    account_a = uuid.uuid4()
    cat_specific = uuid.uuid4()
    cat_global = uuid.uuid4()
    tx = make_tx(counterparty_name="ALBERT")

    rule_specific = make_rule_with_account("counterparty_contains", {"value": "albert"}, account_id=account_a, category_id=cat_specific, priority=200)
    rule_global = make_rule("counterparty_contains", {"value": "albert"}, cat_global, priority=100)

    rules = [rule_specific, rule_global]
    filtered = [r for r in rules if r.get("account_id") is None or r["account_id"] == account_a]
    result = RulesEngine.apply(tx, filtered)
    assert result.category_id == cat_specific
```

- [ ] **Step 3: Run tests to confirm they pass (engine code doesn't change)**

```bash
cd backend
python -m pytest tests/test_rules_engine.py -v
```

Expected: all 3 new tests PASS (filtering logic is in the test itself, not in the engine)

- [ ] **Step 4: Create Alembic migration**

Create `backend/app/db/migrations/versions/<rev>_add_account_id_to_rules.py` with a new unique revision ID (e.g. `a9b8c7d6e5f4`):

```python
"""add_account_id_to_rules

Revision ID: a9b8c7d6e5f4
Revises: 020befd00102
Create Date: 2026-04-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = '020befd00102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'rules',
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=True)
    )
    op.create_index('ix_rules_account_id', 'rules', ['account_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_rules_account_id', table_name='rules')
    op.drop_column('rules', 'account_id')
```

- [ ] **Step 5: Run migration**

```bash
cd backend
alembic upgrade head
```

Expected: `Running upgrade 020befd00102 -> a9b8c7d6e5f4, add_account_id_to_rules`

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/models.py backend/app/db/migrations/versions/a9b8c7d6e5f4_add_account_id_to_rules.py backend/tests/test_rules_engine.py
git commit -m "feat: add account_id to Rule model and migration"
```

---

### Task 2: Backend API — expose account_id in rules endpoints

**Files:**
- Modify: `backend/app/api/rules.py`
- Modify: `backend/app/services/categorization_service.py`

- [ ] **Step 1: Update Pydantic schemas in api/rules.py**

Replace the existing schemas with:

```python
class RuleCreate(BaseModel):
    name: str
    priority: int = 100
    match_type: str
    match_value: dict
    category_id: uuid.UUID
    account_id: uuid.UUID | None = None

class RuleUpdate(BaseModel):
    name: str | None = None
    priority: int | None = None
    match_type: str | None = None
    match_value: dict | None = None
    category_id: uuid.UUID | None = None
    enabled: bool | None = None
    account_id: uuid.UUID | None = None

class RuleOut(BaseModel):
    id: uuid.UUID
    name: str
    priority: int
    match_type: str
    match_value: dict
    category_id: uuid.UUID
    account_id: uuid.UUID | None
    enabled: bool
    hit_count: int
    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Update categorization_service._load_rules to include account_id**

In `backend/app/services/categorization_service.py`, update `_load_rules`:

```python
async def _load_rules(self) -> list[dict]:
    result = await self._db.execute(
        select(Rule).where(Rule.enabled == True).order_by(Rule.priority.desc())
    )
    rules = result.scalars().all()
    return [
        {
            "id": r.id,
            "match_type": r.match_type,
            "match_value": r.match_value,
            "category_id": r.category_id,
            "priority": r.priority,
            "enabled": r.enabled,
            "account_id": r.account_id,
        }
        for r in rules
    ]
```

- [ ] **Step 3: Add filtering helper and apply it in _categorize_one and _categorize_one_rules_only**

Add a static helper after `_load_rules`:

```python
@staticmethod
def _rules_for_account(rules: list[dict], account_id) -> list[dict]:
    return [r for r in rules if r.get("account_id") is None or r["account_id"] == account_id]
```

In `_categorize_one`, replace:
```python
match = RulesEngine.apply(row, rules)
```
with:
```python
match = RulesEngine.apply(row, self._rules_for_account(rules, tx.account_id))
```

In `_categorize_one_rules_only`, replace:
```python
match = RulesEngine.apply(row, rules)
```
with:
```python
match = RulesEngine.apply(row, self._rules_for_account(rules, tx.account_id))
```

- [ ] **Step 4: Start backend and verify the endpoint returns account_id**

```bash
cd backend
uvicorn app.main:app --reload --port 8300
curl http://localhost:8300/api/rules | python3 -m json.tool | grep account_id
```

Expected: `"account_id": null` for each existing rule.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/rules.py backend/app/services/categorization_service.py
git commit -m "feat: expose account_id in rules API and filter by account during categorization"
```

---

### Task 3: Frontend — account_id in API client + RuleForm + Rules table

**Files:**
- Modify: `frontend/src/api/rules.ts`
- Modify: `frontend/src/pages/Rules/RuleForm.tsx`
- Modify: `frontend/src/pages/Rules/index.tsx`
- Modify: `frontend/public/locales/en/translation.json`
- Modify: `frontend/public/locales/cs/translation.json`

- [ ] **Step 1: Update Rule type in frontend/src/api/rules.ts**

Add `account_id` to the `Rule` interface:

```typescript
export interface Rule {
  id: string;
  name: string;
  priority: number;
  match_type: string;
  match_value: Record<string, unknown>;
  category_id: string;
  account_id: string | null;
  enabled: boolean;
  hit_count: number;
}
```

Also update `createRule` and `updateRule` to allow `account_id`:

```typescript
export async function createRule(
  body: Omit<Rule, "id" | "hit_count">
): Promise<Rule> {
  const { data } = await client.post<Rule>("/api/rules", body);
  return data;
}

export async function updateRule(
  id: string,
  body: Partial<Omit<Rule, "id" | "hit_count">>
): Promise<Rule> {
  const { data } = await client.patch<Rule>(`/api/rules/${id}`, body);
  return data;
}
```

(No change needed in function signatures — `account_id` fits naturally as part of `Omit<Rule, "id" | "hit_count">`)

- [ ] **Step 2: Add i18n keys — English**

In `frontend/public/locales/en/translation.json`, inside the `"rules"` object, add:

```json
"fieldAccount": "Account (optional)",
"colAccount": "Account",
"accountAny": "Any account"
```

- [ ] **Step 3: Add i18n keys — Czech**

In `frontend/public/locales/cs/translation.json`, inside the `"rules"` object, add:

```json
"fieldAccount": "Účet (volitelný)",
"colAccount": "Účet",
"accountAny": "Libovolný účet"
```

- [ ] **Step 4: Add account selector to RuleForm**

In `frontend/src/pages/Rules/RuleForm.tsx`:

1. Add `listAccounts` import:
```typescript
import { listAccounts } from "../../api/accounts";
import type { Account } from "../../api/accounts";
```

2. Add account state after the existing `useState` calls:
```typescript
const [accountId, setAccountId] = useState<string>(rule?.account_id ?? "");
```

3. Add accounts query after the `groups` query:
```typescript
const { data: accounts = [] } = useQuery({
  queryKey: ["accounts"],
  queryFn: listAccounts,
});
```

4. Update the `save` mutation body to include `account_id`:
```typescript
const body = {
  name,
  match_type: matchType,
  match_value: buildMatchValue(matchType, matchValue),
  category_id: categoryId,
  priority,
  enabled,
  account_id: accountId !== "" ? accountId : null,
};
```

5. Add the account selector field in the JSX, after the match value field and before the category field:
```tsx
<div>
  <label className="block text-sm font-medium text-gray-700 mb-1">
    {t("rules.fieldAccount")}
  </label>
  <select
    value={accountId}
    onChange={(e) => setAccountId(e.target.value)}
    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
  >
    <option value="">{t("rules.accountAny")}</option>
    {accounts.filter((a) => a.is_active).map((a) => (
      <option key={a.id} value={a.id}>
        {a.name}
      </option>
    ))}
  </select>
</div>
```

- [ ] **Step 5: Add "Account" column to the rules list table**

In `frontend/src/pages/Rules/index.tsx`:

1. Add accounts query:
```typescript
import { listAccounts } from "../../api/accounts";
import type { Account } from "../../api/accounts";
// ...
const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });

const accountById = useMemo(() => {
  const map: Record<string, string> = {};
  accounts.forEach((a) => { map[a.id] = a.name; });
  return map;
}, [accounts]);
```

2. Add `t("rules.colAccount")` to the column headers array (after `t("rules.colMatchValue")`):
```typescript
{[
  t("rules.colPriority"),
  t("rules.colName"),
  t("rules.colType"),
  t("rules.colMatchValue"),
  t("rules.colAccount"),   // ← new
  t("rules.colCategory"),
  t("rules.colHits"),
  t("rules.colEnabled"),
  "",
].map(...)}
```

3. Add the account cell in the row, after the match value cell and before the category cell:
```tsx
<td className="px-4 py-3 text-xs text-gray-500">
  {r.account_id ? accountById[r.account_id] ?? "—" : <span className="text-gray-300">{t("rules.accountAny")}</span>}
</td>
```

- [ ] **Step 6: Verify frontend compiles without errors**

```bash
cd frontend
npm run build 2>&1 | tail -20
```

Expected: `built in Xs` with no TypeScript errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/rules.ts frontend/src/pages/Rules/RuleForm.tsx frontend/src/pages/Rules/index.tsx frontend/public/locales/en/translation.json frontend/public/locales/cs/translation.json
git commit -m "feat: add account selector to rule form and account column to rules list"
```

---

## Self-Review

**Spec coverage:**
- ✅ Rules can be created/edited for a specific account (Task 3: RuleForm selector)
- ✅ Rules without an account apply to all accounts (Task 2: `_rules_for_account` filter, `account_id=None`)
- ✅ Priority still works across global and account-specific rules (priority order unchanged in engine)
- ✅ Account column visible in list so user can see which rules are scoped (Task 3: index.tsx)
- ✅ DB persists account_id (Task 1: migration)
- ✅ Existing rules unaffected (`account_id=None` means all accounts — backward compatible)

**Placeholder scan:** None found.

**Type consistency:** `account_id: uuid.UUID | None` in Python models/schemas; `account_id: string | null` in TypeScript — consistent. `_rules_for_account` uses `r.get("account_id")` which returns `None` for old-format rule dicts (backward safe).
