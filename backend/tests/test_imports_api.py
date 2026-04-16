import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Account, ImportBatch, Transaction
from app.db.session import get_db
from app.main import app


def _make_account(account_id: uuid.UUID | None = None) -> Account:
    acct = MagicMock(spec=Account)
    acct.id = account_id or uuid.uuid4()
    acct.is_active = True
    acct.bank = "partners"
    return acct


def _make_batch(batch_id: uuid.UUID | None = None, account_id: uuid.UUID | None = None) -> ImportBatch:
    batch = MagicMock(spec=ImportBatch)
    batch.id = batch_id or uuid.uuid4()
    batch.account_id = account_id or uuid.uuid4()
    batch.filename = "export.csv"
    batch.parser_used = "partners"
    batch.row_count = 0
    batch.imported_count = 0
    batch.duplicate_count = 0
    batch.status = "processing"
    batch.error_message = None
    batch.imported_at = datetime(2026, 4, 10, 12, 0, 0)
    return batch


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


async def test_start_import_account_not_found(client, mock_db):
    mock_db.get.return_value = None
    async with client as c:
        resp = await c.post(
            "/api/imports",
            data={"account_id": str(uuid.uuid4())},
            files={"file": ("export.csv", b"data", "text/csv")},
        )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Account not found"


async def test_start_import_inactive_account_returns_404(client, mock_db):
    acct = _make_account()
    acct.is_active = False
    mock_db.get.return_value = acct
    async with client as c:
        resp = await c.post(
            "/api/imports",
            data={"account_id": str(acct.id)},
            files={"file": ("export.csv", b"data", "text/csv")},
        )
    assert resp.status_code == 404


async def test_start_import_returns_202(client, mock_db):
    acct = _make_account()
    batch = _make_batch(account_id=acct.id)

    mock_db.get.return_value = acct

    # refresh populates batch.id on the mock
    async def _refresh(obj):
        obj.id = batch.id

    mock_db.refresh.side_effect = _refresh

    with patch("app.api.imports._run_import"):
        async with client as c:
            resp = await c.post(
                "/api/imports",
                data={"account_id": str(acct.id)},
                files={"file": ("export.csv", b"col1\nval1", "text/csv")},
            )

    assert resp.status_code == 202
    body = resp.json()
    assert "batch_id" in body
    assert body["message"] == "Import started"


async def test_list_imports_empty(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/imports")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_imports_with_account_filter(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get(f"/api/imports?account_id={uuid.uuid4()}")
    assert resp.status_code == 200
    assert mock_db.execute.called
    call_arg = mock_db.execute.call_args[0][0]
    assert "account_id" in str(call_arg).lower()


async def test_get_import_batch_not_found(client, mock_db):
    mock_db.get.return_value = None
    async with client as c:
        resp = await c.get(f"/api/imports/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Import batch not found"


async def test_get_import_batch_returns_batch(client, mock_db):
    batch = _make_batch()
    mock_db.get.return_value = batch
    async with client as c:
        resp = await c.get(f"/api/imports/{batch.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(batch.id)
    assert resp.json()["status"] == "processing"


def _make_transaction(batch_id: uuid.UUID, categorization_source: str | None = "rule", is_transfer: bool = False) -> Transaction:
    tx = MagicMock(spec=Transaction)
    tx.id = uuid.uuid4()
    tx.import_batch_id = batch_id
    tx.booking_date = date(2026, 3, 15)
    tx.amount = -500.0
    tx.currency = "CZK"
    tx.counterparty_name = "Lidl"
    tx.counterparty_account = None
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
    assert "is_transfer" not in data[0]


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
    assert "is_transfer" not in data[0]
