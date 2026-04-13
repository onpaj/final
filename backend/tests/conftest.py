import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import event
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import get_db, engine


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
