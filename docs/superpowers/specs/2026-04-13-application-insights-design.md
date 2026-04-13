# Application Insights Integration — Design Spec

**Date:** 2026-04-13
**Status:** Approved

## Goal

Route Python `logging` output, unhandled exceptions, and HTTP request traces from the FastAPI backend to Azure Application Insights — production only.

## Approach

Use `azure-monitor-opentelemetry` (Microsoft's official OpenTelemetry distro for Azure). A single `configure_azure_monitor()` call auto-instruments:
- FastAPI ASGI layer → HTTP request telemetry
- Python `logging` bridge → trace telemetry (INFO and above)
- Unhandled exceptions → exception telemetry with stack traces

## What Gets Captured

| Telemetry type | Source | App Insights table |
|---|---|---|
| HTTP requests | FastAPI ASGI middleware | `requests` |
| Unhandled exceptions | ASGI error propagation | `exceptions` |
| `logger.exception(...)` calls | logging bridge | `exceptions` + `traces` |
| INFO/WARNING/ERROR log lines | logging bridge | `traces` |

Not captured (intentional): SQLAlchemy query traces, Anthropic API dependency calls.

## Code Changes

### `backend/pyproject.toml`

Add to `dependencies`:
```
azure-monitor-opentelemetry>=1.6.0
```

### `backend/app/config.py`

Add one optional field to `Settings`:
```python
appinsights_connection_string: str = ""
```

### `backend/app/main.py`

Add `setup_telemetry()` called before app construction:

```python
def setup_telemetry():
    if settings.environment == "production" and settings.appinsights_connection_string:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=settings.appinsights_connection_string)
    else:
        import logging
        logging.basicConfig(level=logging.INFO)

setup_telemetry()
app = FastAPI(...)
```

## Environment Variables

| Variable | Value | Where set |
|---|---|---|
| `APPINSIGHTS_CONNECTION_STRING` | `InstrumentationKey=89584153-33bf-4b32-9584-d539fce65efb` | Azure App Service Application Settings (portal) |

The instrumentation key never appears in committed code.

## Behaviour by Environment

| Environment | Telemetry |
|---|---|
| `development` | `logging.basicConfig(INFO)` → stdout only |
| `production` | `configure_azure_monitor()` → App Insights + stdout |

## Files Changed

- `backend/pyproject.toml` — add dependency
- `backend/app/config.py` — add `appinsights_connection_string` field
- `backend/app/main.py` — add `setup_telemetry()` function

No changes to service or router code. Existing `logging.getLogger(__name__)` calls work unchanged.
