# ADR-0001: Form Factor and Tech Stack

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

Finance Analyzer needs to ingest bank exports, categorize transactions, and present analytics. Multiple interaction patterns were viable: command-line scripts, a local web app, a desktop app, or a REST API service. The choice heavily influences the developer experience, the UI richness possible, and how the system grows.

The user has prior Python experience (FastAPI, OpenAI SDK) from the `invoice_categorizer` project, and is comfortable with local development but prefers not to run Docker for a personal tool.

## Decision

**Form factor:** Local web app running on `localhost`.
**Backend:** Python with FastAPI, running via `uvicorn` in a local Python virtual environment.
**Frontend:** React with TypeScript, built with Vite, served by the Vite dev server during development. Charts via Recharts; styling via Tailwind CSS.
**Runtime:** No Docker. Two terminals: one for `uvicorn`, one for `npm run dev`. A future `start.sh` script can launch both.

## Consequences

- The browser UI enables interactive re-categorization, drag-and-drop import, and charts — impossible with a CLI.
- FastAPI aligns with existing developer knowledge; no new backend paradigm to learn.
- React + Vite requires Node.js and `npm` on the developer machine. This is a one-time setup cost.
- Running without Docker means the developer manages their own Python venv and Node version. Acceptable for a single-developer personal tool.
- If the app is ever deployed to a server, containerization should be added at that point (covered by ADR-0009 which scopes v1 to local use).

## Alternatives Considered

- **CLI / scripts** — No UI; re-categorization and rule editing would require editing config files. Not suitable for regular monthly use.
- **Streamlit (pure Python)** — Fastest to prototype, but UI control is limited and charts are less interactive. Becomes constraining for a long-term tool.
- **Desktop app (Electron / Tauri)** — Richer native features, but high setup complexity and no benefit over a local web app for this use case.
- **FastAPI + Jinja2/HTMX** — No Node build step. Simpler to run, but chart libraries for server-rendered HTML are weaker. React was preferred for the analytics views.
- **.NET / C# backend** — User has .NET experience (Anela.Heblo projects) but the LLM integration and data science ecosystem is stronger in Python. The `invoice_categorizer` precedent also points to Python.
