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
    tx.notes = None
    tx.created_at = datetime(2026, 1, 15, 10, 0, 0)
    tx.raw_reference = None
    tx.applied_rule_id = None
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
    call_arg = mock_db.execute.call_args[0][0]
    assert "account_id" in str(call_arg).lower()


async def test_list_transactions_with_date_range(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?date_from=2026-01-01&date_to=2026-01-31")
    assert resp.status_code == 200
    call_arg = mock_db.execute.call_args[0][0]
    query_str = str(call_arg).lower()
    assert "booking_date" in query_str


async def test_list_transactions_needs_review_filter(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true")
    assert resp.status_code == 200
    assert mock_db.execute.called
    call_arg = mock_db.execute.call_args[0][0]
    query_str = str(call_arg).lower()
    assert "category_id" in query_str
    assert "categorization_source" in query_str


async def test_list_transactions_categorization_source_filter(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?categorization_source=transfer")
    assert resp.status_code == 200
    call_arg = mock_db.execute.call_args[0][0]
    assert "categorization_source" in str(call_arg).lower()


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


async def test_include_llm_status_no_classification(client, mock_db):
    """Transaction with no LlmClassification row → llm_status='no_rule_no_llm'."""
    tx = _make_transaction()
    # First execute call → transaction list; second → llm classifications (empty)
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]
    mock_db.execute.side_effect = [tx_result, empty_result]

    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true&include_llm_status=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["llm_status"] == "no_rule_no_llm"
    assert data[0]["llm_confidence"] is None


async def test_include_llm_status_llm_error(client, mock_db):
    """Transaction with LlmClassification reasoning='error' → llm_status='llm_error'."""
    tx = _make_transaction()
    cls = MagicMock()
    cls.transaction_id = tx.id
    cls.accepted = False
    cls.confidence = None
    cls.reasoning = "error"

    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]
    cls_result = MagicMock()
    cls_result.scalars.return_value.all.return_value = [cls]
    mock_db.execute.side_effect = [tx_result, cls_result]

    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true&include_llm_status=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["llm_status"] == "llm_error"


async def test_include_llm_status_llm_rejected(client, mock_db):
    """Transaction with LlmClassification accepted=False, confidence set → llm_status='llm_rejected'."""
    tx = _make_transaction()
    cls = MagicMock()
    cls.transaction_id = tx.id
    cls.accepted = False
    cls.confidence = Decimal("0.38")
    cls.reasoning = "Low confidence"

    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]
    cls_result = MagicMock()
    cls_result.scalars.return_value.all.return_value = [cls]
    mock_db.execute.side_effect = [tx_result, cls_result]

    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true&include_llm_status=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["llm_status"] == "llm_rejected"
    assert abs(float(data[0]["llm_confidence"]) - 0.38) < 0.01


async def test_include_llm_status_false_by_default(client, mock_db):
    """Without include_llm_status, only one DB execute call is made and llm_status is None."""
    tx = _make_transaction()
    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]
    mock_db.execute.return_value = tx_result

    async with client as c:
        resp = await c.get("/api/transactions")
    assert resp.status_code == 200
    assert mock_db.execute.call_count == 1
    assert resp.json()[0]["llm_status"] is None


def _make_account(account_id: uuid.UUID | None = None) -> MagicMock:
    from app.db.models import Account as AccountModel
    acc = MagicMock(spec=AccountModel)
    acc.id = account_id or uuid.uuid4()
    acc.name = "My Account"
    acc.iban = "CZ6508000000192000145399"
    return acc


async def test_get_transaction_details_not_found(client, mock_db):
    empty_result = MagicMock()
    empty_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = empty_result
    async with client as c:
        resp = await c.get(f"/api/transactions/{uuid.uuid4()}/details")
    assert resp.status_code == 404


async def test_get_transaction_details_basic(client, mock_db):
    tx = _make_transaction()
    tx.value_date = None
    tx.transfer_pair_id = None
    tx.category_id = None
    acc = _make_account(tx.account_id)

    tx_result = MagicMock()
    tx_result.scalars.return_value.first.return_value = tx
    acc_result = MagicMock()
    acc_result.scalars.return_value.first.return_value = acc

    mock_db.execute.side_effect = [tx_result, acc_result]

    async with client as c:
        resp = await c.get(f"/api/transactions/{tx.id}/details")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(tx.id)
    assert data["account"]["name"] == "My Account"
    assert data["category"] is None
    assert data["applied_rule"] is None
    assert data["transfer_pair"] is None


async def test_get_transaction_details_with_transfer_pair(client, mock_db):
    tx = _make_transaction()
    tx.value_date = None
    tx.categorization_source = "transfer"
    pair_id = uuid.uuid4()
    tx.transfer_pair_id = pair_id
    tx.category_id = None

    pair_tx = _make_transaction()
    pair_tx.id = pair_id
    pair_account = _make_account()

    tx_result = MagicMock()
    tx_result.scalars.return_value.first.return_value = tx
    acc_result = MagicMock()
    acc_result.scalars.return_value.first.return_value = _make_account(tx.account_id)
    pair_tx_result = MagicMock()
    pair_tx_result.scalars.return_value.first.return_value = pair_tx
    pair_acc_result = MagicMock()
    pair_acc_result.scalars.return_value.first.return_value = pair_account

    mock_db.execute.side_effect = [tx_result, acc_result, pair_tx_result, pair_acc_result]

    async with client as c:
        resp = await c.get(f"/api/transactions/{tx.id}/details")
    assert resp.status_code == 200
    data = resp.json()
    assert data["transfer_pair"] is not None
    assert data["transfer_pair"]["account"]["name"] == "My Account"


async def test_needs_review_excludes_transfers(client, mock_db):
    """needs_review=true excludes transactions with categorization_source='transfer'."""
    tx_transfer = _make_transaction()
    tx_transfer.categorization_source = "transfer"
    tx_uncategorized = _make_transaction()
    tx_uncategorized.categorization_source = None

    # Both have no category_id; only tx_uncategorized should appear in needs_review
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tx_uncategorized]
    mock_db.execute.return_value = mock_result

    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    # The transfer tx must not appear; the uncategorized one must
    ids = [d["id"] for d in data]
    assert str(tx_uncategorized.id) in ids


async def test_list_transactions_categorization_source_none_filters_null(client, mock_db):
    """categorization_source=none returns transactions WHERE categorization_source IS NULL."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?categorization_source=none")
    assert resp.status_code == 200
    call_arg = mock_db.execute.call_args[0][0]
    query_str = str(call_arg).lower()
    # IS NULL, not equality
    assert "is null" in query_str or "isnull" in query_str or "is_(none)" in query_str.replace(" ", "")
