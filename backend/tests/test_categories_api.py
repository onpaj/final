import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_create_group(client):
    resp = await client.post("/api/categories/groups", json={"name": "Living", "color": "#6366f1"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Living"
    assert data["color"] == "#6366f1"
    assert "id" in data


async def test_update_group(client):
    create = await client.post("/api/categories/groups", json={"name": "Old Group"})
    group_id = create.json()["id"]
    resp = await client.patch(f"/api/categories/groups/{group_id}", json={"name": "New Group"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Group"


async def test_delete_group(client):
    create = await client.post("/api/categories/groups", json={"name": "ToDelete"})
    group_id = create.json()["id"]
    resp = await client.delete(f"/api/categories/groups/{group_id}")
    assert resp.status_code == 204


async def test_create_category(client):
    group = await client.post("/api/categories/groups", json={"name": "Food"})
    group_id = group.json()["id"]
    resp = await client.post("/api/categories", json={
        "group_id": group_id,
        "name": "Groceries",
        "color": "#22c55e",
        "is_income": False,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Groceries"
    assert data["group_id"] == group_id


async def test_update_category(client):
    group = await client.post("/api/categories/groups", json={"name": "G"})
    group_id = group.json()["id"]
    cat = await client.post("/api/categories", json={"group_id": group_id, "name": "Old"})
    cat_id = cat.json()["id"]
    resp = await client.patch(f"/api/categories/{cat_id}", json={"name": "New", "color": "#ff0000"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"
    assert resp.json()["color"] == "#ff0000"


async def test_delete_category(client):
    group = await client.post("/api/categories/groups", json={"name": "G2"})
    group_id = group.json()["id"]
    cat = await client.post("/api/categories", json={"group_id": group_id, "name": "ToDelete"})
    cat_id = cat.json()["id"]
    resp = await client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 204


async def test_reorder_groups(client):
    g1 = (await client.post("/api/categories/groups", json={"name": "G1"})).json()
    g2 = (await client.post("/api/categories/groups", json={"name": "G2"})).json()
    resp = await client.patch("/api/categories/groups/reorder", json=[
        {"id": g1["id"], "sort_order": 1},
        {"id": g2["id"], "sort_order": 0},
    ])
    assert resp.status_code == 200


async def test_reorder_categories(client):
    group = (await client.post("/api/categories/groups", json={"name": "G"})).json()
    c1 = (await client.post("/api/categories", json={"group_id": group["id"], "name": "C1"})).json()
    c2 = (await client.post("/api/categories", json={"group_id": group["id"], "name": "C2"})).json()
    resp = await client.patch("/api/categories/reorder", json=[
        {"id": c1["id"], "sort_order": 1},
        {"id": c2["id"], "sort_order": 0},
    ])
    assert resp.status_code == 200


async def test_update_nonexistent_group_returns_404(client):
    import uuid
    resp = await client.patch(f"/api/categories/groups/{uuid.uuid4()}", json={"name": "X"})
    assert resp.status_code == 404


async def test_update_nonexistent_category_returns_404(client):
    import uuid
    resp = await client.patch(f"/api/categories/{uuid.uuid4()}", json={"name": "X"})
    assert resp.status_code == 404
