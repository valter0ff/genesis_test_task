# Architecture Decisions

## ADR-001 — Deterministic analysis stays in Python
**Decision:** All statistical calculations (YoY, Theil-Sen, MAD spikes, reliability) live in Python modules.
**Reason:** Agents should interpret results, not re-implement formulas. This keeps behaviour reproducible and testable.

## ADR-002 — Wikipedia pageviews = attention signal only
**Decision:** Never claim that pageviews equal product demand or willingness to pay.
**Reason:** Explicit requirement from `context.md` and good scientific practice.

## ADR-003 — Cross-language comparison uses only normalized metrics
**Decision:** Never rank languages by raw view counts. Always use normalized series / YoY / trend.
**Reason:** Different language editions have vastly different audience sizes.

## ADR-004 — Official Wikimedia Pageviews API only
**Decision:** Use `https://wikimedia.org/api/rest_v1/metrics/pageviews/...`
Do **not** scrape pageviews.wmcloud.org.
**Reason:** Official, stable, cacheable, rate-limited API. The Toolforge site is just a frontend over the same data.

## ADR-005 — CLI is the only interface for the agent
**Decision:** Agent interacts only via `wikitrends` CLI commands that return JSON.
**Reason:** Makes the skill usable by weak/cheap models and keeps the boundary clean.

## ADR-006 — Small phases, one commit per phase
**Decision:** Each implementation phase is small enough to review and revert.
**Reason:** Multiple human architects (Claude / GPT / Grok) + coding agent require clear checkpoints.

## ADR-007 — Manual override always available
**Decision:** `spec.articles` can override any automatic resolution.
**Reason:** Wikidata resolution is good but not perfect; user must stay in control.
