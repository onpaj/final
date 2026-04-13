from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from alembic.config import Config
    from alembic import command
    import asyncio

    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
    yield


app = FastAPI(title="Finance Analyzer", version="0.1.0", lifespan=lifespan)

if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

from app.api import accounts, imports, transactions, categories, rules, categorization, analytics
from app.api import settings as settings_router

app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(categorization.router, prefix="/api/categorize", tags=["categorization"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])

# Serve frontend static files in production
static_dir = Path(__file__).parent.parent / "static"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
