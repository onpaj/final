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
