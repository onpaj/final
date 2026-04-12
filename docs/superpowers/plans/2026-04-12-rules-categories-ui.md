# Rules & Categories UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full CRUD UI for rules (create/edit/toggle/delete) and categories (groups + categories with drag-to-reorder), plus a new `counterparty_account_equals` match type.

**Architecture:** Slide-over panel for create/edit forms; two-column layout for categories page; @dnd-kit/sortable for reordering; backend CRUD endpoints added to existing routers.

**Tech Stack:** FastAPI, SQLAlchemy async, React 19, TanStack Query, Tailwind CSS, @dnd-kit/core + @dnd-kit/sortable, react-i18next.

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `backend/app/services/rules_engine.py` | Add `counterparty_account_equals` match type |
| Modify | `backend/tests/test_rules_engine.py` | Tests for new match type |
| Modify | `backend/app/api/categories.py` | Add CRUD endpoints for groups & categories |
| Create | `backend/tests/test_categories_api.py` | Tests for new endpoints |
| Modify | `frontend/src/api/rules.ts` | Add `updateRule` |
| Modify | `frontend/src/api/categories.ts` | Add CRUD methods + expand types |
| Create | `frontend/src/components/SlideOverPanel.tsx` | Reusable right-side panel |
| Create | `frontend/src/pages/Rules/RuleForm.tsx` | Rule create/edit form |
| Modify | `frontend/src/pages/Rules/index.tsx` | Add New/Edit buttons, enable toggle, panel |
| Create | `frontend/src/pages/Categories/index.tsx` | Two-column categories management page |
| Create | `frontend/src/pages/Categories/CategoryForm.tsx` | Category create/edit form |
| Modify | `frontend/src/components/NavBar.tsx` | Add `/categories` nav link |
| Modify | `frontend/src/App.tsx` | Add `/categories` route |
| Modify | `frontend/public/locales/en/translation.json` | New i18n keys |
| Modify | `frontend/public/locales/cs/translation.json` | Czech translations for new keys |

---

## Task 1: Add `counterparty_account_equals` to rules engine

**Files:**
- Modify: `backend/app/services/rules_engine.py`
- Modify: `backend/tests/test_rules_engine.py`

- [ ] **Step 1: Add failing tests to `backend/tests/test_rules_engine.py`**

Append after the last existing test:

```python
def test_counterparty_account_equals_match():
    tx = make_tx(counterparty_account="CZ6508000000192000145399")
    rule = make_rule("counterparty_account_equals", {"account": "CZ6508000000192000145399"})
    result = RulesEngine.apply(tx, [rule])
    assert result is not None
    assert result.category_id == rule["category_id"]

def test_counterparty_account_equals_no_match():
    tx = make_tx(counterparty_account="CZ6508000000192000145399")
    rule = make_rule("counterparty_account_equals", {"account": "CZ9999999999999999999999"})
    assert RulesEngine.apply(tx, [rule]) is None

def test_counterparty_account_equals_none_account():
    tx = make_tx(counterparty_account=None)
    rule = make_rule("counterparty_account_equals", {"account": "CZ6508000000192000145399"})
    assert RulesEngine.apply(tx, [rule]) is None

def test_counterparty_account_equals_case_insensitive():
    tx = make_tx(counterparty_account="cz6508000000192000145399")
    rule = make_rule("counterparty_account_equals", {"account": "CZ6508000000192000145399"})
    assert RulesEngine.apply(tx, [rule]) is not None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_rules_engine.py::test_counterparty_account_equals_match -v
```

Expected: `FAILED` — `AssertionError` (returns None because match type is unknown).

- [ ] **Step 3: Add `counterparty_account_equals` to `rules_engine.py`**

In `_matches_single`, after the `description_contains` block (line 23) and before the `_logger.warning` line, insert:

```python
        if match_type == "counterparty_account_equals":
            return (tx.counterparty_account or "").lower() == match_value["account"].lower()
```

- [ ] **Step 4: Run all rules engine tests**

```bash
cd backend && python -m pytest tests/test_rules_engine.py -v
```

Expected: all tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/services/rules_engine.py tests/test_rules_engine.py
git commit -m "feat: add counterparty_account_equals match type to rules engine"
```

---

## Task 2: Category & Group CRUD backend endpoints

**Files:**
- Modify: `backend/app/api/categories.py`
- Create: `backend/tests/test_categories_api.py`

- [ ] **Step 1: Create `backend/tests/test_categories_api.py`**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_create_group(client):
    resp = await client.post("/api/categories/groups", json={"name": "Living", "color": "#6366f1"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Living"
    assert data["color"] == "#6366f1"
    assert "id" in data


async def test_update_group(client):
    create = await client.post("/api/categories/groups", json={"name": "Old Group"})
    group_id = create.json()["id"]
    resp = await client.patch(f"/api/categories/groups/{group_id}", json={"name": "New Group"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Group"


async def test_delete_group(client):
    create = await client.post("/api/categories/groups", json={"name": "ToDelete"})
    group_id = create.json()["id"]
    resp = await client.delete(f"/api/categories/groups/{group_id}")
    assert resp.status_code == 204


async def test_create_category(client):
    group = await client.post("/api/categories/groups", json={"name": "Food"})
    group_id = group.json()["id"]
    resp = await client.post("/api/categories", json={
        "group_id": group_id,
        "name": "Groceries",
        "color": "#22c55e",
        "is_income": False,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Groceries"
    assert data["group_id"] == group_id


async def test_update_category(client):
    group = await client.post("/api/categories/groups", json={"name": "G"})
    group_id = group.json()["id"]
    cat = await client.post("/api/categories", json={"group_id": group_id, "name": "Old"})
    cat_id = cat.json()["id"]
    resp = await client.patch(f"/api/categories/{cat_id}", json={"name": "New", "color": "#ff0000"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"
    assert resp.json()["color"] == "#ff0000"


async def test_delete_category(client):
    group = await client.post("/api/categories/groups", json={"name": "G2"})
    group_id = group.json()["id"]
    cat = await client.post("/api/categories", json={"group_id": group_id, "name": "ToDelete"})
    cat_id = cat.json()["id"]
    resp = await client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 204


async def test_reorder_groups(client):
    g1 = (await client.post("/api/categories/groups", json={"name": "G1"})).json()
    g2 = (await client.post("/api/categories/groups", json={"name": "G2"})).json()
    resp = await client.patch("/api/categories/groups/reorder", json=[
        {"id": g1["id"], "sort_order": 1},
        {"id": g2["id"], "sort_order": 0},
    ])
    assert resp.status_code == 200


async def test_reorder_categories(client):
    group = (await client.post("/api/categories/groups", json={"name": "G"})).json()
    c1 = (await client.post("/api/categories", json={"group_id": group["id"], "name": "C1"})).json()
    c2 = (await client.post("/api/categories", json={"group_id": group["id"], "name": "C2"})).json()
    resp = await client.patch("/api/categories/reorder", json=[
        {"id": c1["id"], "sort_order": 1},
        {"id": c2["id"], "sort_order": 0},
    ])
    assert resp.status_code == 200


async def test_update_nonexistent_group_returns_404(client):
    import uuid
    resp = await client.patch(f"/api/categories/groups/{uuid.uuid4()}", json={"name": "X"})
    assert resp.status_code == 404


async def test_update_nonexistent_category_returns_404(client):
    import uuid
    resp = await client.patch(f"/api/categories/{uuid.uuid4()}", json={"name": "X"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_categories_api.py -v
```

Expected: `FAILED` — 405 Method Not Allowed (endpoints don't exist yet).

- [ ] **Step 3: Replace `backend/app/api/categories.py` with full CRUD version**

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Category, CategoryGroup

router = APIRouter()


class CategoryOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    name: str
    is_income: bool
    is_system: bool
    color: str | None
    sort_order: int
    model_config = {"from_attributes": True}


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    color: str | None
    sort_order: int
    categories: list[CategoryOut]
    model_config = {"from_attributes": True}


GroupOut.model_rebuild()


class GroupCreate(BaseModel):
    name: str
    color: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class CategoryCreate(BaseModel):
    group_id: uuid.UUID
    name: str
    color: str | None = None
    is_income: bool = False


class CategoryUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    is_income: bool | None = None


class ReorderItem(BaseModel):
    id: uuid.UUID
    sort_order: int


# ── Group routes ─────────────────────────────────────────────────────────────

@router.get("/groups", response_model=list[GroupOut])
async def list_groups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CategoryGroup).order_by(CategoryGroup.sort_order))
    groups = result.scalars().all()
    for g in groups:
        await db.refresh(g, ["categories"])
    return groups


@router.post("/groups", response_model=GroupOut, status_code=201)
async def create_group(body: GroupCreate, db: AsyncSession = Depends(get_db)):
    count_result = await db.execute(select(func.count()).select_from(CategoryGroup))
    count = count_result.scalar() or 0
    group = CategoryGroup(**body.model_dump(), sort_order=count)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    await db.refresh(group, ["categories"])
    return group


# NOTE: /groups/reorder must be defined before /groups/{group_id}
@router.patch("/groups/reorder", response_model=list[GroupOut])
async def reorder_groups(items: list[ReorderItem], db: AsyncSession = Depends(get_db)):
    for item in items:
        group = await db.get(CategoryGroup, item.id)
        if group:
            group.sort_order = item.sort_order
    await db.commit()
    result = await db.execute(select(CategoryGroup).order_by(CategoryGroup.sort_order))
    groups = result.scalars().all()
    for g in groups:
        await db.refresh(g, ["categories"])
    return groups


@router.patch("/groups/{group_id}", response_model=GroupOut)
async def update_group(group_id: uuid.UUID, body: GroupUpdate, db: AsyncSession = Depends(get_db)):
    group = await db.get(CategoryGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(group, f, v)
    await db.commit()
    await db.refresh(group)
    await db.refresh(group, ["categories"])
    return group


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(group_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    group = await db.get(CategoryGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    await db.delete(group)
    await db.commit()


# ── Category routes ───────────────────────────────────────────────────────────

@router.get("", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    return result.scalars().all()


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    count_result = await db.execute(
        select(func.count()).select_from(Category).where(Category.group_id == body.group_id)
    )
    count = count_result.scalar() or 0
    category = Category(**body.model_dump(), sort_order=count)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


# NOTE: /reorder must be defined before /{category_id}
@router.patch("/reorder", response_model=list[CategoryOut])
async def reorder_categories(items: list[ReorderItem], db: AsyncSession = Depends(get_db)):
    for item in items:
        cat = await db.get(Category, item.id)
        if cat:
            cat.sort_order = item.sort_order
    await db.commit()
    result = await db.execute(select(Category).order_by(Category.sort_order))
    return result.scalars().all()


@router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(category_id: uuid.UUID, body: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(cat, f, v)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    await db.delete(cat)
    await db.commit()
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_categories_api.py -v
```

Expected: all tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/api/categories.py tests/test_categories_api.py
git commit -m "feat: add CRUD endpoints for categories and groups"
```

---

## Task 3: Install @dnd-kit/sortable

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`

- [ ] **Step 1: Install**

```bash
cd frontend && npm install @dnd-kit/sortable
```

Expected output includes: `added 1 package` and `@dnd-kit/sortable` appears in `package.json` dependencies.

- [ ] **Step 2: Commit**

```bash
cd frontend && git add package.json package-lock.json
git commit -m "chore: add @dnd-kit/sortable"
```

---

## Task 4: Update frontend API clients

**Files:**
- Modify: `frontend/src/api/rules.ts`
- Modify: `frontend/src/api/categories.ts`

- [ ] **Step 1: Add `updateRule` to `frontend/src/api/rules.ts`**

Append after the `createRule` function:

```typescript
export async function updateRule(
  id: string,
  body: Partial<Omit<Rule, "id" | "hit_count">>
): Promise<Rule> {
  const { data } = await client.patch<Rule>(`/api/rules/${id}`, body);
  return data;
}
```

- [ ] **Step 2: Replace `frontend/src/api/categories.ts` with expanded version**

```typescript
import client from "./client";

export interface Category {
  id: string;
  group_id: string;
  name: string;
  is_income: boolean;
  is_system: boolean;
  color: string | null;
  sort_order: number;
}

export interface CategoryGroup {
  id: string;
  name: string;
  color: string | null;
  sort_order: number;
  categories: Category[];
}

export interface ReorderItem {
  id: string;
  sort_order: number;
}

export async function listCategoryGroups(): Promise<CategoryGroup[]> {
  const { data } = await client.get<CategoryGroup[]>("/api/categories/groups");
  return data;
}

export async function listCategories(): Promise<Category[]> {
  const { data } = await client.get<Category[]>("/api/categories");
  return data;
}

export async function createGroup(body: { name: string; color?: string }): Promise<CategoryGroup> {
  const { data } = await client.post<CategoryGroup>("/api/categories/groups", body);
  return data;
}

export async function updateGroup(id: string, body: { name?: string; color?: string }): Promise<CategoryGroup> {
  const { data } = await client.patch<CategoryGroup>(`/api/categories/groups/${id}`, body);
  return data;
}

export async function deleteGroup(id: string): Promise<void> {
  await client.delete(`/api/categories/groups/${id}`);
}

export async function reorderGroups(items: ReorderItem[]): Promise<CategoryGroup[]> {
  const { data } = await client.patch<CategoryGroup[]>("/api/categories/groups/reorder", items);
  return data;
}

export async function createCategory(body: {
  group_id: string;
  name: string;
  color?: string;
  is_income?: boolean;
}): Promise<Category> {
  const { data } = await client.post<Category>("/api/categories", body);
  return data;
}

export async function updateCategory(
  id: string,
  body: { name?: string; color?: string; is_income?: boolean }
): Promise<Category> {
  const { data } = await client.patch<Category>(`/api/categories/${id}`, body);
  return data;
}

export async function deleteCategory(id: string): Promise<void> {
  await client.delete(`/api/categories/${id}`);
}

export async function reorderCategories(items: ReorderItem[]): Promise<Category[]> {
  const { data } = await client.patch<Category[]>("/api/categories/reorder", items);
  return data;
}
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/api/rules.ts src/api/categories.ts
git commit -m "feat: add updateRule and categories CRUD to API clients"
```

---

## Task 5: SlideOverPanel component

**Files:**
- Create: `frontend/src/components/SlideOverPanel.tsx`

- [ ] **Step 1: Create `frontend/src/components/SlideOverPanel.tsx`**

```tsx
import { ReactNode } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export default function SlideOverPanel({ open, onClose, title, children }: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="fixed inset-0 bg-black/30" onClick={onClose} />
      <div className="relative z-50 w-96 bg-white shadow-xl flex flex-col h-full">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd frontend && git add src/components/SlideOverPanel.tsx
git commit -m "feat: add SlideOverPanel component"
```

---

## Task 6: Rules page — create/edit/toggle + i18n

**Files:**
- Create: `frontend/src/pages/Rules/RuleForm.tsx`
- Modify: `frontend/src/pages/Rules/index.tsx`
- Modify: `frontend/public/locales/en/translation.json`
- Modify: `frontend/public/locales/cs/translation.json`

- [ ] **Step 1: Create `frontend/src/pages/Rules/RuleForm.tsx`**

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Rule, createRule, updateRule } from "../../api/rules";
import { listCategoryGroups } from "../../api/categories";

interface Props {
  rule?: Rule;
  onClose: () => void;
}

type MatchType = "counterparty_account_equals" | "counterparty_contains" | "description_contains";

function getInitialMatchValue(rule?: Rule): string {
  if (!rule) return "";
  if (rule.match_type === "counterparty_account_equals") {
    return (rule.match_value.account as string) ?? "";
  }
  return (rule.match_value.value as string) ?? "";
}

function buildMatchValue(type: MatchType, value: string): Record<string, string> {
  if (type === "counterparty_account_equals") return { account: value };
  return { value };
}

export default function RuleForm({ rule, onClose }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState(rule?.name ?? "");
  const [matchType, setMatchType] = useState<MatchType>(
    (rule?.match_type as MatchType) ?? "counterparty_account_equals"
  );
  const [matchValue, setMatchValue] = useState(() => getInitialMatchValue(rule));
  const [categoryId, setCategoryId] = useState(rule?.category_id ?? "");
  const [priority, setPriority] = useState(rule?.priority ?? 100);
  const [enabled, setEnabled] = useState(rule?.enabled ?? true);

  const { data: groups = [] } = useQuery({
    queryKey: ["category-groups"],
    queryFn: listCategoryGroups,
  });

  const save = useMutation({
    mutationFn: () => {
      const body = {
        name,
        match_type: matchType,
        match_value: buildMatchValue(matchType, matchValue),
        category_id: categoryId,
        priority,
        enabled,
      };
      return rule ? updateRule(rule.id, body) : createRule(body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rules"] });
      onClose();
    },
  });

  const matchValueLabels: Record<MatchType, string> = {
    counterparty_account_equals: t("rules.fieldMatchValue.counterparty_account_equals"),
    counterparty_contains: t("rules.fieldMatchValue.counterparty_contains"),
    description_contains: t("rules.fieldMatchValue.description_contains"),
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
      className="space-y-4"
    >
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("rules.fieldName")}</label>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("rules.fieldMatchType")}</label>
        <select
          value={matchType}
          onChange={(e) => {
            setMatchType(e.target.value as MatchType);
            setMatchValue("");
          }}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        >
          <option value="counterparty_account_equals">{t("rules.matchType.counterparty_account_equals")}</option>
          <option value="counterparty_contains">{t("rules.matchType.counterparty_contains")}</option>
          <option value="description_contains">{t("rules.matchType.description_contains")}</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{matchValueLabels[matchType]}</label>
        <input
          required
          value={matchValue}
          onChange={(e) => setMatchValue(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("rules.fieldCategory")}</label>
        <select
          required
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        >
          <option value="">—</option>
          {groups.map((g) => (
            <optgroup key={g.id} label={g.name}>
              {g.categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("rules.fieldPriority")}</label>
        <input
          type="number"
          value={priority}
          onChange={(e) => setPriority(Number(e.target.value))}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="enabled"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="rounded"
        />
        <label htmlFor="enabled" className="text-sm font-medium text-gray-700">
          {t("rules.fieldEnabled")}
        </label>
      </div>
      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={save.isPending}
          className="flex-1 bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {t("common.save")}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex-1 border border-gray-300 px-4 py-2 rounded text-sm font-medium hover:bg-gray-50"
        >
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Replace `frontend/src/pages/Rules/index.tsx`**

```tsx
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Rule, deleteRule, listRules, updateRule } from "../../api/rules";
import { listCategoryGroups } from "../../api/categories";
import SlideOverPanel from "../../components/SlideOverPanel";
import RuleForm from "./RuleForm";

export default function RulesPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: rules = [] } = useQuery({ queryKey: ["rules"], queryFn: listRules });
  const { data: groups = [] } = useQuery({ queryKey: ["category-groups"], queryFn: listCategoryGroups });
  const [panel, setPanel] = useState<{ rule?: Rule } | null>(null);

  const categoryById = useMemo(() => {
    const map: Record<string, string> = {};
    groups.forEach((g) => g.categories.forEach((c) => { map[c.id] = c.name; }));
    return map;
  }, [groups]);

  const remove = useMutation({
    mutationFn: deleteRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => updateRule(id, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t("rules.title")}</h1>
        <button
          onClick={() => setPanel({})}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700"
        >
          + {t("rules.newRule")}
        </button>
      </div>
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              {[
                t("rules.colPriority"),
                t("rules.colName"),
                t("rules.colType"),
                t("rules.colMatchValue"),
                t("rules.colCategory"),
                t("rules.colHits"),
                t("rules.colEnabled"),
                "",
              ].map((h, i) => (
                <th key={i} className="px-4 py-2 text-left">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3">{r.priority}</td>
                <td className="px-4 py-3 font-medium">{r.name}</td>
                <td className="px-4 py-3 text-xs">
                  {t(`rules.matchType.${r.match_type}`, r.match_type)}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 max-w-[160px] truncate">
                  {String(r.match_value.account ?? r.match_value.value ?? "")}
                </td>
                <td className="px-4 py-3 text-xs">{categoryById[r.category_id] ?? "—"}</td>
                <td className="px-4 py-3">{r.hit_count}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggle.mutate({ id: r.id, enabled: !r.enabled })}
                    className={`px-2 py-0.5 rounded text-xs ${
                      r.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {r.enabled ? t("rules.active") : t("rules.disabled")}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-3">
                    <button
                      onClick={() => setPanel({ rule: r })}
                      className="text-blue-500 text-xs hover:underline"
                    >
                      {t("common.edit")}
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(t("rules.deleteConfirm"))) remove.mutate(r.id);
                      }}
                      className="text-red-500 text-xs hover:underline"
                    >
                      {t("common.delete")}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <SlideOverPanel
        open={panel !== null}
        onClose={() => setPanel(null)}
        title={panel?.rule ? t("rules.editRule") : t("rules.newRule")}
      >
        {panel !== null && <RuleForm rule={panel.rule} onClose={() => setPanel(null)} />}
      </SlideOverPanel>
    </div>
  );
}
```

- [ ] **Step 3: Add new keys to `frontend/public/locales/en/translation.json`**

In the `"common"` object, add:
```json
"save": "Save",
"cancel": "Cancel",
"edit": "Edit"
```

Replace the entire `"rules"` object with:
```json
"rules": {
  "title": "Categorization Rules",
  "newRule": "New Rule",
  "editRule": "Edit Rule",
  "colPriority": "Priority",
  "colName": "Name",
  "colType": "Type",
  "colMatchValue": "Match Value",
  "colCategory": "Category",
  "colHits": "Hits",
  "colEnabled": "Enabled",
  "active": "Active",
  "disabled": "Disabled",
  "deleteConfirm": "Delete this rule?",
  "matchType": {
    "counterparty_account_equals": "Account Number",
    "counterparty_contains": "Counterparty Name",
    "description_contains": "Description"
  },
  "fieldName": "Name",
  "fieldMatchType": "Match type",
  "fieldMatchValue": {
    "counterparty_account_equals": "IBAN / account number (exact match)",
    "counterparty_contains": "Name contains",
    "description_contains": "Description contains"
  },
  "fieldCategory": "Category",
  "fieldPriority": "Priority",
  "fieldEnabled": "Enabled"
}
```

- [ ] **Step 4: Add same keys to `frontend/public/locales/cs/translation.json`**

In the `"common"` object, add:
```json
"save": "Uložit",
"cancel": "Zrušit",
"edit": "Upravit"
```

Replace the entire `"rules"` object with:
```json
"rules": {
  "title": "Pravidla kategorizace",
  "newRule": "Nové pravidlo",
  "editRule": "Upravit pravidlo",
  "colPriority": "Priorita",
  "colName": "Název",
  "colType": "Typ",
  "colMatchValue": "Hodnota",
  "colCategory": "Kategorie",
  "colHits": "Shody",
  "colEnabled": "Aktivní",
  "active": "Aktivní",
  "disabled": "Vypnuto",
  "deleteConfirm": "Smazat toto pravidlo?",
  "matchType": {
    "counterparty_account_equals": "Číslo účtu",
    "counterparty_contains": "Název protistrany",
    "description_contains": "Popis"
  },
  "fieldName": "Název",
  "fieldMatchType": "Typ shody",
  "fieldMatchValue": {
    "counterparty_account_equals": "IBAN / číslo účtu (přesná shoda)",
    "counterparty_contains": "Název obsahuje",
    "description_contains": "Popis obsahuje"
  },
  "fieldCategory": "Kategorie",
  "fieldPriority": "Priorita",
  "fieldEnabled": "Aktivní"
}
```

- [ ] **Step 5: Commit**

```bash
cd frontend && git add src/pages/Rules/ src/components/SlideOverPanel.tsx public/locales/
git commit -m "feat: rules page create/edit/toggle + i18n keys"
```

---

## Task 7: Categories page, nav, route, i18n

**Files:**
- Create: `frontend/src/pages/Categories/index.tsx`
- Create: `frontend/src/pages/Categories/CategoryForm.tsx`
- Modify: `frontend/src/components/NavBar.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/public/locales/en/translation.json`
- Modify: `frontend/public/locales/cs/translation.json`

- [ ] **Step 1: Create `frontend/src/pages/Categories/CategoryForm.tsx`**

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Category, createCategory, updateCategory } from "../../api/categories";

interface Props {
  groupId: string;
  category?: Category;
  onClose: () => void;
}

export default function CategoryForm({ groupId, category, onClose }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState(category?.name ?? "");
  const [color, setColor] = useState(category?.color ?? "#6366f1");
  const [isIncome, setIsIncome] = useState(category?.is_income ?? false);

  const save = useMutation({
    mutationFn: () =>
      category
        ? updateCategory(category.id, { name, color, is_income: isIncome })
        : createCategory({ group_id: groupId, name, color, is_income: isIncome }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["category-groups"] });
      onClose();
    },
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
      className="space-y-4"
    >
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("categories.fieldName")}</label>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("categories.fieldColor")}</label>
        <input
          type="color"
          value={color ?? "#6366f1"}
          onChange={(e) => setColor(e.target.value)}
          className="w-full h-10 border border-gray-300 rounded cursor-pointer p-1"
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_income"
          checked={isIncome}
          onChange={(e) => setIsIncome(e.target.checked)}
          className="rounded"
        />
        <label htmlFor="is_income" className="text-sm font-medium text-gray-700">
          {t("categories.fieldIsIncome")}
        </label>
      </div>
      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={save.isPending}
          className="flex-1 bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {t("common.save")}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex-1 border border-gray-300 px-4 py-2 rounded text-sm font-medium hover:bg-gray-50"
        >
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Create `frontend/src/pages/Categories/index.tsx`**

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  DndContext,
  closestCenter,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  Category,
  CategoryGroup,
  listCategoryGroups,
  createGroup,
  updateGroup,
  deleteGroup,
  reorderGroups,
  deleteCategory,
  reorderCategories,
} from "../../api/categories";
import SlideOverPanel from "../../components/SlideOverPanel";
import CategoryForm from "./CategoryForm";

function SortableGroupItem({
  group,
  selected,
  editing,
  onSelect,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onDelete,
}: {
  group: CategoryGroup;
  selected: boolean;
  editing: boolean;
  onSelect: () => void;
  onStartEdit: () => void;
  onSaveEdit: (name: string, color: string) => void;
  onCancelEdit: () => void;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: group.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  const [editName, setEditName] = useState(group.name);
  const [editColor, setEditColor] = useState(group.color ?? "#6366f1");

  if (editing) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 border-t border-gray-100">
        <input
          autoFocus
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onSaveEdit(editName, editColor);
            if (e.key === "Escape") onCancelEdit();
          }}
          className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
        />
        <input
          type="color"
          value={editColor}
          onChange={(e) => setEditColor(e.target.value)}
          className="w-8 h-8 border-0 cursor-pointer rounded p-0"
        />
        <button onClick={() => onSaveEdit(editName, editColor)} className="text-blue-600 text-xs hover:underline">✓</button>
        <button onClick={onCancelEdit} className="text-gray-500 text-xs hover:underline">✕</button>
      </div>
    );
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-2 px-3 py-2 border-t border-gray-100 ${
        selected ? "bg-blue-50" : "hover:bg-gray-50"
      }`}
    >
      <span {...attributes} {...listeners} className="text-gray-300 cursor-grab text-lg select-none">
        ⠿
      </span>
      {group.color && (
        <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: group.color }} />
      )}
      <span className="flex-1 text-sm font-medium truncate cursor-pointer" onClick={onSelect}>
        {group.name}
      </span>
      <button onClick={onStartEdit} className="text-gray-400 hover:text-gray-600 text-xs">✎</button>
      <button onClick={onDelete} className="text-gray-400 hover:text-red-500 text-xs">✕</button>
    </div>
  );
}

function SortableCategoryItem({
  category,
  onEdit,
  onDelete,
}: {
  category: Category;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: category.id });
  const style = { transform: CSS.Transform.toString(transform), transition };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 px-3 py-2 border-t border-gray-100 hover:bg-gray-50"
    >
      <span {...attributes} {...listeners} className="text-gray-300 cursor-grab text-lg select-none">
        ⠿
      </span>
      {category.color && (
        <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: category.color }} />
      )}
      <span className="flex-1 text-sm">{category.name}</span>
      {category.is_income && (
        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Income</span>
      )}
      {category.is_system && (
        <span className="text-xs text-gray-400" title="System category">🔒</span>
      )}
      <button onClick={onEdit} className="text-gray-400 hover:text-gray-600 text-xs">✎</button>
      {!category.is_system && (
        <button onClick={onDelete} className="text-gray-400 hover:text-red-500 text-xs">✕</button>
      )}
    </div>
  );
}

export default function CategoriesPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: groups = [] } = useQuery({ queryKey: ["category-groups"], queryFn: listCategoryGroups });

  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
  const [addingGroup, setAddingGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupColor, setNewGroupColor] = useState("#6366f1");
  const [categoryPanel, setCategoryPanel] = useState<{ groupId: string; category?: Category } | null>(null);

  const sensors = useSensors(useSensor(PointerSensor));
  const selectedGroup = groups.find((g) => g.id === selectedGroupId) ?? null;

  const addGroup = useMutation({
    mutationFn: (vars: { name: string; color: string }) => createGroup(vars),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["category-groups"] });
      setAddingGroup(false);
      setNewGroupName("");
    },
  });

  const patchGroup = useMutation({
    mutationFn: (vars: { id: string; name: string; color: string }) =>
      updateGroup(vars.id, { name: vars.name, color: vars.color }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["category-groups"] });
      setEditingGroupId(null);
    },
  });

  const removeGroup = useMutation({
    mutationFn: deleteGroup,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["category-groups"] });
      setSelectedGroupId(null);
    },
  });

  const reorderGroupsMutation = useMutation({
    mutationFn: reorderGroups,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["category-groups"] }),
  });

  const removeCategory = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["category-groups"] }),
  });

  const reorderCategoriesMutation = useMutation({
    mutationFn: reorderCategories,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["category-groups"] }),
  });

  function handleGroupDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = groups.findIndex((g) => g.id === active.id);
    const newIndex = groups.findIndex((g) => g.id === over.id);
    const reordered = arrayMove(groups, oldIndex, newIndex);
    reorderGroupsMutation.mutate(reordered.map((g, i) => ({ id: g.id, sort_order: i })));
  }

  function handleCategoryDragEnd(event: DragEndEvent) {
    if (!selectedGroup) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const cats = selectedGroup.categories;
    const oldIndex = cats.findIndex((c) => c.id === active.id);
    const newIndex = cats.findIndex((c) => c.id === over.id);
    const reordered = arrayMove(cats, oldIndex, newIndex);
    reorderCategoriesMutation.mutate(reordered.map((c, i) => ({ id: c.id, sort_order: i })));
  }

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">{t("categories.title")}</h1>
      <div className="flex gap-6">
        {/* Left: Groups */}
        <div className="w-80 flex-shrink-0">
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100">
              <span className="text-sm font-semibold text-gray-700">{t("categories.groupsTitle")}</span>
            </div>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleGroupDragEnd}>
              <SortableContext items={groups.map((g) => g.id)} strategy={verticalListSortingStrategy}>
                {groups.map((g) => (
                  <SortableGroupItem
                    key={g.id}
                    group={g}
                    selected={selectedGroupId === g.id}
                    editing={editingGroupId === g.id}
                    onSelect={() => setSelectedGroupId(g.id)}
                    onStartEdit={() => setEditingGroupId(g.id)}
                    onSaveEdit={(name, color) => patchGroup.mutate({ id: g.id, name, color })}
                    onCancelEdit={() => setEditingGroupId(null)}
                    onDelete={() => removeGroup.mutate(g.id)}
                  />
                ))}
              </SortableContext>
            </DndContext>
            {addingGroup ? (
              <div className="flex items-center gap-2 px-3 py-2 border-t border-gray-100">
                <input
                  autoFocus
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newGroupName.trim()) addGroup.mutate({ name: newGroupName, color: newGroupColor });
                    if (e.key === "Escape") setAddingGroup(false);
                  }}
                  placeholder={t("categories.fieldName")}
                  className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
                />
                <input
                  type="color"
                  value={newGroupColor}
                  onChange={(e) => setNewGroupColor(e.target.value)}
                  className="w-8 h-8 border-0 cursor-pointer rounded p-0"
                />
                <button
                  onClick={() => { if (newGroupName.trim()) addGroup.mutate({ name: newGroupName, color: newGroupColor }); }}
                  className="text-blue-600 text-xs hover:underline"
                >
                  ✓
                </button>
                <button onClick={() => setAddingGroup(false)} className="text-gray-500 text-xs hover:underline">✕</button>
              </div>
            ) : (
              <button
                onClick={() => setAddingGroup(true)}
                className="w-full px-4 py-2 text-sm text-blue-600 hover:bg-gray-50 text-left border-t border-gray-100"
              >
                + {t("categories.newGroup")}
              </button>
            )}
          </div>
        </div>

        {/* Right: Categories */}
        <div className="flex-1">
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-700">
                {selectedGroup ? selectedGroup.name : t("categories.categoriesTitle")}
              </span>
              {selectedGroup && (
                <button
                  onClick={() => setCategoryPanel({ groupId: selectedGroup.id })}
                  className="text-sm text-blue-600 hover:underline"
                >
                  + {t("categories.newCategory")}
                </button>
              )}
            </div>
            {!selectedGroup ? (
              <p className="px-4 py-8 text-sm text-gray-400 text-center">{t("categories.selectGroup")}</p>
            ) : (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleCategoryDragEnd}>
                <SortableContext
                  items={selectedGroup.categories.map((c) => c.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {selectedGroup.categories.map((c) => (
                    <SortableCategoryItem
                      key={c.id}
                      category={c}
                      onEdit={() => setCategoryPanel({ groupId: selectedGroup.id, category: c })}
                      onDelete={() => removeCategory.mutate(c.id)}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            )}
          </div>
        </div>
      </div>

      <SlideOverPanel
        open={categoryPanel !== null}
        onClose={() => setCategoryPanel(null)}
        title={categoryPanel?.category ? t("categories.editCategory") : t("categories.newCategory")}
      >
        {categoryPanel && (
          <CategoryForm
            groupId={categoryPanel.groupId}
            category={categoryPanel.category}
            onClose={() => setCategoryPanel(null)}
          />
        )}
      </SlideOverPanel>
    </div>
  );
}
```

- [ ] **Step 3: Add `/categories` to `frontend/src/App.tsx`**

Add the import at the top with other page imports:
```tsx
import CategoriesPage from "./pages/Categories";
```

Add the route inside `<Routes>`:
```tsx
<Route path="/categories" element={<CategoriesPage />} />
```

- [ ] **Step 4: Add `/categories` link to `frontend/src/components/NavBar.tsx`**

In the `links` array, add after the rules entry:
```tsx
{ to: "/categories", label: t("nav.categories") },
```

- [ ] **Step 5: Add i18n keys to `frontend/public/locales/en/translation.json`**

In the `"nav"` object, add:
```json
"categories": "Categories"
```

Add a new top-level `"categories"` object:
```json
"categories": {
  "title": "Categories",
  "groupsTitle": "Groups",
  "categoriesTitle": "Categories",
  "newGroup": "New Group",
  "newCategory": "New Category",
  "editCategory": "Edit Category",
  "selectGroup": "Select a group to manage its categories.",
  "fieldName": "Name",
  "fieldColor": "Color",
  "fieldIsIncome": "Income category"
}
```

- [ ] **Step 6: Add i18n keys to `frontend/public/locales/cs/translation.json`**

In the `"nav"` object, add:
```json
"categories": "Kategorie"
```

Add a new top-level `"categories"` object:
```json
"categories": {
  "title": "Kategorie",
  "groupsTitle": "Skupiny",
  "categoriesTitle": "Kategorie",
  "newGroup": "Nová skupina",
  "newCategory": "Nová kategorie",
  "editCategory": "Upravit kategorii",
  "selectGroup": "Vyberte skupinu pro správu kategorií.",
  "fieldName": "Název",
  "fieldColor": "Barva",
  "fieldIsIncome": "Příjmová kategorie"
}
```

- [ ] **Step 7: Start dev server and verify**

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173/categories` — verify two-column layout, group create/edit/reorder, category create/edit/reorder, slide-over panel.

Open `http://localhost:5173/rules` — verify table has Match Value and Category columns, New Rule button opens panel, enable toggle works.

- [ ] **Step 8: Commit**

```bash
cd frontend && git add src/pages/Categories/ src/components/NavBar.tsx src/App.tsx public/locales/
git commit -m "feat: add categories management page with drag-to-reorder"
```
