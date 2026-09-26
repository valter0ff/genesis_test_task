# Agent Handoff

## Current task
PHASE 0 — Freeze baseline

## Objective
Create a clean, reproducible baseline before any further changes.

## Do
1. Run `cd wikipedia-interest && uv run pytest -v` and record exact pass/fail count.
2. Run one real example (astronomy / uk) via `wikitrends run --spec …`.
3. Confirm the PDF and result.json are produced.
4. Update `PROJECT_STATUS.md` with the test count and date.
5. Commit with message: `chore: freeze baseline before final hardening`.

## Do not
- Change any source code
- Add new features
- Refactor
- Touch metrics or resolve logic

## Acceptance criteria
- Test count written in PROJECT_STATUS.md
- One working example artefact exists
- Clean commit on main (or current branch)

## After finishing
1. Show `git status` and `git log -1`
2. Show the exact pytest summary line
3. Stop. Do not start Phase 1.
