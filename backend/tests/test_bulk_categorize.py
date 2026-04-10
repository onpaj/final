import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


async def test_bulk_categorize_happy_path(client, mock_db):
    mock_result = MagicMock()
    mock_db.execute.return_value = mock_result

    transaction_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    category_id = str(uuid.uuid4())

    async with client as c:
        resp = await c.patch(
            "/api/transactions/bulk-categorize",
            json={"transaction_ids": transaction_ids, "category_id": category_id},
        )

    assert resp.status_code == 204
    assert mock_db.execute.called
    assert mock_db.commit.called


async def test_bulk_categorize_empty_transaction_ids_rejected(client, mock_db):
    category_id = str(uuid.uuid4())

    async with client as c:
        resp = await c.patch(
            "/api/transactions/bulk-categorize",
            json={"transaction_ids": [], "category_id": category_id},
        )

    assert resp.status_code == 422
    assert not mock_db.commit.called


async def test_bulk_categorize_missing_category_id_rejected(client, mock_db):
    transaction_ids = [str(uuid.uuid4())]

    async with client as c:
        resp = await c.patch(
            "/api/transactions/bulk-categorize",
            json={"transaction_ids": transaction_ids},
        )

    assert resp.status_code == 422
    assert not mock_db.commit.called
