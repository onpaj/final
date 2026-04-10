# Finance Analyzer

A personal local web application for analyzing household finances across multiple bank accounts.

## What It Does

- **Imports CSV exports** from multiple Czech bank accounts (Partners Bank natively; any bank via a configurable CSV mapper)
- **Categorizes transactions** automatically: user-defined rules first, Claude AI (Anthropic) for unmatched transactions
- **Detects and excludes** internal transfers between your own accounts
- **Analytics dashboard** showing monthly spend by category, trends over time, income vs. expenses, savings rate, and anomaly alerts

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
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

The web app will be available at `http://localhost:5173`.

## First Use

1. **Add an account** → Go to Settings, click "Add Account", enter the name (e.g., "Main Checking")
2. **Upload a CSV file** → Go to Imports, select account and CSV file, click Upload
3. **Wait for processing** → The import pipeline categorizes transactions and detects transfers
4. **View analytics** → Go to Analytics to see your spending by category, trends, and savings rate

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, uvicorn |
| **ORM** | SQLAlchemy (async), Alembic migrations |
| **Database** | Neon (serverless Postgres) |
| **Database driver** | asyncpg |
| **LLM** | Anthropic Claude (`claude-haiku-4-5` default, `claude-sonnet-4-6` for escalation) |
| **Frontend** | React 19, TypeScript, Vite, TanStack Query, Recharts, Tailwind CSS |

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

Not yet implemented. See [`docs/roadmap.md`](docs/roadmap.md) for post-M5 milestones.

## License

[Add your license here]
