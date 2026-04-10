# ADR-0003: LLM Provider — Anthropic Claude

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

LLM-assisted categorization requires a capable language model accessible via API. The primary alternative was OpenAI (which the user had already used in `invoice_categorizer`). The user explicitly requested Anthropic instead.

Two tiers of classification need are anticipated:
- **High-volume routine classification** — most transactions have a clear counterparty and description; cheap models are sufficient.
- **Ambiguous / low-confidence cases** — a small fraction of transactions need a stronger model for better accuracy.

## Decision

**Provider:** Anthropic (Claude API), via the official `anthropic` Python SDK.
**Primary model:** `claude-haiku-4-5` — fast and cheap; used for all initial classification attempts.
**Escalation model:** `claude-sonnet-4-6` — invoked when Haiku returns confidence < 0.7 on a second attempt (single escalation retry).

**Structured output:** The prompt requests a JSON response matching a defined schema: `{"category": string, "confidence": number, "reasoning": string}`. Claude is instructed to use tool use / structured output to ensure parseable responses.

**Audit log:** Every LLM call is recorded in the `llm_classifications` table: model, tokens used, confidence, reasoning. This enables cost monitoring and retrospective review of categorization quality.

## Consequences

- Anthropic API key must be set in `.env` (`ANTHROPIC_API_KEY`). App will not start without it.
- Transaction data (counterparty, description, amount — but NOT account numbers) is sent to Anthropic's API. See ADR-0008 for privacy posture.
- Anthropic's API has no model training on API data by default, which mitigates privacy concerns for financial data.
- Two-tier (Haiku → Sonnet) model routing keeps costs low while allowing accuracy escalation. The cost per escalation is ~10x higher than Haiku; this should affect only a small minority of transactions.
- The `llm_classifications` audit log gives the user visibility into how much is being spent and which transactions were hard to classify.

## Alternatives Considered

- **OpenAI GPT-4o-mini / GPT-4** — Functionally equivalent. The user switched from OpenAI (`invoice_categorizer`) to Anthropic for this project. OpenAI is a drop-in alternative if needed.
- **Local LLM (Ollama + Mistral / Llama)** — Fully private; no API cost. Classification quality for structured output is weaker on typical consumer hardware. Viable if privacy requirements change; the `anthropic_client.py` wrapper would be the only thing to swap.
- **No LLM (rules only)** — See ADR-0004. Chosen against because bootstrapping a complete rule set is time-consuming and new payees constantly appear.
