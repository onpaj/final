# AirBank PDF Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AirBank PDF statement parser and wire it into the import pipeline alongside the existing Partners Bank CSV parser.

**Architecture:** A new `AirBankPdfParser` class follows the existing parser pattern (`parse(file_bytes) -> list[TransactionRow]`). It uses `pdfplumber` to extract the statement table row-by-row. Row parsing is isolated in `_parse_row()` for direct testability. `import_service.py` gets an `"airbank"` branch alongside the existing `"partners"` branch.

**Tech Stack:** `pdfplumber>=0.11.0` (PDF table extraction), `pytest` (unit + integration tests)

---

### Task 1: Switch local dev config to `.env.test`

**Files:**
- Modify: `backend/app/config.py:13-16`

- [ ] **Step 1: Update `env_file` in `config.py`**

Replace lines 13–16:

```python
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
    )
```

- [ ] **Step 2: Verify the app still starts (reads from `.env.test`)**

```bash
cd backend && .venv/bin/uvicorn app.main:app --port 8300
```

Expected: App starts without errors, no `ValidationError` for missing env vars.

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "config: use .env.test for local development"
```

---

### Task 2: Add `pdfplumber` dependency

**Files:**
- Modify: `backend/pyproject.toml:9-20`

- [ ] **Step 1: Add `pdfplumber` to `[project] dependencies`**

The full updated `dependencies` list:

```toml
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.13.0",
    "asyncpg>=0.29.0",
    "pydantic-settings>=2.4.0",
    "python-multipart>=0.0.9",
    "anthropic>=0.28.0",
    "azure-storage-blob>=12.0.0",
    "azure-monitor-opentelemetry>=1.6.0",
    "pdfplumber>=0.11.0",
]
```

- [ ] **Step 2: Install**

```bash
cd backend && .venv/bin/pip install -e ".[test]"
```

Expected: `pdfplumber` and `pdfminer.six` install without errors.

- [ ] **Step 3: Probe AirBank PDF to confirm table column structure**

Run:

```bash
cd backend && .venv/bin/python - << 'EOF'
import pdfplumber, io

with open("../data/Attachment-1.pdf", "rb") as f:
    pdf_bytes = f.read()

with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
    for i, page in enumerate(pdf.pages):
        table = page.extract_table()
        print(f"=== PAGE {i+1} ({len(table) if table else 0} rows) ===")
        if table:
            for j, row in enumerate(table[:6]):
                print(f"  Row {j}: {row}")
EOF
```

Expected output (verify these column indices before proceeding to Task 3):
- Col 0: booking date (`"02.03.2026"`)
- Col 1: execution date (`"02.03.2026"`)
- Col 2: type (`"Trvalý příkaz"`)
- Col 3: transaction code (`"151641036232"`)
- Col 4: counterparty name (`"SOS vesničky"`)
- Col 5: account number (`"120777711 / 0300"`)
- Col 6: details/VS (`"VS140060\nSOS vesničky"`)
- Col 7: amount (`"-500,00"`)
- Col 8: fees (`"0,00"`)

**If the probe shows a different number of columns or different ordering, adjust the `_COL_*` constants in Task 4 accordingly — and update the test fixture data in Task 3 to match.**

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "deps: add pdfplumber for AirBank PDF parsing"
```

---

### Task 3: Write failing tests for `AirBankPdfParser`

**Files:**
- Create: `backend/tests/test_airbank_pdf_parser.py`

> Row fixture data below matches the expected 9-column pdfplumber output confirmed in Task 2 Step 3. If probe showed different structure, update the fixtures to match actual output before writing this file.

- [ ] **Step 1: Create test file**

```python
import pytest
from datetime import date
from decimal import Decimal

from app.services.parsers.airbank_pdf import AirBankPdfParser

# Raw rows as returned by pdfplumber (9 columns):
# [booking_date, execution_date, type, tx_code, name, account, details, amount_czk, fees]

STANDING_ORDER = [
    "02.03.2026", "02.03.2026", "Trvalý příkaz", "151641036232",
    "SOS vesničky", "120777711 / 0300", "VS140060\nSOS vesničky",
    "-500,00", "0,00",
]

INCOMING = [
    "02.03.2026", "02.03.2026", "Příchozí úhrada", "151663208902",
    "dům sinkulova 12", "5112785001 / 5500", "VS7653250275\nOsobní výběr Sinkulova 12",
    "3 000,00", "0,00",
]

OUTGOING_NO_NAME = [
    "06.03.2026", "06.03.2026", "Odchozí úhrada", "152172884502",
    None, "7757000901 / 6363", None,
    "-25 000,00", "0,00",
]

SIPO = [
    "11.03.2026", "11.03.2026", "Inkaso SIPO", "152579099922",
    "Air Bank", None, "SIPO\n1044362983",
    "-212,00", "0,00",
]

LARGE_AMOUNT = [
    "03.03.2026", "03.03.2026", "Příchozí úhrada", "151800655262",
    "Anela Cosmetics s.r.", "2103271662 / 2010", "VS7413769\n001 - Andrea Pajgrt Bartosova",
    "21 478,00", "0,00",
]


def test_standing_order_debit():
    row = AirBankPdfParser()._parse_row(STANDING_ORDER)
    assert row.booking_date == date(2026, 3, 2)
    assert row.value_date == date(2026, 3, 2)
    assert row.amount == Decimal("-500.00")
    assert row.currency == "CZK"
    assert row.counterparty_name == "SOS vesničky"
    assert row.counterparty_account == "120777711 / 0300"
    assert row.description == "VS140060\nSOS vesničky"
    assert row.raw_reference == "151641036232"


def test_incoming_payment_with_thousands_separator():
    row = AirBankPdfParser()._parse_row(INCOMING)
    assert row.booking_date == date(2026, 3, 2)
    assert row.value_date == date(2026, 3, 2)
    assert row.amount == Decimal("3000.00")
    assert row.currency == "CZK"
    assert row.counterparty_name == "dům sinkulova 12"
    assert row.counterparty_account == "5112785001 / 5500"
    assert row.description == "VS7653250275\nOsobní výběr Sinkulova 12"
    assert row.raw_reference == "151663208902"


def test_outgoing_no_counterparty_name():
    row = AirBankPdfParser()._parse_row(OUTGOING_NO_NAME)
    assert row.booking_date == date(2026, 3, 6)
    assert row.amount == Decimal("-25000.00")
    assert row.counterparty_name is None
    assert row.counterparty_account == "7757000901 / 6363"
    assert row.description == "Odchozí úhrada"  # falls back to type


def test_sipo_no_account():
    row = AirBankPdfParser()._parse_row(SIPO)
    assert row.booking_date == date(2026, 3, 11)
    assert row.amount == Decimal("-212.00")
    assert row.counterparty_name == "Air Bank"
    assert row.counterparty_account is None
    assert row.description == "SIPO\n1044362983"
    assert row.raw_reference == "152579099922"


def test_large_amount_with_spaces():
    row = AirBankPdfParser()._parse_row(LARGE_AMOUNT)
    assert row.amount == Decimal("21478.00")


def test_is_data_row_skips_header():
    parser = AirBankPdfParser()
    header = ["Zaúčtování", "Provedení", "Typ", "Kód transakce", "Název",
              "Číslo účtu / debetní karty", "Detaily", "Částka CZK", "Poplatky"]
    assert parser._is_data_row(header) is False


def test_is_data_row_skips_none_row():
    parser = AirBankPdfParser()
    assert parser._is_data_row([None] * 9) is False
    assert parser._is_data_row([]) is False


def test_is_data_row_accepts_transaction():
    parser = AirBankPdfParser()
    assert parser._is_data_row(STANDING_ORDER) is True


def test_integration_real_pdf():
    """Parse the real AirBank sample PDF and verify basic counts/values."""
    import io
    with open("../data/Attachment-1.pdf", "rb") as f:
        pdf_bytes = f.read()
    rows = AirBankPdfParser().parse(pdf_bytes)
    # Sample PDF has 15 transactions (verified by counting the statement)
    assert len(rows) == 15
    # All rows have a booking date and amount
    for row in rows:
        assert row.booking_date is not None
        assert row.amount != 0
        assert row.currency == "CZK"
    # First transaction: SOS vesničky -500
    first = rows[0]
    assert first.amount == Decimal("-500.00")
    assert first.counterparty_name == "SOS vesničky"
```

- [ ] **Step 2: Run tests to confirm they fail with ImportError**

```bash
cd backend && .venv/bin/pytest tests/test_airbank_pdf_parser.py -v 2>&1 | head -30
```

Expected: `ImportError: cannot import name 'AirBankPdfParser' from 'app.services.parsers.airbank_pdf'` (or `ModuleNotFoundError`).

---

### Task 4: Implement `AirBankPdfParser`

**Files:**
- Create: `backend/app/services/parsers/airbank_pdf.py`

- [ ] **Step 1: Create the parser**

```python
import io
import re
from datetime import date
from decimal import Decimal

import pdfplumber

from app.services.parsers.base import TransactionRow

# Column indices in pdfplumber table output.
# Verified against data/Attachment-1.pdf probe in Task 2 Step 3.
_COL_BOOKING = 0
_COL_EXECUTION = 1
_COL_TYPE = 2
_COL_TX_CODE = 3
_COL_NAME = 4
_COL_ACCOUNT = 5
_COL_DETAILS = 6
_COL_AMOUNT = 7

_DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


class AirBankPdfParser:

    def parse(self, file_bytes: bytes) -> list[TransactionRow]:
        raw_rows = self._extract_rows(file_bytes)
        return [self._parse_row(row) for row in raw_rows if self._is_data_row(row)]

    def _extract_rows(self, file_bytes: bytes) -> list[list[str | None]]:
        result = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    result.extend(table)
        return result

    def _is_data_row(self, row: list[str | None]) -> bool:
        if not row or len(row) <= _COL_AMOUNT:
            return False
        first = (row[_COL_BOOKING] or "").strip()
        return bool(_DATE_RE.match(first))

    def _parse_row(self, row: list[str | None]) -> TransactionRow:
        details = self._clean(row[_COL_DETAILS])
        return TransactionRow(
            booking_date=self._parse_date(row[_COL_BOOKING]),
            value_date=self._parse_date(row[_COL_EXECUTION]) if self._clean(row[_COL_EXECUTION]) else None,
            amount=self._parse_amount(row[_COL_AMOUNT]),
            currency="CZK",
            counterparty_name=self._clean(row[_COL_NAME]),
            counterparty_account=self._clean(row[_COL_ACCOUNT]),
            description=details or self._clean(row[_COL_TYPE]),
            raw_reference=self._clean(row[_COL_TX_CODE]),
        )

    @staticmethod
    def _parse_date(s: str | None) -> date:
        if not s:
            raise ValueError("Date field is empty")
        d, m, y = s.strip().split(".")
        return date(int(y), int(m), int(d))

    @staticmethod
    def _parse_amount(s: str | None) -> Decimal:
        if not s:
            raise ValueError("Amount field is empty")
        cleaned = s.strip().replace("\xa0", "").replace(" ", "")
        return Decimal(cleaned.replace(",", "."))

    @staticmethod
    def _clean(s: str | None) -> str | None:
        if not s:
            return None
        stripped = s.strip()
        return stripped or None
```

- [ ] **Step 2: Run unit tests (excluding integration)**

```bash
cd backend && .venv/bin/pytest tests/test_airbank_pdf_parser.py -v -k "not integration"
```

Expected: All unit tests pass. If any fail due to mismatched column structure, revisit probe output from Task 2 and update `_COL_*` constants and test fixtures.

- [ ] **Step 3: Run integration test**

```bash
cd backend && .venv/bin/pytest tests/test_airbank_pdf_parser.py::test_integration_real_pdf -v
```

Expected: PASS. If transaction count is wrong, count transactions in the PDF manually and update the assertion in `test_integration_real_pdf`.

- [ ] **Step 4: Run the full test suite to check for regressions**

```bash
cd backend && .venv/bin/pytest -v 2>&1 | tail -20
```

Expected: All previously passing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/parsers/airbank_pdf.py backend/tests/test_airbank_pdf_parser.py
git commit -m "feat: add AirBankPdfParser using pdfplumber"
```

---

### Task 5: Wire `AirBankPdfParser` into `import_service.py`

**Files:**
- Modify: `backend/app/services/import_service.py:12-13` (imports)
- Modify: `backend/app/services/import_service.py:37-38` (parser selection)

- [ ] **Step 1: Add import at top of `import_service.py`**

After the existing parser imports (line 13), add:

```python
from app.services.parsers.airbank_pdf import AirBankPdfParser
```

- [ ] **Step 2: Add `"airbank"` branch in `process_batch`**

In `process_batch`, the current parser selection block (lines 37–47):

```python
        if account.bank == "partners":
            rows = PartnersParser().parse(file_bytes)
        else:
            ...
```

Replace with:

```python
        if account.bank == "partners":
            rows = PartnersParser().parse(file_bytes)
        elif account.bank == "airbank":
            rows = AirBankPdfParser().parse(file_bytes)
        else:
            if not column_mapping:
                column_mapping = batch.column_mapping
            if not column_mapping:
                batch.status = "failed"
                batch.error_message = "column_mapping required for generic CSV accounts"
                await db.commit()
                return
            rows = GenericCsvParser.parse(file_bytes, column_mapping)
            if not batch.column_mapping:
                batch.column_mapping = column_mapping
```

- [ ] **Step 3: Run full test suite**

```bash
cd backend && .venv/bin/pytest -v 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/import_service.py
git commit -m "feat: wire AirBankPdfParser into import pipeline for bank='airbank'"
```

---

## Self-Review

**Spec coverage:**
- [x] AirBank PDF parser using pdfplumber — Task 4
- [x] `parse(file_bytes) -> list[TransactionRow]` interface — Task 4
- [x] All TransactionRow fields mapped — Task 4 (`_parse_row`)
- [x] Wired into import_service with `"airbank"` bank value — Task 5
- [x] `pdfplumber` dependency added — Task 2
- [x] `.env.test` for local dev — Task 1
- [x] Tests for unit row parsing + integration with real PDF — Task 3

**Placeholder scan:** No TBDs, no vague steps. All code is complete. Task 3 integration test transaction count (15) must be verified against the actual PDF after running Task 2 probe — this is explicit in the step.

**Type consistency:** `_parse_row` takes `list[str | None]` and returns `TransactionRow` consistently across Tasks 3 and 4. `_is_data_row` takes same type.
