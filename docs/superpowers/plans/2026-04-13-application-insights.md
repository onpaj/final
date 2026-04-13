# Application Insights Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route FastAPI logs, exceptions, and HTTP request traces to Azure Application Insights in production using `azure-monitor-opentelemetry`.

**Architecture:** `setup_telemetry()` is called once at module level in `main.py` before the FastAPI app is constructed. In production it calls `configure_azure_monitor()` which auto-instruments the ASGI layer and Python logging. In development it falls back to `logging.basicConfig`. Configuration is driven by a new `appinsights_connection_string` field in `Settings`.

**Tech Stack:** `azure-monitor-opentelemetry>=1.6.0`, Python `logging`, FastAPI/uvicorn

---

## File Map

| File | Change |
|---|---|
| `backend/pyproject.toml` | Add `azure-monitor-opentelemetry>=1.6.0` to dependencies |
| `backend/app/config.py` | Add `appinsights_connection_string: str = ""` to `Settings` |
| `backend/app/main.py` | Add `setup_telemetry()` function, call it before `app = FastAPI(...)` |
| `backend/tests/test_telemetry.py` | New: unit tests for `setup_telemetry()` branching logic |

---

### Task 1: Add dependency and config field

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add the package to pyproject.toml**

Open `backend/pyproject.toml`. In the `dependencies` list, add after `azure-storage-blob`:

```toml
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.13.0",
    "asyncpg>=0.29.0",
    "pydantic-settings>=2.4.0",
    "python-multipart>=0.0.9",
    "anthropic>=0.28.0",
    "azure-storage-blob>=12.0.0",
    "azure-monitor-opentelemetry>=1.6.0",
]
```

- [ ] **Step 2: Add config field**

Open `backend/app/config.py`. Add `appinsights_connection_string` to `Settings`:

```python
class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"  # "development" | "production"
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "uploads"
    appinsights_connection_string: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
```

- [ ] **Step 3: Install the new dependency**

```bash
cd backend
pip install -e ".[test]"
```

Expected: package resolves and installs without errors. `azure-monitor-opentelemetry` and its OTel transitive deps appear in the output.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/app/config.py
git commit -m "feat: add azure-monitor-opentelemetry dependency and appinsights config field"
```

---

### Task 2: Write failing tests for setup_telemetry()

**Files:**
- Create: `backend/tests/test_telemetry.py`

- [ ] **Step 1: Create the test file**

```python
# backend/tests/test_telemetry.py
from unittest.mock import patch, MagicMock
import logging


def test_setup_telemetry_calls_configure_azure_monitor_in_production():
    mock_configure = MagicMock()
    with (
        patch("app.main.settings") as mock_settings,
        patch.dict("sys.modules", {"azure.monitor.opentelemetry": MagicMock(configure_azure_monitor=mock_configure)}),
    ):
        mock_settings.environment = "production"
        mock_settings.appinsights_connection_string = "InstrumentationKey=test-key"

        from app.main import setup_telemetry
        setup_telemetry()

    mock_configure.assert_called_once_with(connection_string="InstrumentationKey=test-key")


def test_setup_telemetry_uses_basicconfig_in_development():
    with (
        patch("app.main.settings") as mock_settings,
        patch("logging.basicConfig") as mock_basicconfig,
    ):
        mock_settings.environment = "development"
        mock_settings.appinsights_connection_string = ""

        from app.main import setup_telemetry
        setup_telemetry()

    mock_basicconfig.assert_called_once_with(level=logging.INFO)


def test_setup_telemetry_uses_basicconfig_when_connection_string_missing():
    with (
        patch("app.main.settings") as mock_settings,
        patch("logging.basicConfig") as mock_basicconfig,
    ):
        mock_settings.environment = "production"
        mock_settings.appinsights_connection_string = ""

        from app.main import setup_telemetry
        setup_telemetry()

    mock_basicconfig.assert_called_once_with(level=logging.INFO)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_telemetry.py -v
```

Expected: `ImportError` or `AttributeError` — `setup_telemetry` doesn't exist yet.

---

### Task 3: Implement setup_telemetry() in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add setup_telemetry() and call it before app construction**

Replace the contents of `backend/app/main.py` with:

```python
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings


def setup_telemetry():
    if settings.environment == "production" and settings.appinsights_connection_string:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=settings.appinsights_connection_string)
    else:
        logging.basicConfig(level=logging.INFO)


setup_telemetry()


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
```

- [ ] **Step 2: Run the telemetry tests**

```bash
cd backend
pytest tests/test_telemetry.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 3: Run the full test suite to verify no regressions**

```bash
cd backend
pytest tests/ -x -q
```

Expected: all tests PASS (same count as before this task).

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py backend/tests/test_telemetry.py
git commit -m "feat: add Application Insights telemetry via azure-monitor-opentelemetry"
```

---

### Task 4: Configure Azure App Service environment variable

This task is manual — no code changes.

- [ ] **Step 1: Add the Application Setting in Azure portal**

Navigate to: **Azure Portal → App Service (`<your-app-name>`) → Configuration → Application settings**

Add a new setting:
- **Name:** `APPINSIGHTS_CONNECTION_STRING`
- **Value:** `InstrumentationKey=89584153-33bf-4b32-9584-d539fce65efb`

Click **Save** and confirm the restart.

- [ ] **Step 2: Verify telemetry arrives in App Insights**

After the next deployment, navigate to **Application Insights → Live Metrics** and make a request to the app. You should see:
- Incoming request in the **Requests** stream
- No exceptions (assuming a healthy request)

To verify logs: go to **Logs → traces** and run:
```kusto
traces
| order by timestamp desc
| take 20
```

You should see log lines from the app (INFO level and above).
