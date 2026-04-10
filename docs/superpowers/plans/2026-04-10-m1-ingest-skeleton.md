# M1 — Ingest Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import a real Partners Bank CSV export and view transactions in a paginated list via the browser.

**Architecture:** FastAPI backend with SQLAlchemy async models; CSV parsed by a pure-function `PartnersParser`; import runs as a FastAPI background task (fire-and-forget); React frontend with Imports page (upload + history) and Analytics skeleton (main page).

**Tech Stack:** Python 3.11, FastAPI 0.111, SQLAlchemy 2.0 async, asyncpg, Alembic, pydantic-settings · React 18, TypeScript 5, Vite 5, TanStack Query 5, Tailwind CSS 3, react-router-dom 6 · Neon Postgres

---

> ⚠️ **BLOCKER — Read Before Starting**
>
> Task 4 (`PartnersParser`) cannot be implemented until a real Partners Bank CSV export is provided at `sample_data/partners_sample.csv`. Do not guess column names or encoding. All other tasks (1–3, 5–12) can proceed in parallel with the parser stub.

---

## Task 1: Backend Scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/parsers/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "final-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.13.0",
    "asyncpg>=0.29.0",
    "pydantic-settings>=2.4.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create .env.example**

```
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 3: Create app/config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

settings = Settings()
```

- [ ] **Step 4: Create app/db/session.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 5: Create app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Finance Analyzer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 6: Copy backend/.env.example to backend/.env and fill in DATABASE_URL from Neon**

- [ ] **Step 7: Install and verify**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
uvicorn app.main:app --reload
```

Expected: `Application startup complete.` on port 8000.

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat(m1): backend scaffold — FastAPI app, config, DB session"
```

---

## Task 2: Database Models + Alembic Migrations

**Files:**
- Create: `backend/app/db/models.py`
- Create: `backend/app/db/migrations/env.py`
- Create: `backend/app/db/migrations/script.py.mako`
- Create: `backend/alembic.ini`

- [ ] **Step 1: Create app/db/models.py**

```python
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer,
    Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    bank: Mapped[str] = mapped_column(String, nullable=False)  # "partners" | "generic"
    iban: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="CZK")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
    import_batches: Mapped[list["ImportBatch"]] = relationship(back_populates="account")

class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    parser_used: Mapped[str] = mapped_column(String, nullable=False)
    column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="processing")  # processing | completed | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="import_batches")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="import_batch")

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("import_batches.id"), nullable=False)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="CZK")
    counterparty_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    counterparty_account: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    categorization_source: Mapped[str | None] = mapped_column(String, nullable=True)  # rule | llm | manual
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    is_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transfer_pair_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    hash_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    account: Mapped["Account"] = relationship(back_populates="transactions")
    import_batch: Mapped["ImportBatch"] = relationship(back_populates="transactions")
```

Note: `category_id` FK references `categories.id` which is created in M2. Add the FK then; for M1 the column is present but the FK constraint is added in the M2 migration.

- [ ] **Step 2: Initialise Alembic**

```bash
cd backend
alembic init app/db/migrations
```

- [ ] **Step 3: Edit alembic.ini — set sqlalchemy.url placeholder**

In `alembic.ini`, set:
```ini
sqlalchemy.url = placeholder  # overridden in env.py
```

- [ ] **Step 4: Edit app/db/migrations/env.py**

Replace the generated `env.py` with:

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.config import settings
from app.db.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 5: Generate and apply M1 migration**

```bash
alembic revision --autogenerate -m "m1_initial_schema"
alembic upgrade head
```

Expected: tables `accounts`, `import_batches`, `transactions` created in Neon (without `categories` FK constraint yet).

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/ backend/alembic.ini
git commit -m "feat(m1): SQLAlchemy models + Alembic migration for accounts/transactions/import_batches"
```

---

## Task 3: Accounts CRUD API

**Files:**
- Create: `backend/app/api/accounts.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_accounts_api.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_accounts_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

async def test_create_account(client):
    resp = await client.post("/api/accounts", json={
        "name": "Partners – Checking",
        "bank": "partners",
        "currency": "CZK",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Partners – Checking"
    assert "id" in data

async def test_list_accounts(client):
    await client.post("/api/accounts", json={"name": "A", "bank": "partners", "currency": "CZK"})
    resp = await client.get("/api/accounts")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

async def test_get_account(client):
    create = await client.post("/api/accounts", json={"name": "B", "bank": "generic", "currency": "CZK"})
    acct_id = create.json()["id"]
    resp = await client.get(f"/api/accounts/{acct_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == acct_id

async def test_update_account(client):
    create = await client.post("/api/accounts", json={"name": "Old", "bank": "partners", "currency": "CZK"})
    acct_id = create.json()["id"]
    resp = await client.patch(f"/api/accounts/{acct_id}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"

async def test_delete_account(client):
    create = await client.post("/api/accounts", json={"name": "Del", "bank": "partners", "currency": "CZK"})
    acct_id = create.json()["id"]
    resp = await client.delete(f"/api/accounts/{acct_id}")
    assert resp.status_code == 204
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_accounts_api.py -v
```

Expected: `ImportError` or 404 (routes not registered yet).

- [ ] **Step 3: Create app/api/accounts.py**

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Account

router = APIRouter()

class AccountCreate(BaseModel):
    name: str
    bank: str
    currency: str = "CZK"
    iban: str | None = None

class AccountUpdate(BaseModel):
    name: str | None = None
    bank: str | None = None
    currency: str | None = None
    iban: str | None = None
    is_active: bool | None = None

class AccountOut(BaseModel):
    id: uuid.UUID
    name: str
    bank: str
    currency: str
    iban: str | None
    is_active: bool

    model_config = {"from_attributes": True}

@router.get("", response_model=list[AccountOut])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.is_active == True))
    return result.scalars().all()

@router.post("", response_model=AccountOut, status_code=201)
async def create_account(body: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = Account(**body.model_dump())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account

@router.get("/{account_id}", response_model=AccountOut)
async def get_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(account_id: uuid.UUID, body: AccountUpdate, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return account

@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_active = False
    await db.commit()
```

- [ ] **Step 4: Register router in app/main.py**

```python
from app.api import accounts

app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_accounts_api.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/accounts.py backend/app/main.py backend/tests/test_accounts_api.py
git commit -m "feat(m1): accounts CRUD API"
```

---

## Task 4: PartnersParser

> ⚠️ **BLOCKED** until `sample_data/partners_sample.csv` is provided. Complete Tasks 1–3, 5–9 first.

**Files:**
- Create: `backend/app/services/parsers/base.py`
- Create: `backend/app/services/parsers/partners.py`
- Create: `backend/tests/test_partners_parser.py`
- Add: `sample_data/partners_sample.csv` (user-provided, gitignored)

- [ ] **Step 1: Create parsers/base.py — TransactionRow dataclass**

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass
class TransactionRow:
    booking_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    counterparty_name: str | None
    counterparty_account: str | None
    description: str | None
    raw_reference: str | None
```

- [ ] **Step 2: Inspect the real CSV sample**

Open `sample_data/partners_sample.csv` in a text editor. Note:
- File encoding (likely UTF-8 or CP1250)
- Column separator (`,` or `;`)
- Exact header names for: date, value date, amount, currency, counterparty name, counterparty account, description, reference
- Date format (e.g., `DD.MM.YYYY` or `YYYY-MM-DD`)
- Amount format (e.g., `1 234,56` with space-thousands and comma-decimal)

Record findings as a comment at the top of `partners.py`.

- [ ] **Step 3: Write failing tests against the real file**

```python
# backend/tests/test_partners_parser.py
from pathlib import Path
from decimal import Decimal
from app.services.parsers.partners import PartnersParser

SAMPLE = Path(__file__).parent.parent.parent / "sample_data" / "partners_sample.csv"

def test_parse_returns_rows():
    rows = PartnersParser.parse(SAMPLE.read_bytes())
    assert len(rows) > 0

def test_row_types():
    rows = PartnersParser.parse(SAMPLE.read_bytes())
    row = rows[0]
    assert isinstance(row.amount, Decimal)
    assert row.booking_date is not None

def test_no_header_row_in_output():
    rows = PartnersParser.parse(SAMPLE.read_bytes())
    # amount must be numeric, not the header string
    assert all(isinstance(r.amount, Decimal) for r in rows)
```

- [ ] **Step 4: Implement PartnersParser based on real column names**

```python
# backend/app/services/parsers/partners.py
# Column mapping discovered from sample_data/partners_sample.csv:
# (Fill in actual column names after inspecting the file)
# encoding: <discovered>
# separator: <discovered>
# date format: <discovered>
# amount format: <discovered>

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from app.services.parsers.base import TransactionRow

class PartnersParser:
    ENCODING = "utf-8"       # update after inspecting real file
    SEPARATOR = ";"          # update after inspecting real file
    DATE_FORMAT = "%d.%m.%Y" # update after inspecting real file

    # Update these with exact header names from the CSV:
    COL_BOOKING_DATE = "Datum zaúčtování"
    COL_VALUE_DATE = "Datum valutace"
    COL_AMOUNT = "Částka"
    COL_CURRENCY = "Měna"
    COL_COUNTERPARTY_NAME = "Název protistrany"
    COL_COUNTERPARTY_ACCOUNT = "Účet protistrany"
    COL_DESCRIPTION = "Zpráva pro příjemce"
    COL_REFERENCE = "Referenční číslo"

    @classmethod
    def parse(cls, file_bytes: bytes) -> list[TransactionRow]:
        text = file_bytes.decode(cls.ENCODING)
        reader = csv.DictReader(io.StringIO(text), delimiter=cls.SEPARATOR)
        rows = []
        for raw in reader:
            try:
                amount_str = raw[cls.COL_AMOUNT].replace("\xa0", "").replace(" ", "").replace(",", ".")
                amount = Decimal(amount_str)
            except (KeyError, InvalidOperation):
                continue
            rows.append(TransactionRow(
                booking_date=datetime.strptime(raw[cls.COL_BOOKING_DATE].strip(), cls.DATE_FORMAT).date(),
                value_date=datetime.strptime(raw[cls.COL_VALUE_DATE].strip(), cls.DATE_FORMAT).date()
                    if raw.get(cls.COL_VALUE_DATE, "").strip() else None,
                amount=amount,
                currency=raw.get(cls.COL_CURRENCY, "CZK").strip(),
                counterparty_name=raw.get(cls.COL_COUNTERPARTY_NAME, "").strip() or None,
                counterparty_account=raw.get(cls.COL_COUNTERPARTY_ACCOUNT, "").strip() or None,
                description=raw.get(cls.COL_DESCRIPTION, "").strip() or None,
                raw_reference=raw.get(cls.COL_REFERENCE, "").strip() or None,
            ))
        return rows
```

- [ ] **Step 5: Run tests against the real file**

```bash
pytest tests/test_partners_parser.py -v
```

Expected: all 3 tests pass. If column names don't match, update the `COL_*` constants and re-run.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/parsers/ backend/tests/test_partners_parser.py
git commit -m "feat(m1): PartnersParser built against real CSV sample"
```

---

## Task 5: ImportService

**Files:**
- Create: `backend/app/services/import_service.py`
- Create: `backend/tests/test_import_service.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_import_service.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from app.services.import_service import ImportService
from app.services.parsers.base import TransactionRow
from datetime import date
from decimal import Decimal
import uuid

def make_row(**kwargs):
    defaults = dict(
        booking_date=date(2026, 1, 15),
        value_date=None,
        amount=Decimal("-250.00"),
        currency="CZK",
        counterparty_name="ALBERT",
        counterparty_account=None,
        description="Nákup",
        raw_reference="REF001",
    )
    return TransactionRow(**{**defaults, **kwargs})

async def test_hash_key_is_deterministic():
    row = make_row()
    account_id = uuid.uuid4()
    h1 = ImportService.compute_hash_key(account_id, row)
    h2 = ImportService.compute_hash_key(account_id, row)
    assert h1 == h2

async def test_hash_key_differs_for_different_amounts():
    account_id = uuid.uuid4()
    r1 = make_row(amount=Decimal("-100.00"))
    r2 = make_row(amount=Decimal("-200.00"))
    assert ImportService.compute_hash_key(account_id, r1) != ImportService.compute_hash_key(account_id, r2)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_import_service.py -v
```

Expected: `ImportError` (module not found).

- [ ] **Step 3: Create app/services/import_service.py**

```python
import hashlib
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, ImportBatch, Transaction
from app.services.parsers.base import TransactionRow
from app.services.parsers.partners import PartnersParser

PARSER_REGISTRY = {
    "partners": PartnersParser,
}

@dataclass
class ImportResult:
    batch_id: uuid.UUID
    imported: int
    duplicates: int

class ImportService:

    @staticmethod
    def compute_hash_key(account_id: uuid.UUID, row: TransactionRow) -> str:
        raw = f"{account_id}|{row.booking_date}|{row.amount}|{row.counterparty_name or ''}|{row.description or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _select_parser(bank: str):
        parser = PARSER_REGISTRY.get(bank)
        if parser is None:
            raise ValueError(f"No parser for bank '{bank}'. Use generic CSV mapper.")
        return parser

    @classmethod
    async def import_file(
        cls,
        db: AsyncSession,
        account: Account,
        file_bytes: bytes,
        filename: str,
    ) -> ImportResult:
        parser = cls._select_parser(account.bank)
        rows = parser.parse(file_bytes)

        batch = ImportBatch(
            account_id=account.id,
            filename=filename,
            parser_used=account.bank,
            row_count=len(rows),
            status="processing",
        )
        db.add(batch)
        await db.flush()  # get batch.id

        # Compute hash keys
        hash_keys = {cls.compute_hash_key(account.id, row): row for row in rows}

        # Find existing duplicates
        existing = await db.execute(
            select(Transaction.hash_key).where(
                Transaction.hash_key.in_(list(hash_keys.keys()))
            )
        )
        existing_keys = {r[0] for r in existing.all()}

        new_rows = {k: v for k, v in hash_keys.items() if k not in existing_keys}

        # Insert new transactions
        for hash_key, row in new_rows.items():
            tx = Transaction(
                account_id=account.id,
                import_batch_id=batch.id,
                booking_date=row.booking_date,
                value_date=row.value_date,
                amount=row.amount,
                currency=row.currency,
                counterparty_name=row.counterparty_name,
                counterparty_account=row.counterparty_account,
                description=row.description,
                raw_reference=row.raw_reference,
                hash_key=hash_key,
            )
            db.add(tx)

        batch.imported_count = len(new_rows)
        batch.duplicate_count = len(rows) - len(new_rows)
        batch.status = "completed"

        await db.commit()
        return ImportResult(
            batch_id=batch.id,
            imported=batch.imported_count,
            duplicates=batch.duplicate_count,
        )

    @classmethod
    async def get_batches(cls, db: AsyncSession) -> list[ImportBatch]:
        result = await db.execute(
            select(ImportBatch).order_by(ImportBatch.imported_at.desc())
        )
        return result.scalars().all()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_import_service.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/import_service.py backend/tests/test_import_service.py
git commit -m "feat(m1): ImportService with dedup by hash_key"
```

---

## Task 6: Import + Transactions API

**Files:**
- Create: `backend/app/api/imports.py`
- Create: `backend/app/api/transactions.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create app/api/imports.py**

```python
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Account, ImportBatch
from app.services.import_service import ImportService

router = APIRouter()

class BatchOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    filename: str
    parser_used: str
    row_count: int
    imported_count: int
    duplicate_count: int
    status: str
    error_message: str | None

    model_config = {"from_attributes": True}

class ImportInitiated(BaseModel):
    batch_id: uuid.UUID
    message: str

async def _run_import(account_id: uuid.UUID, file_bytes: bytes, filename: str):
    """Background task — runs import pipeline independently."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        account = await db.get(Account, account_id)
        if account:
            try:
                await ImportService.import_file(db, account, file_bytes, filename)
            except Exception as e:
                # Mark batch as failed (best-effort — batch may not exist yet if parse failed early)
                pass

@router.post("", response_model=ImportInitiated, status_code=202)
async def upload_import(
    background_tasks: BackgroundTasks,
    account_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    file_bytes = await file.read()

    # Create a placeholder batch immediately so the UI can show it
    batch = ImportBatch(
        account_id=account_id,
        filename=file.filename or "upload.csv",
        parser_used=account.bank,
        row_count=0,
        status="processing",
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    background_tasks.add_task(_run_import, account_id, file_bytes, file.filename or "upload.csv")

    return ImportInitiated(batch_id=batch.id, message="Import started")

@router.get("", response_model=list[BatchOut])
async def list_batches(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ImportBatch).order_by(ImportBatch.imported_at.desc())
    )
    return result.scalars().all()

@router.get("/{batch_id}", response_model=BatchOut)
async def get_batch(batch_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    batch = await db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch
```

- [ ] **Step 2: Create app/api/transactions.py**

```python
import uuid
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Transaction

router = APIRouter()

class TransactionOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    booking_date: date
    amount: Decimal
    currency: str
    counterparty_name: str | None
    description: str | None
    category_id: uuid.UUID | None
    categorization_source: str | None
    is_transfer: bool

    model_config = {"from_attributes": True}

class PaginatedTransactions(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int

@router.get("", response_model=PaginatedTransactions)
async def list_transactions(
    account_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Transaction)
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if date_from:
        q = q.where(Transaction.booking_date >= date_from)
    if date_to:
        q = q.where(Transaction.booking_date <= date_to)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(Transaction.booking_date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)

    return PaginatedTransactions(
        items=result.scalars().all(),
        total=total,
        page=page,
        page_size=page_size,
    )
```

- [ ] **Step 3: Register both routers in app/main.py**

```python
from app.api import accounts, imports, transactions

app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
```

- [ ] **Step 4: Manual smoke test**

```bash
uvicorn app.main:app --reload
# In another terminal:
curl http://localhost:8000/api/accounts
curl http://localhost:8000/api/imports
curl http://localhost:8000/api/transactions
```

Expected: empty arrays `[]` for all three.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/ backend/app/main.py
git commit -m "feat(m1): imports + transactions API endpoints"
```

---

## Task 7: Frontend Scaffold

**Files:**
- Create: `frontend/` (Vite project)
- Create: `frontend/src/api/client.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Scaffold Vite + React + TypeScript project**

```bash
cd /path/to/FinAl
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2: Install dependencies**

```bash
npm install @tanstack/react-query react-router-dom axios
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

- [ ] **Step 3: Configure tailwind.config.js**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 4: Update src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 5: Create src/api/client.ts**

```typescript
import axios from "axios";

const client = axios.create({
  baseURL: "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

export default client;
```

- [ ] **Step 6: Verify dev server starts**

```bash
npm run dev
```

Expected: `http://localhost:5173` loads a blank Vite default page.

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(m1): frontend scaffold — Vite, React, TypeScript, Tailwind, TanStack Query"
```

---

## Task 8: Nav Bar + Routing

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/NavBar.tsx`
- Create: `frontend/src/components/ProcessingStatus.tsx`
- Create: `frontend/src/api/imports.ts`

- [ ] **Step 1: Create src/api/imports.ts**

```typescript
import client from "./client";

export interface Batch {
  id: string;
  account_id: string;
  filename: string;
  parser_used: string;
  row_count: number;
  imported_count: number;
  duplicate_count: number;
  status: "processing" | "completed" | "failed";
  error_message: string | null;
}

export async function listBatches(): Promise<Batch[]> {
  const { data } = await client.get<Batch[]>("/api/imports");
  return data;
}

export async function uploadImport(accountId: string, file: File): Promise<{ batch_id: string }> {
  const form = new FormData();
  form.append("account_id", accountId);
  form.append("file", file);
  const { data } = await client.post("/api/imports", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
```

- [ ] **Step 2: Create src/components/ProcessingStatus.tsx**

```tsx
import { useQuery } from "@tanstack/react-query";
import { listBatches } from "../api/imports";

export default function ProcessingStatus() {
  const { data: batches = [] } = useQuery({
    queryKey: ["batches"],
    queryFn: listBatches,
    refetchInterval: 5000,
  });

  const isProcessing = batches.some((b) => b.status === "processing");
  const hasFailed = batches.some((b) => b.status === "failed");

  const color = hasFailed ? "bg-red-500" : isProcessing ? "bg-yellow-400" : "bg-green-500";
  const title = hasFailed ? "Import failed" : isProcessing ? "Processing…" : "Idle";

  return (
    <span className="flex items-center gap-2 text-sm text-gray-500" title={title}>
      <span className={`w-2 h-2 rounded-full ${color}`} />
      {title}
    </span>
  );
}
```

- [ ] **Step 3: Create src/components/NavBar.tsx**

```tsx
import { NavLink } from "react-router-dom";
import ProcessingStatus from "./ProcessingStatus";

const links = [
  { to: "/", label: "Analytics" },
  { to: "/imports", label: "Imports" },
  { to: "/rules", label: "Rules" },
  { to: "/settings", label: "Settings" },
];

export default function NavBar() {
  return (
    <nav className="flex items-center gap-1 px-6 py-3 border-b border-gray-200 bg-white">
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.to === "/"}
          className={({ isActive }) =>
            `px-4 py-2 rounded text-sm font-medium transition-colors ` +
            (isActive ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100")
          }
        >
          {l.label}
        </NavLink>
      ))}
      <div className="ml-auto">
        <ProcessingStatus />
      </div>
    </nav>
  );
}
```

- [ ] **Step 4: Create src/App.tsx**

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import AnalyticsPage from "./pages/Analytics";
import ImportsPage from "./pages/Imports";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <NavBar />
          <main className="p-6">
            <Routes>
              <Route path="/" element={<AnalyticsPage />} />
              <Route path="/imports" element={<ImportsPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 5: Update src/main.tsx**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 6: Verify nav renders**

Open `http://localhost:5173`. Expected: nav bar with Analytics / Imports / Rules / Settings tabs, green status dot.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat(m1): nav bar, routing skeleton, processing status indicator"
```

---

## Task 9: Analytics Page Skeleton (Main Page)

**Files:**
- Create: `frontend/src/pages/Analytics/index.tsx`

- [ ] **Step 1: Create pages/Analytics/index.tsx — skeleton**

```tsx
export default function AnalyticsPage() {
  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h1>
      <p className="text-gray-500">
        Analytics will be available after importing transactions (M4).
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Verify it renders at `http://localhost:5173/`**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Analytics/
git commit -m "feat(m1): analytics page skeleton (placeholder for M4)"
```

---

## Task 10: Imports Page

**Files:**
- Create: `frontend/src/pages/Imports/index.tsx`
- Create: `frontend/src/pages/Imports/UploadForm.tsx`
- Create: `frontend/src/pages/Imports/BatchHistory.tsx`
- Create: `frontend/src/api/accounts.ts`

- [ ] **Step 1: Create src/api/accounts.ts**

```typescript
import client from "./client";

export interface Account {
  id: string;
  name: string;
  bank: string;
  currency: string;
  is_active: boolean;
}

export async function listAccounts(): Promise<Account[]> {
  const { data } = await client.get<Account[]>("/api/accounts");
  return data;
}
```

- [ ] **Step 2: Create pages/Imports/UploadForm.tsx**

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listAccounts } from "../../api/accounts";
import { uploadImport } from "../../api/imports";

export default function UploadForm() {
  const qc = useQueryClient();
  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const [accountId, setAccountId] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const mutation = useMutation({
    mutationFn: () => uploadImport(accountId, file!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["batches"] });
      setFile(null);
    },
  });

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
      <h2 className="text-lg font-semibold mb-4">Upload Bank Export</h2>
      <div className="flex flex-col gap-4 max-w-md">
        <select
          className="border border-gray-300 rounded px-3 py-2 text-sm"
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
        >
          <option value="">Select account…</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <input
          type="file"
          accept=".csv"
          className="text-sm"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
          disabled={!accountId || !file || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? "Uploading…" : "Import"}
        </button>
        {mutation.isSuccess && <p className="text-green-600 text-sm">Import started!</p>}
        {mutation.isError && <p className="text-red-500 text-sm">Upload failed. Check the console.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create pages/Imports/BatchHistory.tsx**

```tsx
import { useQuery } from "@tanstack/react-query";
import { listBatches } from "../../api/imports";

const STATUS_BADGE: Record<string, string> = {
  processing: "bg-yellow-100 text-yellow-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function BatchHistory() {
  const { data: batches = [], isLoading } = useQuery({
    queryKey: ["batches"],
    queryFn: listBatches,
    refetchInterval: 3000,
  });

  if (isLoading) return <p className="text-gray-400 text-sm">Loading…</p>;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <h2 className="text-lg font-semibold px-6 py-4 border-b">Import History</h2>
      {batches.length === 0 ? (
        <p className="px-6 py-8 text-gray-400 text-sm">No imports yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              {["File", "Account", "Rows", "Imported", "Duplicates", "Status", "Date"].map((h) => (
                <th key={h} className="px-4 py-2 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {batches.map((b) => (
              <tr key={b.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{b.filename}</td>
                <td className="px-4 py-3 text-gray-500">{b.account_id}</td>
                <td className="px-4 py-3">{b.row_count}</td>
                <td className="px-4 py-3 text-green-700">{b.imported_count}</td>
                <td className="px-4 py-3 text-gray-400">{b.duplicate_count}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[b.status] ?? ""}`}>
                    {b.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400">{new Date(b.imported_at ?? "").toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

Note: `imported_at` field needs to be added to `BatchOut` pydantic model in the backend.

- [ ] **Step 4: Create pages/Imports/index.tsx**

```tsx
import UploadForm from "./UploadForm";
import BatchHistory from "./BatchHistory";

export default function ImportsPage() {
  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Imports</h1>
      <UploadForm />
      <BatchHistory />
    </div>
  );
}
```

- [ ] **Step 5: Add `imported_at` to BatchOut in backend/app/api/imports.py**

```python
from datetime import datetime

class BatchOut(BaseModel):
    ...
    imported_at: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 6: Verify end-to-end**

1. Start backend: `uvicorn app.main:app --reload`
2. Create an account: `POST /api/accounts` via curl or Swagger at `http://localhost:8000/docs`
3. Open `http://localhost:5173/imports`
4. Select account, upload `sample_data/partners_sample.csv`
5. History table shows the batch; status transitions from `processing` to `completed`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat(m1): imports page — upload form + batch history table"
```

---

## M1 Acceptance Criteria Verification

- [ ] Upload a real Partners Bank export → correct row count imported (check batch `imported_count`)
- [ ] Re-upload the same file → `imported_count = 0`, `duplicate_count = N`
- [ ] `GET /api/transactions` returns imported rows with date, amount, counterparty
- [ ] Nav status indicator shows yellow while processing, green when done
- [ ] Analytics page loads at `/` (skeleton)
