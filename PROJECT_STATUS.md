# Project Status

**Last updated:** 2026-09-27

## Current state
Wikipedia Interest Agent Skill is functionally working end-to-end
(fetch → resolve → analyze → report), but has several gaps relative to `context.md`
before it can be considered submission-ready.

## Current phase
**Phase 0 — Freeze baseline** (completed)

## Last completed
- Implemented `resolve.py` (Wikidata sitelinks + manual override via `spec.articles`)
- Metrics: YoY raw/norm/ex-spikes, Theil-Sen, robust spike detection
- Reliability rubric with plain-language reasons (uk/en)
- One-page PDF report with Cyrillic support
- CLI JSON interface (`ok`, `data`, `warnings`, `next_step`)
- Unit tests for metrics, reliability, resolve, api, report

## Currently working on
Nothing (awaiting Phase 0)

## Next task
Phase 1 — Documentation consistency

## Validation (last known)
- Unit tests: 41 passed
- Live run: astronomy / uk.wikipedia → low confidence (window_short + low_daily_volume)
- Numbers roughly consistent with pageviews.wmcloud.org

## Important constraints
- Do **not** redesign the overall architecture
- Do **not** add external paid services or heavy dependencies
- Keep Wikimedia Pageviews REST API as the only data source
- Keep CLI JSON interface stable (additive changes only)
- Agent must never recalculate metrics itself — only interpret CLI JSON
- Prefer small, reviewable commits (one phase = one commit ideally)

## Known gaps (summary)
1. Report language still partially hardcoded to `uk`
2. No real cross-language comparison / ranking / combined chart
3. No `evals/` with results on a cheap model
4. Documentation (README / SKILL.md) has some outdated claims
5. `spike_share` definition / threshold may need final alignment
6. No sample PDF + JSON in `examples/`
