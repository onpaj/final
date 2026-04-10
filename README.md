# Finance Analyzer

A personal local web application for analyzing household finances across multiple bank accounts.

**Status: Design phase — no code yet.**

---

## What It Does

- Imports CSV exports from multiple Czech bank accounts (Partners Bank natively; any bank via a configurable CSV mapper)
- Categorizes transactions automatically: user-defined rules first, Claude AI (Anthropic) for the rest
- Detects and excludes internal transfers between your own accounts
- Shows monthly spend by category, trends over time, income vs. expenses, savings rate, and anomaly alerts

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/overview.md`](docs/overview.md) | Full description, goals, non-goals, open questions |
| [`docs/architecture.md`](docs/architecture.md) | Component diagram, services, request flows |
| [`docs/data-model.md`](docs/data-model.md) | Database tables and relationships |
| [`docs/pipelines.md`](docs/pipelines.md) | Import, categorization, transfer detection pipelines |
| [`docs/roadmap.md`](docs/roadmap.md) | Milestones M1–M5 with acceptance criteria |
| [`docs/glossary.md`](docs/glossary.md) | Term definitions |
| [`docs/architecture/ADR/`](docs/architecture/ADR/README.md) | Architecture Decision Records |

## Stack

Python · FastAPI · React · TypeScript · Neon Postgres · Anthropic Claude

## Contributing / Developing

See [`CLAUDE.md`](CLAUDE.md) for context, setup instructions, and coding conventions.

> Before starting implementation: a real **Partners Bank CSV export** is needed to build the primary bank parser. Place it in `sample_data/` (gitignored).
