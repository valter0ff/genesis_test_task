# Project Status

**Last updated:** 2026-09-27

## Current state
Wikipedia Interest Agent Skill is functionally working end-to-end
(fetch → resolve → analyze → report), but has a known regression to fix
before continuing, plus several gaps relative to `context.md`.

## Current phase
**BUGFIX — spike_share regression** (found during review, not yet fixed)

## Last completed
- Phase 0: baseline frozen (41 tests passed)
- Phase 1: documentation consistency (README, SKILL.md, AUDIT.md)
- Phase 2: statistical hardening (volume window aligned to full calendar months) —
  **introduced a regression, see below**
- Phase 3: report_lang parameter (spec.json field, wired through run/analyze/report)

## Known regression (blocking, found in review)
Phase 2 changed `spike_share`'s formula from `excess / total_views` to
`excess / total_excess_above_baseline`, but the `> 0.3` threshold in
`reliability.py` was not recalibrated for the new, much smaller denominator.
Verified on a realistic noisy 2-year series with 3 genuine spikes: old formula
gives `spike_share ≈ 0.04` (correctly not flagged), new formula gives
`spike_share ≈ 0.38` (falsely flagged as spike-dominated). Existing unit tests
did not catch this because they use noise-free synthetic
