# Agent Handoff

## Current task
BUGFIX — spike_share regression (before Phase 4)

## Objective
Revert `spike_share`'s formula in `metrics.py` to the original definition and
add a regression test using realistic noisy data, so this class of bug can't
silently reappear.

## Context
- Phase 2 changed `find_spikes()` in `metrics.py`: `spike_share` went from
  `spike_excess / total_views` to `spike_excess / total_excess_above_baseline`.
- The `> 0.3` threshold for the `spike_dominated` flag in `reliability.py` was
  never recalibrated for the new denominator.
- Verified impact: a realistic 2-year series (normal day-to-day noise, 3 genuine
  spikes) scores `spike_share ≈ 0.04` under the old formula and `≈ 0.38` under
  the new one — the new formula falsely triggers `spike_dominated` on ordinary
  data.
- The existing unit tests (`test_find_spikes`, the scenario tests in
  `test_metrics.py`) all use perfectly smooth/deterministic synthetic series, so
  they didn't catch this: the denominator degenerates to ~0 or ~the-spike-itself
  either way in those cases.

## Do

1. In `metrics.py`'s `find_spikes()`, revert `spike_share` to:
```python
   spike_excess = sum(daily[i] - baseline[i] for i in range(n) if flags[i])
   total_views = sum(daily)
   spike_share = spike_excess / total_views if total_views != 0 else 0.0
```
2. Update the docstring (currently says "fraction of excess views above baseline
   that come from spike days" — revert to "fraction of total views that come
   from spike days (above baseline)").
3. In `tests/test_metrics.py`'s `test_find_spikes`, restore the original expected
   value and comment (`spike_share ≈ 99.0/129.0 ≈ 0.767` for that fixture, not
   `1.0`).
4. Add ONE new test in `tests/test_metrics.py` using a series with realistic
   Gaussian day-to-day noise (e.g. `random.gauss(30, sqrt(30))` per day, seeded)
   plus 2-3 genuine spikes added on top, over ~2 years. Assert `spike_share`
   stays comfortably under 0.3 in that case. This is the exact scenario Phase 2
   broke, and it must not regress silently again.
5. Do not touch `reliability.py`'s threshold — the original formula was already
   calibrated against it.

## Do not

- Change any other metric (`yoy_*`, `trend_pct_per_year`, `volume`)
- Touch `reliability.py`
- Start Phase 4 before this is committed and green

## Acceptance criteria

- `find_spikes()` uses the original `excess / total_views` formula
- `test_find_spikes`
