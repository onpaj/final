import os
import re
from pathlib import Path

# Load .env.test into the environment before any app module is imported,
# so that Settings() picks up the test database URL instead of .env.
_env_test = Path(__file__).parent.parent / ".env.test"
for _line in _env_test.read_text().splitlines():
    _line = _line.strip()
    if not _line or _line.startswith("#"):
        continue
    _m = re.match(r"^([A-Z_]+)\s*=\s*(.*)$", _line)
    if _m:
        os.environ[_m.group(1)] = _m.group(2).strip()

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import event
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.db.session import get_db, engine
from app.db.models import Base

if "neon.tech" in settings.database_url or "azure.com" in settings.database_url:
    raise RuntimeError(
        "Tests must not run against a cloud database. "
        "Set DATABASE_URL in .env.test to a local/dockerized Postgres instance."
    )


@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()  # outermost savepoint

        session = AsyncSession(bind=conn, expire_on_commit=False)

        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(sess, transaction):
            # After each commit (which releases the savepoint), start a new one
            # so subsequent operations still sit inside our outer transaction.
            if transaction.nested and not transaction._parent.nested:
                sess.begin_nested()

        yield session

        await session.close()
        await conn.rollback()


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
