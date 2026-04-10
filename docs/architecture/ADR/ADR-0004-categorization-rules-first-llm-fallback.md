# ADR-0004: Categorization — Rules-First with LLM Fallback

**Status:** Accepted
**Date:** 2026-04-10

---

## Context

Every transaction needs a category. Two mechanisms are available: deterministic rules (pattern match on counterparty / description / amount) and LLM classification. Both have distinct trade-offs.

- **Rules** are fast, free to run, perfectly predictable, and auditable. They require upfront authoring and miss anything not yet written.
- **LLM** handles novel payees without any upfront work but is slower, costs money per call, and can occasionally produce wrong or inconsistent answers.

Most transactions in a personal account are highly repetitive (the same supermarket, landlord, utility provider), which means a small rule set covers a large fraction of transactions once bootstrapped.

## Decision

**Strategy:** Rules-first, LLM fallback.

1. For each uncategorized transaction, evaluate all active rules in priority order (highest priority first). The first rule that matches assigns the category and sets `categorization_source = 'rule'`, `confidence = 1.0`.
2. If no rule matches, send the transaction to Claude Haiku (see ADR-0003). If Haiku returns `confidence >= 0.7`, accept the result (`categorization_source = 'llm'`).
3. If Haiku returns `confidence < 0.7`, escalate to Claude Sonnet (one retry). If Sonnet's result has `confidence >= 0.7`, accept it.
4. If both models return `confidence < 0.7`, leave the transaction uncategorized and surface it in the UI's "Needs Review" queue.
5. When a user manually assigns a category in the UI, they are offered the option to create a rule from the assignment (e.g., "Always classify ALBERT → Groceries"). This progressively grows the rule set and reduces LLM calls over time.

**Rule match types** (stored in a JSON field):
- `counterparty_contains` — substring match on counterparty name
- `counterparty_regex` — regex match on counterparty name
- `description_contains` — substring match on transaction description
- `amount_range` — matches when amount is within a specified range (useful for recurring fixed payments like rent)
- `composite` — AND of multiple sub-conditions

## Consequences

- The majority of recurring transactions (the user's regular payees) will be classified by rules after a few months of use — fast, free, deterministic.
- LLM is only called for genuinely unknown transactions or new payees. The expected call rate will decrease over time as the rule set matures.
- The system is fully auditable: every transaction has a `categorization_source` field (`rule`, `llm`, or `manual`) so the user can see exactly how each was categorized.
- Rules must be managed in the UI (CRUD). If rules become numerous, a priority / ordering mechanism prevents conflicts.
- Transactions in the "Needs Review" queue (low LLM confidence) need periodic user attention; the app must make this easy.

## Alternatives Considered

- **LLM-first, rules override** — More LLM spend, harder to be predictable for known payees. Not chosen; rules are cheaper and more reliable for recurring items.
- **LLM only** — Simplest bootstrapping, but every transaction costs tokens. Expensive and slower over high volumes.
- **Rules only** — Perfectly predictable, zero cost. Requires authoring a rule for every payee the user encounters. Viable long-term but poor experience early on, when payees are still being discovered.
