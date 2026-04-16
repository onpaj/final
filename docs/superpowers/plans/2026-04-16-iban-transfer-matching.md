# IBAN-Validated Transfer Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `TransferMatcher` validate that `counterparty_account` on each transaction explicitly references the other internal account, normalizing between IBAN and Czech local (`account/bankcode`) formats.

**Architecture:** New pure-function module `iban_utils.py` handles all format normalization. `TransferMatcher` loads IBAN-configured accounts at the start of `match_batch` and uses those identifiers to validate every candidate pair — both sides must cross-reference. Accounts without IBAN are skipped silently.

**Tech Stack:** Python 3.11, SQLAlchemy async, pytest-asyncio, `re` (stdlib)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `backend/app/services/iban_utils.py` | IBAN/local normalization, identifier set builder |
| Create | `backend/tests/test_iban_utils.py` | Unit tests for all iban_utils functions |
| Modify | `backend/app/services/transfer_matcher.py` | Load account identifiers, validate counterparty accounts |
| Modify | `backend/tests/test_transfer_matcher.py` | Update existing tests + add new validation cases |

---

## Task 1: `iban_utils.py` — write failing tests

**Files:**
- Create: `backend/tests/test_iban_utils.py`

- [ ] **Step 1: Create the test file**

```python
# backend/tests/test_iban_utils.py
import pytest
from app.services.iban_utils import (
    normalize_iban,
    iban_to_local_cz,
    normalize_local_cz,
    account_identifiers,
)

# --- normalize_iban ---

def test_normalize_iban_strips_spaces():
    assert normalize_iban("CZ65 0800 0000 1920 0014 5399") == "CZ6508000000192000145399"

def test_normalize_iban_uppercases():
    assert normalize_iban("cz6508000000192000145399") == "CZ6508000000192000145399"

def test_normalize_iban_already_normalized():
    assert normalize_iban("CZ6508000000192000145399") == "CZ6508000000192000145399"

# --- iban_to_local_cz ---
# Czech IBAN structure (24 chars): CZ + 2 check + 4 bank + 6 prefix + 10 account
# CZ6508000000192000145399 → bank=0800, prefix=000019→19, account=2000145399
# CZ6503000000000001234567 → bank=0300, prefix=000000→0,  account=0001234567→1234567

def test_iban_to_local_cz_with_prefix():
    assert iban_to_local_cz("CZ6508000000192000145399") == "19-2000145399/0800"

def test_iban_to_local_cz_without_prefix():
    assert iban_to_local_cz("CZ6503000000000001234567") == "1234567/0300"

def test_iban_to_local_cz_accepts_spaces():
    assert iban_to_local_cz("CZ65 0800 0000 1920 0014 5399") == "19-2000145399/0800"

def test_iban_to_local_cz_non_czech_returns_none():
    assert iban_to_local_cz("DE89370400440532013000") is None

def test_iban_to_local_cz_malformed_returns_none():
    assert iban_to_local_cz("NOTANIBAN") is None

def test_iban_to_local_cz_wrong_length_returns_none():
    assert iban_to_local_cz("CZ650800") is None

# --- normalize_local_cz ---

def test_normalize_local_cz_basic():
    assert normalize_local_cz("1234567/0300") == "1234567/0300"

def test_normalize_local_cz_strips_leading_zeros_from_account():
    assert normalize_local_cz("0001234567/0300") == "1234567/0300"

def test_normalize_local_cz_with_prefix():
    assert normalize_local_cz("19-2000145399/0800") == "19-2000145399/0800"

def test_normalize_local_cz_strips_leading_zeros_from_prefix():
    assert normalize_local_cz("019-2000145399/0800") == "19-2000145399/0800"

def test_normalize_local_cz_zero_prefix_omitted():
    assert normalize_local_cz("0-1234567/0300") == "1234567/0300"

def test_normalize_local_cz_no_slash_returns_none():
    assert normalize_local_cz("notanaccount") is None

def test_normalize_local_cz_non_numeric_returns_none():
    assert normalize_local_cz("abc/0300") is None

# --- account_identifiers ---

def test_account_identifiers_czech_iban_without_prefix():
    ids = account_identifiers("CZ6503000000000001234567")
    assert ids == {"CZ6503000000000001234567", "1234567/0300"}

def test_account_identifiers_czech_iban_with_prefix():
    ids = account_identifiers("CZ6508000000192000145399")
    assert ids == {"CZ6508000000192000145399", "19-2000145399/0800"}

def test_account_identifiers_normalizes_input_iban():
    # Spaces in input IBAN should be normalized in the set
    ids = account_identifiers("CZ65 0800 0000 1920 0014 5399")
    assert "CZ6508000000192000145399" in ids

def test_account_identifiers_non_czech_iban_returns_only_iban():
    ids = account_identifiers("DE89370400440532013000")
    assert ids == {"DE89370400440532013000"}
```

- [ ] **Step 2: Run to confirm all tests fail with ImportError**

```bash
cd backend && python -m pytest tests/test_iban_utils.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'normalize_iban' from 'app.services.iban_utils'` (or `ModuleNotFoundError`)

---

## Task 2: `iban_utils.py` — implement

**Files:**
- Create: `backend/app/services/iban_utils.py`

- [ ] **Step 1: Create the module**

```python
# backend/app/services/iban_utils.py
import re

_IBAN_RE = re.compile(r'^[A-Za-z]{2}\d{2}')


def normalize_iban(s: str) -> str:
    """Strip spaces and uppercase. Works for any IBAN."""
    return s.replace(" ", "").upper()


def iban_to_local_cz(iban: str) -> str | None:
    """
    Derive Czech local account format from a Czech IBAN.

    Czech IBAN (24 chars): CZ + 2 check + 4 bank + 6 prefix + 10 account
    Returns 'account/bank' (no prefix) or 'prefix-account/bank'.
    Returns None for non-Czech or malformed IBANs.
    """
    normalized = normalize_iban(iban)
    if not normalized.startswith("CZ") or len(normalized) != 24:
        return None
    try:
        bank_code = normalized[4:8]
        prefix_int = int(normalized[8:14])
        account_int = int(normalized[14:24])
    except ValueError:
        return None
    account_str = str(account_int)
    if prefix_int == 0:
        return f"{account_str}/{bank_code}"
    return f"{prefix_int}-{account_str}/{bank_code}"


def normalize_local_cz(s: str) -> str | None:
    """
    Normalize a Czech local account string to canonical form.

    Accepts 'account/bank' or 'prefix-account/bank'.
    Strips leading zeros from prefix and account.
    Returns None if unparseable.
    """
    s = s.strip()
    if "/" not in s:
        return None
    slash_idx = s.rfind("/")
    bank_code = s[slash_idx + 1:].strip()
    account_part = s[:slash_idx].strip()
    if "-" in account_part:
        dash_idx = account_part.index("-")
        prefix_str = account_part[:dash_idx].strip()
        account_str = account_part[dash_idx + 1:].strip()
        try:
            prefix_int = int(prefix_str)
            account_int = int(account_str)
        except ValueError:
            return None
        if prefix_int == 0:
            return f"{account_int}/{bank_code}"
        return f"{prefix_int}-{account_int}/{bank_code}"
    else:
        try:
            account_int = int(account_part)
        except ValueError:
            return None
        return f"{account_int}/{bank_code}"


def account_identifiers(iban: str) -> set[str]:
    """
    Return all canonical identifier forms for an account given its IBAN.
    For Czech IBANs: {normalized_iban, local_cz_format}.
    For other IBANs: {normalized_iban}.
    """
    normalized = normalize_iban(iban)
    identifiers: set[str] = {normalized}
    local = iban_to_local_cz(normalized)
    if local:
        identifiers.add(local)
    return identifiers
```

- [ ] **Step 2: Run tests**

```bash
cd backend && python -m pytest tests/test_iban_utils.py -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/iban_utils.py backend/tests/test_iban_utils.py
git commit -m "feat: add iban_utils for IBAN/local CZ account normalization"
```

---

## Task 3: Update `TransferMatcher` — write failing tests first

**Files:**
- Modify: `backend/tests/test_transfer_matcher.py`

- [ ] **Step 1: Replace the contents of the test file**

The existing `make_tx` helper needs a `counterparty_account` param. The existing tests need `_account_identifiers` set on the matcher. Add new test cases for cross-format and rejection scenarios.

```python
# backend/tests/test_transfer_matcher.py
import pytest
import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.services.iban_utils import account_identifiers
from app.services.transfer_matcher import TransferMatcher

IBAN_A = "CZ6503000000000001234567"  # bank=0300, account=1234567, no prefix
IBAN_B = "CZ6508000000192000145399"  # bank=0800, account=2000145399, prefix=19


def make_tx(amount, booking_date, account_id=None, tx_id=None, counterparty_account=None):
    tx = MagicMock()
    tx.id = tx_id or uuid.uuid4()
    tx.amount = Decimal(str(amount))
    tx.booking_date = booking_date
    tx.account_id = account_id or uuid.uuid4()
    tx.is_transfer = False
    tx.transfer_pair_id = None
    tx.category_id = None
    tx.counterparty_account = counterparty_account
    return tx


def make_matcher_with_accounts(mock_db, acct_a, iban_a, acct_b, iban_b):
    matcher = TransferMatcher(mock_db)
    matcher._account_identifiers = {
        acct_a: account_identifiers(iban_a),
        acct_b: account_identifiers(iban_b),
    }
    return matcher


# --- IBAN ↔ IBAN ---

@pytest.mark.asyncio
async def test_match_iban_to_iban():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is not None
    assert result.id == credit.id


# --- IBAN ↔ local (cross-format) ---

@pytest.mark.asyncio
async def test_match_iban_to_local():
    # Debit side exports IBAN for counterparty, credit side exports local format
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account="1234567/0300")

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is not None
    assert result.id == credit.id


# --- local ↔ local ---

@pytest.mark.asyncio
async def test_match_local_to_local():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account="19-2000145399/0800")
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account="1234567/0300")

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is not None
    assert result.id == credit.id


# --- No match: debit account has no IBAN ---

@pytest.mark.asyncio
async def test_no_match_debit_account_has_no_iban():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = TransferMatcher(mock_db)
    # Only acct_b has IBAN, acct_a does not
    matcher._account_identifiers = {acct_b: account_identifiers(IBAN_B)}
    result = await matcher._find_match(debit)
    assert result is None


# --- No match: credit account has no IBAN ---

@pytest.mark.asyncio
async def test_no_match_credit_account_has_no_iban():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = TransferMatcher(mock_db)
    # Only acct_a has IBAN, acct_b does not
    matcher._account_identifiers = {acct_a: account_identifiers(IBAN_A)}
    result = await matcher._find_match(debit)
    assert result is None


# --- No match: counterparty points to wrong account ---

@pytest.mark.asyncio
async def test_no_match_wrong_counterparty_account():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    wrong_iban = "CZ6503000000000009999999"
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=wrong_iban)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is None


# --- No match: counterparty_account is None ---

@pytest.mark.asyncio
async def test_no_match_null_counterparty_account():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=None)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is None


# --- No match: amount mismatch (still tested via empty candidate list) ---

@pytest.mark.asyncio
async def test_no_match_different_amount():
    acct_a = uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": []}
    ))

    matcher = TransferMatcher(mock_db)
    matcher._account_identifiers = {acct_a: account_identifiers(IBAN_A)}
    result = await matcher._find_match(debit)
    assert result is None
```

- [ ] **Step 2: Run to confirm relevant new tests fail**

```bash
cd backend && python -m pytest tests/test_transfer_matcher.py -v 2>&1 | head -40
```

Expected: `test_match_iban_to_iban` and new tests fail because `_find_match` doesn't check counterparty accounts yet. `test_no_match_different_amount` should still pass.

---

## Task 4: Update `TransferMatcher` — implement

**Files:**
- Modify: `backend/app/services/transfer_matcher.py`

- [ ] **Step 1: Replace the file contents**

```python
# backend/app/services/transfer_matcher.py
import re
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Category, Transaction
from app.services.iban_utils import account_identifiers, normalize_iban, normalize_local_cz

AMOUNT_TOLERANCE = Decimal("0.01")
DATE_TOLERANCE_DAYS = 2

_IBAN_PREFIX_RE = re.compile(r'^[A-Za-z]{2}\d{2}')


class TransferMatcher:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._internal_transfer_category_id: uuid.UUID | None = None
        self._account_identifiers: dict[uuid.UUID, set[str]] = {}

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

    async def _load_account_identifiers(self) -> None:
        result = await self._db.execute(
            select(Account).where(Account.iban.isnot(None))
        )
        accounts = result.scalars().all()
        self._account_identifiers = {
            acct.id: account_identifiers(acct.iban)
            for acct in accounts
        }

    def _normalize_counterparty(self, value: str | None) -> str | None:
        if not value:
            return None
        stripped = value.strip()
        if _IBAN_PREFIX_RE.match(stripped):
            return normalize_iban(stripped)
        return normalize_local_cz(stripped)

    async def _find_match(self, debit: Transaction) -> Transaction | None:
        if debit.account_id not in self._account_identifiers:
            return None

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

        debit_identifiers = self._account_identifiers[debit.account_id]

        for credit in candidates:
            if credit.account_id not in self._account_identifiers:
                continue
            credit_identifiers = self._account_identifiers[credit.account_id]

            debit_counterparty = self._normalize_counterparty(debit.counterparty_account)
            if debit_counterparty not in credit_identifiers:
                continue

            credit_counterparty = self._normalize_counterparty(credit.counterparty_account)
            if credit_counterparty not in debit_identifiers:
                continue

            return credit

        return None

    async def match_batch(self, transaction_ids: list[uuid.UUID]) -> int:
        await self._load_account_identifiers()

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

- [ ] **Step 2: Run all transfer matcher tests**

```bash
cd backend && python -m pytest tests/test_transfer_matcher.py -v
```

Expected: all tests PASS

- [ ] **Step 3: Run full test suite**

```bash
cd backend && python -m pytest -v
```

Expected: all tests PASS (no regressions)

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/transfer_matcher.py backend/tests/test_transfer_matcher.py
git commit -m "feat: validate counterparty account numbers in transfer matching"
```

---

## Self-Review Checklist

- [x] `normalize_iban` — covered in Task 1/2
- [x] `iban_to_local_cz` with/without prefix — covered in Task 1/2
- [x] `normalize_local_cz` leading zeros, prefix variants — covered in Task 1/2
- [x] `account_identifiers` — covered in Task 1/2
- [x] IBAN↔IBAN match — Task 3/4
- [x] IBAN↔local cross-format match — Task 3/4
- [x] local↔local match — Task 3/4
- [x] No match when account has no IBAN — Task 3/4
- [x] No match when counterparty wrong — Task 3/4
- [x] No match when counterparty None — Task 3/4
- [x] `_load_account_identifiers` called in `match_batch` — Task 4
- [x] No new DB fields — spec says IBAN is single source of truth ✓
- [x] Non-Czech IBAN returns only normalized IBAN in identifier set ✓
