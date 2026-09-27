# Project Status

**Last updated:** 2026-09-27

## Current state
Wikipedia Interest Agent Skill is functionally working end-to-end
(fetch → resolve → analyze → report), with the Phase 2 regression fixed and
verified. Documentation (README.md, README.ua.md, SKILL.md) is up to date with
the current code. Several features from the roadmap (Phases 4+) are not yet
built.

## Current phase
**Ready for submission** — no phase in progress.

## Last completed
- Phase 0: baseline frozen (41 tests passed)
- Phase 1: documentation consistency (README, SKILL.md, AUDIT.md)
- Phase 2: statistical hardening (volume window aligned to full calendar months)
- Phase 3: report_lang parameter (spec.json field, wired through run/analyze/report)
- **Bugfix**: reverted the Phase 2 `spike_share` regression (formula changed
  from `excess / total_excess_above_baseline` back to `excess / total_views`);
  added a regression test using realistic Gaussian noise + genuine spikes,
  verified `spike_share ≈ 0.02` (correct) instead of `≈ 0.38` (false positive)
- README.md, README.ua.md and SKILL.md updated to accurately describe
  `resolve.py`, `articles` override, and `report_lang` (previously described
  these as not implemented / hardcoded, which was stale)

## Next task
Phase 4 — Cross-language comparison (see IMPLEMENTATION_PLAN.md). Not started.

## Validation (last known)
- Unit tests: 42 passed
- Live run: astronomy / uk.wikipedia → low confidence (window_short + low_daily_volume)
- Numbers roughly consistent with pageviews.wmcloud.org
- Fresh-clone check passed: `uv sync && uv run ruff check . && uv run pytest`

## Important constraints
- Do **not** redesign the overall architecture
- Do **not** add external paid services or heavy dependencies
- Keep Wikimedia Pageviews REST API as the only data source
- Keep CLI JSON interface stable (additive changes only)
- Agent must never recalculate metrics itself — only interpret CLI JSON
- Prefer small, reviewable commits (one phase = one commit ideally)
- Any change to a metric's formula must include a test using realistic noisy
  data (not only smooth/deterministic synthetic series) before it's considered
  validated — added after the spike_share regression

## Known gaps (summary)
1. No real cross-language comparison / ranking / combined chart (Phase 4)
2. No `evals/` with results on a cheap model (Phase 9)
3. No sample PDF + JSON in `examples/` (Phase 10)
4. `median_daily_12m` is computed via manual date-range reconstruction from
   monthly keys (Phase 2) — works and is tested, but more complex than the
   original "last 365 raw days" approach
