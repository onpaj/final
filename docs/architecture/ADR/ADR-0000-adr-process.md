# ADR-0000: ADR Process

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

Finance Analyzer will evolve over time. Architectural decisions made during the design phase — and future ones — need to be recorded in a way that makes reasoning transparent and revisitable. Without a lightweight process, decisions get lost in conversation history or chat logs.

## Decision

We use Architecture Decision Records (ADRs) stored as Markdown files in `docs/architecture/ADR/`. Each ADR documents one significant decision using a consistent five-section template.

**Template sections:**

1. **Status** — `Accepted`, `Proposed`, `Superseded by ADR-NNNN`, or `Deprecated`
2. **Context** — The situation and problem that prompted the decision. What forces were at play?
3. **Decision** — What was decided, stated clearly and directly.
4. **Consequences** — What does this decision enable or constrain? What follow-up work does it create?
5. **Alternatives Considered** — Other options evaluated and why they were rejected or deferred.

**Scope:** An ADR is warranted when a decision:
- Is hard to reverse without significant rework, OR
- Involves a meaningful trade-off between viable alternatives, OR
- Will likely be questioned by future contributors (including future Claude sessions)

A decision like "use Pydantic for validation" does not need an ADR. A decision like "Neon instead of SQLite" does.

**Naming:** `ADR-NNNN-short-hyphenated-title.md` (zero-padded four-digit number).

**Index:** `docs/architecture/ADR/README.md` always lists every ADR with status.

## Consequences

- Every significant design decision has a permanent, searchable record.
- New contributors can understand why the system is built the way it is.
- When a decision is reversed, the old ADR is updated to `Superseded by ADR-NNNN` and a new ADR is written. Old ADRs are never deleted.

## Alternatives Considered

- **Inline comments in CLAUDE.md** — convenient, but mixes navigation hints with design rationale; becomes unwieldy as the project grows.
- **GitHub issues/PRs** — decisions documented in discussion threads are hard to find later; not structured.
- **No formal process** — fastest short-term, but creates confusion about intent in a personal project that may be revisited months later.
