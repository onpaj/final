# ADR-0008: LLM Privacy Posture

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

Classifying transactions via an external LLM API means sending some financial data to a third-party server (Anthropic). The question is how much data to include in each classification request. More context gives the LLM better signals for accurate categorization; less context reduces privacy exposure.

Financial data in transactions includes: counterparty name, description/note, amount, date, and account/IBAN numbers.

## Decision

**What is sent to the Anthropic API:**
- Counterparty name (e.g., `ALBERT CZ s.r.o.`)
- Transaction description / reference text
- Amount and currency (e.g., `450 CZK`)
- Booking date (for seasonal context, e.g., annual insurance)

**What is never sent:**
- Account numbers or IBANs
- Bank codes or sort codes
- Any internal IDs from Finance Analyzer

**Rationale for including amount:** Amount is a strong classification signal. A 15,000 CZK debit is almost certainly rent; a 120 CZK debit from the same counterparty might be a parking fee. Excluding amount meaningfully reduces accuracy.

**Anthropic API data policy:** Anthropic does not train models on API-submitted data by default. API usage is subject to Anthropic's data processing agreement.

## Consequences

- Counterparty names and amounts reach Anthropic's API servers. Users should be aware their transaction data is not purely local.
- Account numbers (the most sensitive identifiers) never leave the local machine or Neon database.
- The privacy posture is explicitly documented here; the user knowingly accepted this trade-off.
- If the user later decides this is too much exposure, the fallback is to run with rules-only mode (`ANTHROPIC_API_KEY` unset) or replace `anthropic_client.py` with a local LLM adapter.

## Alternatives Considered

- **Counterparty + description only (no amount)** — Reduces one data point but classification accuracy drops noticeably. Not chosen.
- **Redacted / hashed counterparty** — Maximally private, but the LLM loses its primary classification signal. Classification quality would be poor. Not chosen.
- **Local LLM (Ollama)** — Fully private; nothing leaves the machine. Classification accuracy on mid-range hardware is lower, and setup is significantly more complex. Viable future alternative; the `anthropic_client.py` module is the only integration point to swap.
