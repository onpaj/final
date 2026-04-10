# ADR-0002: Database — Neon Serverless Postgres

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

Finance Analyzer needs persistent storage for accounts, transactions, rules, categories, and LLM audit logs. A personal tool running locally has modest data volumes (thousands of transactions per year), but the data must survive machine restarts and be queryable for analytics.

Several storage options were evaluated: SQLite, a locally-run Postgres in Docker, plain files, and cloud-hosted Postgres.

## Decision

**Database:** [Neon](https://neon.tech) — serverless Postgres, hosted in the cloud.
**Driver:** `asyncpg` (async Postgres driver).
**ORM / query builder:** SQLAlchemy (async mode) for model definitions and migrations.
**Migrations:** Alembic (pairs with SQLAlchemy).
**Connection:** via `DATABASE_URL` environment variable containing the Neon connection string.

## Consequences

- Data lives in the cloud (Neon), while the app runs locally. This means an internet connection is required when the app is running.
- Financial transaction data (amounts, counterparty names, descriptions) is stored on Neon's infrastructure. This is an accepted trade-off by the user.
- Neon's free tier supports the expected data volume (personal household transactions) without cost.
- Alembic migrations provide a versioned schema history, making future schema changes safe.
- Because the database is external, the app has no local data file to back up or lose — Neon manages durability.
- If Neon ever becomes unavailable or the free tier is discontinued, migrating to a self-hosted Postgres is straightforward (change `DATABASE_URL`; run `alembic upgrade head` on the new host).

## Alternatives Considered

- **SQLite (local file)** — Zero infrastructure; single-file backup. Would have been the recommended default, but the user explicitly chose Neon. SQLite remains a viable fallback if Neon proves inconvenient.
- **PostgreSQL in Docker** — Full Postgres locally without data leaving the machine, but requires running a Docker daemon for a personal tool. User prefers no Docker (see ADR-0001).
- **Plain files (JSON / Parquet)** — Simple but poor for relational queries, aggregations, and concurrent UI operations. Not suitable beyond scripts.
