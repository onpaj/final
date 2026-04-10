# ADR-0009: Scope — Personal Single-Household, Local v1

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

Finance Analyzer could be designed as a multi-user, cloud-deployed SaaS product, or as a lean personal tool. Scope decisions affect data model complexity, infrastructure requirements, authentication, and how much time is spent on features the sole user doesn't need.

## Decision

**v1 scope:**
- **Single user** — no authentication, no user accounts, no session management.
- **Single household** — all accounts and transactions belong to one logical owner.
- **Local runtime** — the app runs on `localhost`; there is no public URL (see ADR-0001).
- **No auth** — because the app is only accessible on `localhost`, no login screen is needed.
- **No budgeting / forecasting features** — v1 is analytical (look backward at what happened), not prescriptive (set limits, predict future).
- **No recurring transaction management** — subscriptions and recurring bills are not tracked as a separate concept; they appear in analytics naturally.
- **No bill reminders / notifications** — out of scope.

## Consequences

- The data model has no `user_id` foreign key on any table. Adding multi-user support later would require a migration — acceptable given the personal use case.
- No auth middleware, no JWT/session logic, no login UI. Significant complexity eliminated.
- If the app is ever deployed to a server (e.g., Fly.io), auth must be added first. That is explicitly a future concern, not a present one.
- Simpler code means faster development and easier future maintenance by any contributor (or Claude session).

## Alternatives Considered

- **Multi-user from day one** — adds `user_id` to all tables, requires auth (OAuth, JWT, or similar), login UI, and session handling. Wasted work for a single-user tool.
- **Deployed cloud app** — accessible from anywhere; always-on. Requires auth (see above), public-facing server, TLS, and ongoing hosting cost. Not needed for a personal household tool.
- **Business + personal mixed** — separate "entities" (e.g., "Me", "My Company") with per-entity reporting. A valid future need, but introduces complexity (entity model, filtering everywhere). Out of v1 scope; can be introduced as an additive migration.
