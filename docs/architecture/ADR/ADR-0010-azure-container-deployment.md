# ADR-0010: Azure Container Web App Deployment

**Status:** Accepted  
**Date:** 2026-04-12

## Context

FinAl is complete (M1–M5). The application needs to move from a localhost-only tool to a cloud-hosted instance accessible remotely, with authentication to protect personal financial data.

ADR-0001 deferred containerization to deployment time ("If the app is ever deployed to a server, containerization should be added at that point"). ADR-0009 noted that authentication must be added before any deployment. Both conditions are now being addressed.

## Decision

### Single-container deployment

FastAPI serves both the API (at `/api/*`) and the pre-built React frontend (as static files mounted at `/`). A multi-stage Dockerfile builds the frontend in Node and runs everything from a single Python container.

**Rationale:** Avoids needing a reverse proxy (nginx) or multi-container orchestration. One App Service, one container, one port.

### Docker Hub as container registry

Docker Hub stores the built images. GitHub Actions builds and pushes on each merge to `main`.

**Rationale:** No additional Azure resource to manage. Docker Hub is sufficient for a single-user project.

### Azure Container Web App (App Service)

Deployed to an existing Azure App Service Plan. Azure App Service pulls the container image from Docker Hub on each deployment.

### Entra ID via Easy Auth

Authentication is handled entirely at the Azure infrastructure level using App Service Authentication (Easy Auth) with Entra ID as the provider. All unauthenticated requests are redirected to Microsoft login.

**Rationale:** Zero code changes in the application. Meets ADR-0009's requirement that auth be added before deployment. Can be scoped to a specific Entra ID tenant.

### Azure Blob Storage for uploads

CSV files uploaded by the user are stored in Azure Blob Storage instead of the local filesystem. A local filesystem fallback is used in development (when no connection string is configured).

**Rationale:** Container filesystem is ephemeral; uploads must survive restarts. Blob Storage is the appropriate Azure primitive.

### Alembic migrations at container startup

The container's startup script runs `alembic upgrade head` before starting uvicorn.

**Rationale:** Acceptable for single-instance deployment. If the app is ever scaled to multiple instances, a separate migration step in CI/CD should be introduced.

### GitHub Actions CI/CD

On push to `main`: run backend tests (against a real Postgres service container) + frontend type-check → build and push Docker image → deploy to Azure.

## Consequences

- Local development is unchanged: two terminals, `uvicorn --reload` + `npm run dev` with Vite proxy
- Frontend API calls use relative `/api/*` paths (no hardcoded host)
- CORS middleware is only active in `development` environment; in production, same-origin requests need no CORS
- `azure-storage-blob` SDK is added as a backend dependency
- Four GitHub Secrets required: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `AZURE_WEBAPP_NAME`, `AZURE_CREDENTIALS` (service principal JSON)
