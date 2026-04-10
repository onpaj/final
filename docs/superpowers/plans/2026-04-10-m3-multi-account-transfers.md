# M3 — Multi-Account + Transfer Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support multiple bank accounts from different banks; detect and flag inter-account transfers so they are excluded from analytics.

**Architecture:** `GenericCsvParser` uses a stored `column_mapping` JSONB field from `import_batches` — on first upload from a generic account the user maps columns via a wizard UI; `TransferMatcher` is a pure service that scans new transactions against all other accounts within a ±2-day, ±0.01 tolerance window.

**Tech Stack:** Same as M2. No new dependencies.

**Prerequisites:** M2 complete and passing.

---

## Task 1: GenericCsvParser

**Files:**
- Create: `backend/app/services/parsers/generic_csv.py`
- Modify: `backend/app/services/import_service.py`
- Create: `backend/tests/test_generic_csv_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_generic_csv_parser.py
from decimal import Decimal
from app.services.parsers.generic_csv import GenericCsvParser

MAPPING = {
    "date": "Datum",
    "amount": "Castka",
    "currency": "Mena",
    "counterparty_name": "Protistrany",
    "counterparty_account": None,
    "description": "Popis",
    "reference": None,
    "date_format": "%d.%m.%Y",
    "decimal_separator": ",",
    "thousands_separator": " ",
    "encoding": "utf-8",
    "separator": ";",
}

CSV_CONTENT = b"""Datum;Castka;Mena;Protistrany;Popis
15.01.2026;-1 250,00;CZK;ALBERT;Nakup
20.01.2026;50 000,00;CZK;Zamestnavatel;Vyplata
"""

def test_parse_returns_rows():
    rows = GenericCsvParser.parse(CSV_CONTENT, MAPPING)
    assert len(rows) == 2

def test_amounts_parsed():
    rows = GenericCsvParser.parse(CSV_CONTENT, MAPPING)
    assert rows[0].amount == Decimal("-1250.00")
    assert rows[1].amount == Decimal("50000.00")

def test_counterparty_name():
    rows = GenericCsvParser.parse(CSV_CONTENT, MAPPING)
    assert rows[0].counterparty_name == "ALBERT"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_generic_csv_parser.py -v
```

- [ ] **Step 3: Create app/services/parsers/generic_csv.py**

```python
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from app.services.parsers.base import TransactionRow

class GenericCsvParser:
    @classmethod
    def parse(cls, file_bytes: bytes, mapping: dict) -> list[TransactionRow]:
        encoding = mapping.get("encoding", "utf-8")
        separator = mapping.get("separator", ",")
        date_fmt = mapping.get("date_format", "%Y-%m-%d")
        dec_sep = mapping.get("decimal_separator", ".")
        thou_sep = mapping.get("thousands_separator", "")

        text = file_bytes.decode(encoding)
        reader = csv.DictReader(io.StringIO(text), delimiter=separator)
        rows = []
        for raw in reader:
            date_str = raw.get(mapping["date"], "").strip()
            amount_str = raw.get(mapping["amount"], "").strip()
            if not date_str or not amount_str:
                continue
            # Normalize amount
            if thou_sep:
                amount_str = amount_str.replace(thou_sep, "")
            if dec_sep != ".":
                amount_str = amount_str.replace(dec_sep, ".")
            try:
                amount = Decimal(amount_str)
                booking_date = datetime.strptime(date_str, date_fmt).date()
            except (InvalidOperation, ValueError):
                continue

            def col(key):
                col_name = mapping.get(key)
                return raw.get(col_name, "").strip() or None if col_name else None

            rows.append(TransactionRow(
                booking_date=booking_date,
                value_date=None,
                amount=amount,
                currency=col("currency") or "CZK",
                counterparty_name=col("counterparty_name"),
                counterparty_account=col("counterparty_account"),
                description=col("description"),
                raw_reference=col("reference"),
            ))
        return rows
```

- [ ] **Step 4: Register GenericCsvParser in ImportService**

In `backend/app/services/import_service.py`:

```python
from app.services.parsers.generic_csv import GenericCsvParser

# In import_file(), update parser selection:
if account.bank == "partners":
    rows = PartnersParser.parse(file_bytes)
else:
    column_mapping = kwargs.get("column_mapping")
    if not column_mapping:
        raise ValueError("column_mapping required for generic CSV accounts")
    rows = GenericCsvParser.parse(file_bytes, column_mapping)
```

Update `import_file` signature to accept `column_mapping: dict | None = None`.

Also update the upload endpoint to accept and pass column_mapping from the request.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_generic_csv_parser.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/parsers/generic_csv.py backend/app/services/import_service.py backend/tests/test_generic_csv_parser.py
git commit -m "feat(m3): GenericCsvParser with configurable column mapping"
```

---

## Task 2: TransferMatcher

**Files:**
- Create: `backend/app/services/transfer_matcher.py`
- Modify: `backend/app/services/import_service.py`
- Create: `backend/tests/test_transfer_matcher.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_transfer_matcher.py
import pytest
import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.transfer_matcher import TransferMatcher

def make_tx(amount, booking_date, account_id=None, tx_id=None, is_transfer=False):
    tx = MagicMock()
    tx.id = tx_id or uuid.uuid4()
    tx.amount = Decimal(str(amount))
    tx.booking_date = booking_date
    tx.account_id = account_id or uuid.uuid4()
    tx.is_transfer = is_transfer
    tx.transfer_pair_id = None
    tx.category_id = None
    return tx

async def test_matching_debit_credit_pair():
    acct_a = uuid.uuid4()
    acct_b = uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a)
    credit = make_tx(5000, date(2026, 1, 16), acct_b)  # within 2 days

    mock_db = AsyncMock()

    async def fake_execute(q):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [credit]
        return mock_result

    mock_db.execute = fake_execute

    matcher = TransferMatcher(mock_db)
    pairs = await matcher._find_match(debit)
    assert pairs is not None
    assert pairs.id == credit.id

async def test_no_match_different_amount():
    acct_a = uuid.uuid4()
    acct_b = uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a)
    credit = make_tx(4000, date(2026, 1, 15), acct_b)

    mock_db = AsyncMock()
    async def fake_execute(q):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        return mock_result
    mock_db.execute = fake_execute

    matcher = TransferMatcher(mock_db)
    result = await matcher._find_match(debit)
    assert result is None
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_transfer_matcher.py -v
```

- [ ] **Step 3: Create app/services/transfer_matcher.py**

```python
import uuid
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Category, Transaction

AMOUNT_TOLERANCE = Decimal("0.01")
DATE_TOLERANCE_DAYS = 2

class TransferMatcher:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._internal_transfer_category_id: uuid.UUID | None = None

    async def _get_internal_transfer_category(self) -> uuid.UUID | None:
        if self._internal_transfer_category_id:
            return self._internal_transfer_category_id
        result = await self._db.execute(
            select(Category).where(Category.name == "Internal Transfer", Category.is_system == True)
        )
        cat = result.scalar_one_or_none()
        if cat:
            self._internal_transfer_category_id = cat.id
        return self._internal_transfer_category_id

    async def _find_match(self, debit: Transaction) -> Transaction | None:
        debit_abs = abs(debit.amount)
        date_min = debit.booking_date - timedelta(days=DATE_TOLERANCE_DAYS)
        date_max = debit.booking_date + timedelta(days=DATE_TOLERANCE_DAYS)
        result = await self._db.execute(
            select(Transaction).where(
                and_(
                    Transaction.account_id != debit.account_id,
                    Transaction.amount >= debit_abs - AMOUNT_TOLERANCE,
                    Transaction.amount <= debit_abs + AMOUNT_TOLERANCE,
                    Transaction.booking_date >= date_min,
                    Transaction.booking_date <= date_max,
                    Transaction.is_transfer == False,
                )
            )
        )
        candidates = result.scalars().all()
        return candidates[0] if candidates else None

    async def match_batch(self, transaction_ids: list[uuid.UUID]) -> int:
        result = await self._db.execute(
            select(Transaction).where(
                Transaction.id.in_(transaction_ids),
                Transaction.amount < 0,
                Transaction.is_transfer == False,
            )
        )
        debits = result.scalars().all()

        internal_cat_id = await self._get_internal_transfer_category()
        matched = 0
        for debit in debits:
            credit = await self._find_match(debit)
            if credit:
                pair_id = uuid.uuid4()
                debit.is_transfer = True
                debit.transfer_pair_id = pair_id
                debit.category_id = internal_cat_id
                credit.is_transfer = True
                credit.transfer_pair_id = pair_id
                credit.category_id = internal_cat_id
                matched += 1

        await self._db.commit()
        return matched
```

- [ ] **Step 4: Wire TransferMatcher into ImportService**

In `backend/app/services/import_service.py`, after CategorizationService call:

```python
from app.services.transfer_matcher import TransferMatcher

transfer_matcher = TransferMatcher(db)
transfers_detected = await transfer_matcher.match_batch(new_ids)
```

Update `ImportResult` to include `transfers_detected: int`.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_transfer_matcher.py -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/transfer_matcher.py backend/app/services/import_service.py backend/tests/test_transfer_matcher.py
git commit -m "feat(m3): TransferMatcher — cross-account pair detection within ±2 days"
```

---

## Task 3: Accounts Management UI + Column Mapper

**Files:**
- Create: `frontend/src/pages/Settings/index.tsx`
- Create: `frontend/src/pages/Settings/AccountsSection.tsx`
- Create: `frontend/src/pages/Settings/AccountForm.tsx`
- Modify: `frontend/src/pages/Imports/UploadForm.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create Settings/AccountForm.tsx**

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import client from "../../api/client";

interface Props { onClose: () => void; }

export default function AccountForm({ onClose }: Props) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [bank, setBank] = useState("partners");

  const mutation = useMutation({
    mutationFn: () => client.post("/api/accounts", { name, bank, currency: "CZK" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["accounts"] }); onClose(); },
  });

  return (
    <div className="flex flex-col gap-3 p-4 bg-gray-50 border border-gray-200 rounded-lg">
      <input
        className="border border-gray-300 rounded px-3 py-2 text-sm"
        placeholder="Account name (e.g. Partners – Checking)"
        value={name} onChange={(e) => setName(e.target.value)}
      />
      <select
        className="border border-gray-300 rounded px-3 py-2 text-sm"
        value={bank} onChange={(e) => setBank(e.target.value)}
      >
        <option value="partners">Partners Bank</option>
        <option value="generic">Other bank (generic CSV)</option>
      </select>
      <div className="flex gap-2">
        <button
          className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm disabled:opacity-50"
          disabled={!name || mutation.isPending}
          onClick={() => mutation.mutate()}
        >Add Account</button>
        <button className="text-gray-500 text-sm px-4" onClick={onClose}>Cancel</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create Settings/AccountsSection.tsx**

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listAccounts } from "../../api/accounts";
import client from "../../api/client";
import AccountForm from "./AccountForm";

export default function AccountsSection() {
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });

  const deactivate = useMutation({
    mutationFn: (id: string) => client.delete(`/api/accounts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Accounts</h2>
        <button
          className="bg-blue-600 text-white text-sm px-3 py-1.5 rounded"
          onClick={() => setAdding(true)}
        >+ Add Account</button>
      </div>
      {adding && <AccountForm onClose={() => setAdding(false)} />}
      <div className="mt-4 space-y-2">
        {accounts.map((a) => (
          <div key={a.id} className="flex items-center justify-between bg-white border border-gray-200 rounded px-4 py-3">
            <div>
              <span className="font-medium text-sm">{a.name}</span>
              <span className="ml-2 text-xs text-gray-400">{a.bank} · {a.currency}</span>
            </div>
            <button
              className="text-red-400 text-xs hover:underline"
              onClick={() => deactivate.mutate(a.id)}
            >Remove</button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create Settings/index.tsx**

```tsx
import AccountsSection from "./AccountsSection";

export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <AccountsSection />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Add Settings route to App.tsx**

```tsx
import SettingsPage from "./pages/Settings";
// Inside <Routes>:
<Route path="/settings" element={<SettingsPage />} />
```

- [ ] **Step 5: Update UploadForm to show column mapper for generic accounts**

In `frontend/src/pages/Imports/UploadForm.tsx`, after account selection detect if account is generic and show a minimal column mapping UI before uploading. For M3, a simplified inline mapper is acceptable — the full wizard can be added in M5.

Add state:
```tsx
const [columnMapping, setColumnMapping] = useState<Record<string, string> | null>(null);
const selectedAccount = accounts.find((a) => a.id === accountId);
const needsMapping = selectedAccount?.bank === "generic" && !columnMapping;
```

Show a simple mapping form when `needsMapping` is true (ask user to enter column names for date, amount, counterparty, description, and CSV settings like separator and date format).

Pass `column_mapping` as a JSON form field alongside the file upload.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Settings/ frontend/src/pages/Imports/ frontend/src/App.tsx
git commit -m "feat(m3): accounts management UI, settings page, generic CSV column mapper"
```

---

## M3 Acceptance Criteria Verification

- [ ] Import a non-Partners CSV via the generic mapper → transactions imported and classified
- [ ] Import from two accounts where a known transfer exists → both rows marked `is_transfer=true`, linked via `transfer_pair_id`
- [ ] Analytics totals exclude the transfer amount (verify manually: sum of non-transfer amounts matches expected)
- [ ] Settings page shows account list, add account, remove account
- [ ] Second import from a generic account reuses stored column mapping without showing the wizard again
