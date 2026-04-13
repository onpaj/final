# Finance Analyzer

A personal local web application for analyzing household finances across multiple bank accounts.

## What It Does

- **Imports CSV exports** from multiple Czech bank accounts (Partners Bank natively; any bank via a configurable CSV mapper)
- **Categorizes transactions** automatically: user-defined rules first, Claude AI (Anthropic) for unmatched transactions, with manual review for remaining
- **Detects and excludes** internal transfers between your own accounts
- **Analytics dashboard** showing monthly spend by category, trends over time, income vs. expenses, savings rate, and anomaly alerts
- **Rule management** — create, prioritize, and test keyword/regex/amount-range rules
- **Category management** — organize categories into groups with color coding and custom ordering

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Neon Postgres account** ([free tier](https://neon.tech) works fine)
- **Anthropic API key** ([get one here](https://console.anthropic.com/))

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/FinAl.git
cd FinAl
```

### 2. Backend setup

```bash
cd backend

# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies (including test extras)
pip install -e ".[test]"

# Create .env from template and fill in your credentials
cp .env.example .env
# Edit .env and add:
#   - DATABASE_URL from Neon console
#   - ANTHROPIC_API_KEY from Anthropic console

# Run migrations
alembic upgrade head

# (Optional) Seed database with starter categories
python -m app.db.seed
```

### 3. Frontend setup

```bash
cd ../frontend

# Install dependencies
npm install
```

## Running the Application

**Terminal 1 — Backend:**

```bash
cd backend
source .venv/bin/activate  # Activate venv if not already active
uvicorn app.main:app --reload --port 8300
```

The API will be available at `http://localhost:8300`.

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

The web app will be available at `http://localhost:5173`.

## First Use

1. **Add an account** → Go to Settings, click "Add Account", enter the name (e.g., "Main Checking")
2. **Upload a CSV file** → Go to Imports, select account and CSV file, click Upload
3. **Wait for processing** → The import pipeline categorizes transactions and detects transfers automatically
4. **Review uncategorized** → Go to Review to manually categorize any transactions the rules and AI couldn't match
5. **View analytics** → Go to Analytics to see your spending by category, trends, and savings rate

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, uvicorn |
| **ORM** | SQLAlchemy (async), Alembic migrations |
| **Database** | Neon (serverless Postgres) |
| **Database driver** | asyncpg |
| **LLM** | Anthropic Claude (`claude-haiku-4-5` default, `claude-sonnet-4-6` for escalation) |
| **Frontend** | React 19, TypeScript, Vite, TanStack Query v5, Recharts, Tailwind CSS |
| **Routing** | React Router v7 |
| **i18n** | i18next (Czech + English) |
| **Drag & drop** | DnD Kit |

## Documentation

For developers, designers, and maintainers:

| Document | Description |
|----------|-------------|
| [`docs/overview.md`](docs/overview.md) | Full description, goals, non-goals, open questions |
| [`docs/architecture.md`](docs/architecture.md) | Component diagram, services, request flows |
| [`docs/data-model.md`](docs/data-model.md) | Database tables and relationships |
| [`docs/pipelines.md`](docs/pipelines.md) | Import, categorization, transfer detection pipelines |
| [`docs/roadmap.md`](docs/roadmap.md) | Milestones M1–M5 with acceptance criteria |
| [`docs/glossary.md`](docs/glossary.md) | Term definitions |
| [`docs/architecture/ADR/`](docs/architecture/ADR/README.md) | Architecture Decision Records |

## Development

See [`CLAUDE.md`](CLAUDE.md) for context, coding conventions, and project structure.

### Running Tests

```bash
cd backend
pytest
```

### Building for Production

A multi-stage Docker image builds the frontend and serves it alongside the API:

```bash
docker build -t final-app .
docker run -p 8300:8300 \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e ENVIRONMENT=production \
  final-app
```

App available at `http://localhost:8300`.

### CI/CD — GitHub Actions

The workflow in `.github/workflows/deploy.yml` runs on every push to `main`:
1. Runs backend tests against a real Postgres container
2. Type-checks and builds the frontend
3. Builds and pushes a Docker image to Docker Hub
4. Deploys the image to Azure Container Web App

#### Required GitHub Secrets

Add these under **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | How to get it |
|--------|---------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub → Account Settings → Personal access tokens → Generate new token |
| `AZURE_WEBAPP_NAME` | The name of your Azure Web App resource (e.g. `my-final-app`) |
| `AZURE_CREDENTIALS` | Output of `az ad sp create-for-rbac --name "final-github-deploy" --role contributor --scopes /subscriptions/<SUB_ID>/resourceGroups/<RG>/providers/Microsoft.Web/sites/<APP_NAME> --json-auth` |

#### Azure App Service — Application Settings

In Azure Portal → Web App → **Configuration → Application settings**, add:

| Setting | Value |
|---------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` (from Neon) |
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `ENVIRONMENT` | `production` |
| `AZURE_STORAGE_CONNECTION_STRING` | Storage account connection string (from Azure Portal → Storage account → Access keys) |
| `AZURE_STORAGE_CONTAINER` | `uploads` |
| `WEBSITES_PORT` | `8300` |

#### Azure Blob Storage — one-time setup

Create a storage account and container for uploaded CSVs:

```bash
az storage account create -n <storage-name> -g <resource-group> --sku Standard_LRS
az storage container create -n uploads --account-name <storage-name>
```

#### Entra ID Authentication (Easy Auth)

1. **Register an App** in [Azure Portal → Entra ID → App Registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps):
   - Redirect URI: `https://<webapp-name>.azurewebsites.net/.auth/login/aad/callback`
   - Supported account types: *Accounts in this organizational directory only* (single tenant)
2. **Enable Authentication** on the Web App:
   - Azure Portal → Web App → **Authentication → Add identity provider**
   - Choose **Microsoft**, paste in the **Application (client) ID** from step 1
   - Set unauthenticated requests to **HTTP 302 Redirect to login page**

No code changes are needed — authentication is enforced at the Azure infrastructure level.

## License

[Add your license here]
