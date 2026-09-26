# Agent Handoff

## Current task
PHASE 2 — Statistical correctness

## Objective
Align the statistical definitions in code with the intended specification and documentation.
Focus on three things only:
1. `spike_share` formula
2. Spike threshold consistency
3. Volume window (prefer last 12 full calendar months)

## Context
Current `spike_share` in `metrics.py` is approximately:

    spike_excess / total_views

The intended definition (from the original metrics design) is closer to:

    spike_excess / total_excess_above_baseline

where excess = max(view - baseline, 0).

Spike detection currently uses robust z-score with threshold `> 4` and an extra
`max(scale, sqrt(baseline))` term. Keep the threshold at 4. Decide whether the
`sqrt(baseline)` floor is still justified; if kept, it must be clearly reflected
in tests/docs. Prefer staying close to the simple robust z-score definition unless
there is a strong reason to keep the floor.

Volume is currently taken from the last 365 days of the daily series.
Prefer calculating volume from the last 12 **full calendar months** to stay
consistent with the rest of the monthly logic.

## Do
1. Read `src/wikitrends/metrics.py` carefully (especially `find_spikes` and volume calculation).
2. Fix `spike_share` so the denominator is total excess above baseline, not total views.
3. Add/adjust unit tests that lock the new definition (include a clear synthetic case where one large spike produces spike_share close to 1.0).
4. Align volume calculation with “last 12 full calendar months” if that is consistent with existing monthly helpers; otherwise document the actual rule and keep it consistent.
5. Make sure spike threshold documentation and code agree on `z > 4`.
6. Run the full test suite and fix any broken tests caused by the definition change.
7. Do **not** implement report_lang or cross-language comparison.

## Do not
- Change resolve logic
- Change reliability rubric rules (except if a test expectation must follow the new spike_share)
- Add new features
- Touch report language or multi-language comparison
- Swallow failures

## Acceptance criteria
1. `spike_share` uses excess-above-baseline in the denominator.
2. Synthetic test exists that demonstrates the corrected behaviour.
3. Volume window is consistent with the monthly full-month approach (or explicitly justified).
4. All tests pass.
5. No unrelated refactors.

## Files likely involved
- `src/wikitrends/metrics.py`
- `tests/test_metrics.py`
- possibly a short note in README/SKILL if a definition sentence must be adjusted

## After finishing
1. Show the key diff in `find_spikes` / volume calculation.
2. Show new or changed tests.
3. Run `uv run pytest -q` and show the summary.
4. STOP. Do not start Phase 3.
