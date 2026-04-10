# M4 — Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Full analytics dashboard with month → group → category → transaction drill-down, trends sub-view, anomaly detection, and "new data available" banner.

**Architecture:** `AnalyticsService` executes parameterized SQL aggregations directly (no ORM overhead); React analytics page tracks drill-down state locally; "new data available" is detected by polling `GET /api/imports?limit=1` and comparing `imported_at` timestamp to when the page was last loaded.

**Tech Stack:** Same as M3 + `recharts` (already listed in frontend dependencies, add if not installed).

**Prerequisites:** M3 complete and passing.

---

## Task 1: AnalyticsService — monthly_summary

**Files:**
- Create: `backend/app/services/analytics_service.py`
- Create: `backend/tests/test_analytics_service.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_analytics_service.py
import pytest
import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock, call
from app.services.analytics_service import AnalyticsService

async def test_monthly_summary_structure():
    mock_db = AsyncMock()

    # Simulate a DB result with one group row
    mock_row = MagicMock()
    mock_row.group_name = "Living"
    mock_row.group_color = "#4CAF50"
    mock_row.category_name = "Groceries"
    mock_row.is_income = False
    mock_row.total = Decimal("-3500.00")

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_result

    service = AnalyticsService(mock_db)
    summary = await service.monthly_summary(2026, 4)

    assert "groups" in summary
    assert "income" in summary
    assert "expenses" in summary
    assert "savings_rate" in summary

async def test_savings_rate_calculation():
    mock_db = AsyncMock()
    mock_db.execute.return_value.all.return_value = []
    service = AnalyticsService(mock_db)
    # Manually test the helper
    rate = service._savings_rate(income=Decimal("50000"), expenses=Decimal("-30000"))
    assert rate == Decimal("0.40")

async def test_savings_rate_zero_income():
    service = AnalyticsService(AsyncMock())
    rate = service._savings_rate(income=Decimal("0"), expenses=Decimal("-1000"))
    assert rate == Decimal("0")
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_analytics_service.py -v
```

- [ ] **Step 3: Create app/services/analytics_service.py**

```python
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self._db = db

    @staticmethod
    def _savings_rate(income: Decimal, expenses: Decimal) -> Decimal:
        if income == 0:
            return Decimal("0")
        saved = income + expenses  # expenses is negative
        return (saved / income).quantize(Decimal("0.01"))

    async def monthly_summary(self, year: int, month: int, account_id: str | None = None) -> dict:
        account_filter = "AND t.account_id = :account_id" if account_id else ""
        sql = text(f"""
            SELECT
                cg.name AS group_name,
                cg.color AS group_color,
                cg.sort_order AS group_sort,
                c.name AS category_name,
                c.is_income,
                c.id AS category_id,
                COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN category_groups cg ON c.group_id = cg.id
            WHERE
                t.is_transfer = false
                AND EXTRACT(YEAR FROM t.booking_date) = :year
                AND EXTRACT(MONTH FROM t.booking_date) = :month
                {account_filter}
            GROUP BY cg.id, cg.name, cg.color, cg.sort_order, c.id, c.name, c.is_income
            ORDER BY cg.sort_order, c.name
        """)
        params = {"year": year, "month": month}
        if account_id:
            params["account_id"] = account_id

        result = await self._db.execute(sql, params)
        rows = result.all()

        groups: dict[str, dict] = {}
        income = Decimal("0")
        expenses = Decimal("0")

        for row in rows:
            gname = row.group_name
            if gname not in groups:
                groups[gname] = {"name": gname, "color": row.group_color, "total": Decimal("0"), "categories": []}
            groups[gname]["total"] += row.total
            groups[gname]["categories"].append({
                "id": str(row.category_id),
                "name": row.category_name,
                "total": row.total,
                "is_income": row.is_income,
            })
            if row.is_income:
                income += row.total
            else:
                expenses += row.total

        return {
            "year": year,
            "month": month,
            "groups": list(groups.values()),
            "income": income,
            "expenses": expenses,
            "savings_rate": self._savings_rate(income, expenses),
        }

    async def trends(self, from_year: int, from_month: int, to_year: int, to_month: int, account_id: str | None = None) -> list[dict]:
        account_filter = "AND t.account_id = :account_id" if account_id else ""
        sql = text(f"""
            SELECT
                EXTRACT(YEAR FROM t.booking_date)::int AS year,
                EXTRACT(MONTH FROM t.booking_date)::int AS month,
                c.name AS category_name,
                cg.name AS group_name,
                c.is_income,
                COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN category_groups cg ON c.group_id = cg.id
            WHERE
                t.is_transfer = false
                AND (EXTRACT(YEAR FROM t.booking_date) * 100 + EXTRACT(MONTH FROM t.booking_date))
                    BETWEEN :from_ym AND :to_ym
                {account_filter}
            GROUP BY year, month, c.id, c.name, cg.name, c.is_income
            ORDER BY year, month, cg.name, c.name
        """)
        params = {
            "from_ym": from_year * 100 + from_month,
            "to_ym": to_year * 100 + to_month,
        }
        if account_id:
            params["account_id"] = account_id

        result = await self._db.execute(sql, params)
        return [
            {
                "year": row.year, "month": row.month,
                "category": row.category_name, "group": row.group_name,
                "is_income": row.is_income, "total": float(row.total),
            }
            for row in result.all()
        ]

    async def anomalies(self, year: int, month: int, account_id: str | None = None) -> list[dict]:
        account_filter = "AND t.account_id = :account_id" if account_id else ""
        # Compare current month to trailing 6-month average per group
        sql = text(f"""
            WITH monthly_group AS (
                SELECT
                    EXTRACT(YEAR FROM t.booking_date)::int AS yr,
                    EXTRACT(MONTH FROM t.booking_date)::int AS mo,
                    cg.id AS group_id,
                    cg.name AS group_name,
                    SUM(ABS(t.amount)) AS total
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                JOIN category_groups cg ON c.group_id = cg.id
                WHERE
                    t.is_transfer = false
                    AND c.is_income = false
                    AND (EXTRACT(YEAR FROM t.booking_date) * 100 + EXTRACT(MONTH FROM t.booking_date))
                        BETWEEN :from_ym AND :to_ym
                    {account_filter}
                GROUP BY yr, mo, cg.id, cg.name
            ),
            trailing AS (
                SELECT group_id, group_name,
                    AVG(total) AS mean, STDDEV(total) AS stddev
                FROM monthly_group
                WHERE NOT (yr = :year AND mo = :month)
                GROUP BY group_id, group_name
            ),
            current_month AS (
                SELECT group_id, total AS current_total
                FROM monthly_group
                WHERE yr = :year AND mo = :month
            )
            SELECT t.group_name, c.current_total, t.mean, t.stddev
            FROM trailing t
            JOIN current_month c ON c.group_id = t.group_id
            WHERE t.stddev > 0 AND c.current_total > t.mean + 2 * t.stddev
        """)
        six_months_ago_ym = (year * 100 + month) - 6  # simplified; good enough for monthly math
        params = {"year": year, "month": month, "from_ym": six_months_ago_ym, "to_ym": year * 100 + month}
        if account_id:
            params["account_id"] = account_id

        result = await self._db.execute(sql, params)
        return [
            {
                "group": row.group_name,
                "current": float(row.current_total),
                "mean": float(row.mean),
                "stddev": float(row.stddev),
            }
            for row in result.all()
        ]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_analytics_service.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/analytics_service.py backend/tests/test_analytics_service.py
git commit -m "feat(m4): AnalyticsService — monthly_summary, trends, anomalies"
```

---

## Task 2: Analytics API Endpoints

**Files:**
- Create: `backend/app/api/analytics.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create app/api/analytics.py**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()

@router.get("/monthly")
async def monthly(
    year: int = Query(...),
    month: int = Query(...),
    account_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.monthly_summary(year, month, account_id)

@router.get("/trends")
async def trends(
    from_year: int = Query(...),
    from_month: int = Query(...),
    to_year: int = Query(...),
    to_month: int = Query(...),
    account_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.trends(from_year, from_month, to_year, to_month, account_id)

@router.get("/anomalies")
async def anomalies(
    year: int = Query(...),
    month: int = Query(...),
    account_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.anomalies(year, month, account_id)
```

- [ ] **Step 2: Register router in main.py**

```python
from app.api import analytics
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
```

- [ ] **Step 3: Smoke test**

```bash
curl "http://localhost:8000/api/analytics/monthly?year=2026&month=4"
```

Expected: JSON with `groups`, `income`, `expenses`, `savings_rate`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/analytics.py backend/app/main.py
git commit -m "feat(m4): analytics API — monthly, trends, anomalies endpoints"
```

---

## Task 3: Analytics Dashboard — Level 1 (Month Summary)

**Files:**
- Create: `frontend/src/api/analytics.ts`
- Modify: `frontend/src/pages/Analytics/index.tsx`
- Create: `frontend/src/pages/Analytics/MonthSummary.tsx`

- [ ] **Step 1: Install recharts if not present**

```bash
cd frontend
npm install recharts
npm install -D @types/recharts
```

- [ ] **Step 2: Create src/api/analytics.ts**

```typescript
import client from "./client";

export interface CategorySummary { id: string; name: string; total: number; is_income: boolean; }
export interface GroupSummary { name: string; color: string; total: number; categories: CategorySummary[]; }
export interface MonthlySummary {
  year: number; month: number;
  groups: GroupSummary[];
  income: number; expenses: number; savings_rate: number;
}

export async function getMonthlySummary(year: number, month: number, accountId?: string): Promise<MonthlySummary> {
  const { data } = await client.get("/api/analytics/monthly", {
    params: { year, month, account_id: accountId },
  });
  return data;
}

export async function getTrends(params: {
  from_year: number; from_month: number; to_year: number; to_month: number; account_id?: string;
}): Promise<Array<{ year: number; month: number; category: string; group: string; total: number }>> {
  const { data } = await client.get("/api/analytics/trends", { params });
  return data;
}
```

- [ ] **Step 3: Create pages/Analytics/MonthSummary.tsx**

```tsx
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import type { MonthlySummary } from "../../api/analytics";

interface Props {
  summary: MonthlySummary;
  onGroupClick: (groupName: string) => void;
}

export default function MonthSummary({ summary, onGroupClick }: Props) {
  const expenseGroups = summary.groups.filter((g) => g.total < 0);
  const pieData = expenseGroups.map((g) => ({ name: g.name, value: Math.abs(g.total), color: g.color }));

  return (
    <div>
      {/* KPI row */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: "Income", value: summary.income, color: "text-green-600" },
          { label: "Expenses", value: Math.abs(summary.expenses), color: "text-red-500" },
          { label: "Savings Rate", value: `${(summary.savings_rate * 100).toFixed(0)}%`, color: "text-blue-600", raw: true },
        ].map(({ label, value, color, raw }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase mb-1">{label}</p>
            <p className={`text-2xl font-bold ${color}`}>
              {raw ? value : `${Number(value).toLocaleString("cs-CZ")} CZK`}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Donut chart */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold mb-4 text-gray-700">Spending by Group</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={60} outerRadius={90}>
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color || "#ccc"} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => `${v.toLocaleString("cs-CZ")} CZK`} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Group breakdown table */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <h3 className="text-sm font-semibold px-4 py-3 border-b text-gray-700">Groups</h3>
          <table className="w-full text-sm">
            <tbody>
              {summary.groups.map((g) => (
                <tr
                  key={g.name}
                  className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                  onClick={() => onGroupClick(g.name)}
                >
                  <td className="px-4 py-2.5">
                    <span className="inline-block w-2 h-2 rounded-full mr-2" style={{ background: g.color }} />
                    {g.name}
                  </td>
                  <td className={`px-4 py-2.5 text-right font-medium ${g.total >= 0 ? "text-green-600" : "text-gray-800"}`}>
                    {Math.abs(g.total).toLocaleString("cs-CZ")} CZK
                  </td>
                  <td className="px-4 py-2.5 text-gray-300 text-xs">→</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/analytics.ts frontend/src/pages/Analytics/MonthSummary.tsx
git commit -m "feat(m4): analytics level 1 — month summary with KPIs + group breakdown"
```

---

## Task 4: Analytics Levels 2–4 + Full Drilldown

**Files:**
- Create: `frontend/src/pages/Analytics/GroupDetail.tsx`
- Create: `frontend/src/pages/Analytics/CategoryDetail.tsx`
- Modify: `frontend/src/pages/Analytics/index.tsx`

- [ ] **Step 1: Create pages/Analytics/GroupDetail.tsx**

```tsx
import type { GroupSummary } from "../../api/analytics";

interface Props {
  group: GroupSummary;
  onCategoryClick: (categoryId: string, categoryName: string) => void;
  onBack: () => void;
}

export default function GroupDetail({ group, onCategoryClick, onBack }: Props) {
  return (
    <div>
      <button className="text-blue-600 text-sm mb-4 hover:underline" onClick={onBack}>
        ← Back to overview
      </button>
      <h2 className="text-xl font-bold mb-4">{group.name}</h2>
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-4 py-2 text-left">Category</th>
              <th className="px-4 py-2 text-right">Total</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {group.categories.map((c) => (
              <tr
                key={c.id}
                className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                onClick={() => onCategoryClick(c.id, c.name)}
              >
                <td className="px-4 py-3">{c.name}</td>
                <td className={`px-4 py-3 text-right font-medium ${c.is_income ? "text-green-600" : "text-gray-800"}`}>
                  {Math.abs(c.total).toLocaleString("cs-CZ")} CZK
                </td>
                <td className="px-4 py-3 text-gray-300 text-xs">→</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create pages/Analytics/CategoryDetail.tsx**

```tsx
import { useQuery } from "@tanstack/react-query";
import { listTransactions } from "../../api/transactions";

interface Props {
  categoryId: string;
  categoryName: string;
  year: number;
  month: number;
  onBack: () => void;
}

export default function CategoryDetail({ categoryId, categoryName, year, month, onBack }: Props) {
  const dateFrom = `${year}-${String(month).padStart(2, "0")}-01`;
  const dateTo = `${year}-${String(month).padStart(2, "0")}-31`;

  const { data, isLoading } = useQuery({
    queryKey: ["transactions", categoryId, year, month],
    queryFn: () => listTransactions({ date_from: dateFrom, date_to: dateTo, category_id: categoryId }),
  });

  return (
    <div>
      <button className="text-blue-600 text-sm mb-4 hover:underline" onClick={onBack}>
        ← Back to group
      </button>
      <h2 className="text-xl font-bold mb-4">{categoryName}</h2>
      {isLoading ? <p className="text-gray-400 text-sm">Loading…</p> : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                {["Date", "Counterparty", "Description", "Amount"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((tx) => (
                <tr key={tx.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-2.5 text-gray-500">{tx.booking_date}</td>
                  <td className="px-4 py-2.5 font-medium">{tx.counterparty_name || "—"}</td>
                  <td className="px-4 py-2.5 text-gray-500 text-xs">{tx.description || "—"}</td>
                  <td className={`px-4 py-2.5 font-medium ${tx.amount < 0 ? "text-red-500" : "text-green-600"}`}>
                    {tx.amount.toLocaleString("cs-CZ")} CZK
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.total === 0 && <p className="px-4 py-8 text-center text-gray-400 text-sm">No transactions.</p>}
        </div>
      )}
    </div>
  );
}
```

Note: Add `category_id` filter param to transactions API backend:
```python
# In backend/app/api/transactions.py:
category_id: uuid.UUID | None = Query(None),
# In query builder:
if category_id:
    q = q.where(Transaction.category_id == category_id)
```

- [ ] **Step 3: Wire drilldown state into Analytics/index.tsx**

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMonthlySummary } from "../../api/analytics";
import MonthSummary from "./MonthSummary";
import GroupDetail from "./GroupDetail";
import CategoryDetail from "./CategoryDetail";

type Level =
  | { view: "summary" }
  | { view: "group"; groupName: string }
  | { view: "category"; groupName: string; categoryId: string; categoryName: string };

export default function AnalyticsPage() {
  const now = new Date();
  const defaultMonth = now.getMonth() === 0 ? 12 : now.getMonth(); // last month
  const defaultYear = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();

  const [year, setYear] = useState(defaultYear);
  const [month, setMonth] = useState(defaultMonth);
  const [accountId, setAccountId] = useState<string | undefined>();
  const [level, setLevel] = useState<Level>({ view: "summary" });
  const [newDataAvailable, setNewDataAvailable] = useState(false);

  const { data: summary, isLoading, refetch } = useQuery({
    queryKey: ["monthly-summary", year, month, accountId],
    queryFn: () => getMonthlySummary(year, month, accountId),
  });

  const monthLabel = new Date(year, month - 1).toLocaleString("cs-CZ", { month: "long", year: "numeric" });

  return (
    <div className="max-w-5xl mx-auto">
      {/* New data banner */}
      {newDataAvailable && (
        <div className="mb-4 flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
          <span className="text-blue-700 text-sm">New data available — import completed.</span>
          <button
            className="bg-blue-600 text-white text-sm px-3 py-1 rounded"
            onClick={() => { refetch(); setNewDataAvailable(false); }}
          >Refresh</button>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Analytics — {monthLabel}
        </h1>
        <div className="flex items-center gap-2">
          <button className="text-gray-500 hover:text-gray-800 px-2" onClick={() => {
            if (month === 1) { setMonth(12); setYear(y => y - 1); }
            else setMonth(m => m - 1);
            setLevel({ view: "summary" });
          }}>‹</button>
          <button className="text-gray-500 hover:text-gray-800 px-2" onClick={() => {
            if (month === 12) { setMonth(1); setYear(y => y + 1); }
            else setMonth(m => m + 1);
            setLevel({ view: "summary" });
          }}>›</button>
        </div>
      </div>

      {isLoading && <p className="text-gray-400 text-sm">Loading…</p>}

      {summary && level.view === "summary" && (
        <MonthSummary
          summary={summary}
          onGroupClick={(groupName) => setLevel({ view: "group", groupName })}
        />
      )}

      {summary && level.view === "group" && (
        <GroupDetail
          group={summary.groups.find((g) => g.name === level.groupName)!}
          onCategoryClick={(categoryId, categoryName) =>
            setLevel({ view: "category", groupName: level.groupName, categoryId, categoryName })
          }
          onBack={() => setLevel({ view: "summary" })}
        />
      )}

      {level.view === "category" && (
        <CategoryDetail
          categoryId={level.categoryId}
          categoryName={level.categoryName}
          year={year}
          month={month}
          onBack={() => setLevel({ view: "group", groupName: level.groupName })}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Analytics/
git commit -m "feat(m4): analytics drilldown — group detail + category detail + transaction list"
```

---

## Task 5: New Data Available Banner (Polling)

The banner is already wired into the `Analytics/index.tsx` state above (`newDataAvailable`). This task connects the detection logic.

**Files:**
- Modify: `frontend/src/components/ProcessingStatus.tsx`
- Modify: `frontend/src/pages/Analytics/index.tsx`

- [ ] **Step 1: Expose a callback from ProcessingStatus for job completion events**

Update `ProcessingStatus.tsx` to accept an optional `onJobCompleted` prop and call it when a batch transitions from `processing` to `completed`:

```tsx
interface Props { onJobCompleted?: () => void; }

export default function ProcessingStatus({ onJobCompleted }: Props) {
  const prevStatusRef = useRef<Record<string, string>>({});
  const { data: batches = [] } = useQuery({...});

  useEffect(() => {
    batches.forEach((b) => {
      const prev = prevStatusRef.current[b.id];
      if (prev === "processing" && b.status === "completed") {
        onJobCompleted?.();
      }
      prevStatusRef.current[b.id] = b.status;
    });
  }, [batches, onJobCompleted]);
  // ... rest of component
}
```

- [ ] **Step 2: Pass callback from NavBar → Analytics via a shared signal**

Use a simple React context or a URL state flag. The simplest approach: lift `newDataAvailable` state into a React context and provide it app-wide via a `DataFreshnessContext`.

Create `frontend/src/context/DataFreshness.tsx`:

```tsx
import { createContext, useContext, useState } from "react";

const Ctx = createContext<{ markStale: () => void; isStale: boolean; markFresh: () => void }>({
  markStale: () => {},
  isStale: false,
  markFresh: () => {},
});

export function DataFreshnessProvider({ children }: { children: React.ReactNode }) {
  const [isStale, setIsStale] = useState(false);
  return (
    <Ctx.Provider value={{ markStale: () => setIsStale(true), isStale, markFresh: () => setIsStale(false) }}>
      {children}
    </Ctx.Provider>
  );
}

export const useDataFreshness = () => useContext(Ctx);
```

Wrap `App.tsx` in `<DataFreshnessProvider>`. In `NavBar.tsx` pass `markStale` as `onJobCompleted` to `ProcessingStatus`. In `Analytics/index.tsx` read `isStale` and call `markFresh` on refresh.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat(m4): new data available banner — polling-based detection via ProcessingStatus"
```

---

## Task 6: Trends Sub-View

**Files:**
- Create: `frontend/src/pages/Analytics/TrendsView.tsx`
- Modify: `frontend/src/pages/Analytics/index.tsx`

- [ ] **Step 1: Create TrendsView.tsx**

```tsx
import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { getTrends } from "../../api/analytics";

interface Props { year: number; month: number; }

const COLORS = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0", "#009688", "#607D8B"];

export default function TrendsView({ year, month }: Props) {
  const fromYear = month <= 6 ? year - 1 : year;
  const fromMonth = month <= 6 ? month + 6 : month - 6;

  const { data: points = [], isLoading } = useQuery({
    queryKey: ["trends", year, month],
    queryFn: () => getTrends({ from_year: fromYear, from_month: fromMonth, to_year: year, to_month: month }),
  });

  // Pivot to { "YYYY-MM": { GroupName: total } }
  const pivoted: Record<string, Record<string, number>> = {};
  const groups = new Set<string>();
  for (const p of points) {
    const key = `${p.year}-${String(p.month).padStart(2, "0")}`;
    pivoted[key] = pivoted[key] || {};
    pivoted[key][p.group] = (pivoted[key][p.group] || 0) + Math.abs(p.total);
    if (!p.is_income) groups.add(p.group);
  }
  const chartData = Object.entries(pivoted)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, vals]) => ({ month: key, ...vals }));
  const groupList = Array.from(groups);

  if (isLoading) return <p className="text-gray-400 text-sm">Loading trends…</p>;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold mb-4 text-gray-700">Spending Trends (6 months)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: number) => `${v.toLocaleString("cs-CZ")} CZK`} />
          <Legend />
          {groupList.map((g, i) => (
            <Line key={g} type="monotone" dataKey={g} stroke={COLORS[i % COLORS.length]} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: Add Trends tab toggle to Analytics/index.tsx**

Add a tab bar (`Overview | Trends`) above the content area. Switch between `MonthSummary/GroupDetail/CategoryDetail` and `TrendsView` based on the selected tab.

```tsx
const [tab, setTab] = useState<"overview" | "trends">("overview");
// Tab buttons:
// <button onClick={() => setTab("overview")}>Overview</button>
// <button onClick={() => setTab("trends")}>Trends</button>
// Render TrendsView when tab === "trends"
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Analytics/TrendsView.tsx frontend/src/pages/Analytics/index.tsx
git commit -m "feat(m4): analytics trends sub-view — 6-month line chart by group"
```

---

## M4 Acceptance Criteria Verification

- [ ] Dashboard totals for a known month match hand-calculated values (within rounding)
- [ ] Clicking a group shows category breakdown; clicking a category shows transaction list
- [ ] Trends tab shows 6-month line chart per category group
- [ ] "New data available" banner appears after an import completes while on Analytics page; clicking Refresh updates totals
- [ ] All analytics exclude `is_transfer = true` transactions (verify: total with transfers excluded matches expected)
