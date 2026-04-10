import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Transaction
from app.db.session import get_db
from app.main import app


def _make_transaction(account_id: uuid.UUID | None = None) -> Transaction:
    tx = MagicMock(spec=Transaction)
    tx.id = uuid.uuid4()
    tx.account_id = account_id or uuid.uuid4()
    tx.import_batch_id = uuid.uuid4()
    tx.booking_date = date(2026, 1, 15)
    tx.value_date = None
    tx.amount = Decimal("-250.00")
    tx.currency = "CZK"
    tx.counterparty_name = "ALBERT"
    tx.counterparty_account = None
    tx.description = "Nákup"
    tx.category_id = None
    tx.categorization_source = None
    tx.confidence = None
    tx.is_transfer = False
    tx.notes = None
    tx.created_at = datetime(2026, 1, 15, 10, 0, 0)
    return tx


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


async def test_list_transactions_empty(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_transactions_returns_items(client, mock_db):
    tx = _make_transaction()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tx]
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["currency"] == "CZK"


async def test_list_transactions_with_account_filter(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    account_id = uuid.uuid4()
    async with client as c:
        resp = await c.get(f"/api/transactions?account_id={account_id}")
    assert resp.status_code == 200
    assert mock_db.execute.called


async def test_list_transactions_with_date_range(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?date_from=2026-01-01&date_to=2026-01-31")
    assert resp.status_code == 200


async def test_list_transactions_needs_review_filter(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true")
    assert resp.status_code == 200
    assert mock_db.execute.called


async def test_list_transactions_is_transfer_filter(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?is_transfer=false")
    assert resp.status_code == 200


async def test_list_transactions_limit_capped_at_500(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?limit=501")
    assert resp.status_code == 422  # FastAPI validation error


async def test_list_transactions_negative_offset_rejected(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?offset=-1")
    assert resp.status_code == 422
