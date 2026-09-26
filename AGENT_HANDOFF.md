# Agent Handoff

## Current task
PHASE 1 — Documentation consistency

## Objective
Bring README.md and SKILL.md in line with the actual current code.
Do **not** change any program behaviour.

## Context
- `resolve.py` is already implemented and wired into `run --spec`.
- README still claims there is no topic-to-article resolution — this is outdated.
- SKILL.md mentions spike threshold as `>4.8xMAD`, while the code uses robust z-score `> 4`.
- Report language is still largely hardcoded to Ukrainian in some places.
- Multi-language runs currently produce independent reports (no ranking / combined chart yet).
- `AUDIT.md` is outdated and should be marked historical or removed.

## Do
1. Read the current code (especially `resolve.py`, `cli.py` run path, `metrics.py` spike logic, `reliability.py`, `report.py`).
2. Update `README.md`:
   - Remove the claim “No topic-to-article resolution”.
   - Accurately describe automatic Wikidata resolution + optional `articles` override.
   - Accurately describe current multi-language behaviour (independent reports, no cross-language ranking yet).
   - Accurately describe report language limitation if it still exists.
   - Keep the honest limitations section.
3. Update `wikipedia-interest/SKILL.md`:
   - Reflect that topic resolution is handled automatically inside `run --spec`.
   - Fix the spike_share / threshold description so it matches the code (`z > 4`, residual vs baseline).
   - Keep the agent workflow clear and conservative.
4. Handle `AUDIT.md`:
   - Either delete it, or add a clear note at the top that it is historical and no longer reflects current state.
5. Do **not** change any Python source files.
6. Do **not** change metrics, reliability, resolve, or CLI behaviour.

## Do not
- Modify any `.py` files
- Add new features
- Refactor code
- Change test expectations
- Implement report_lang or cross-language comparison (those are later phases)
- Soften or remove the honest limitations

## Acceptance criteria
1. README no longer claims that topic resolution is missing.
2. SKILL.md no longer contains the incorrect `4.8xMAD` claim.
3. Documentation accurately describes:
   - automatic resolution + `articles` override
   - current multi-language behaviour
   - current report language behaviour
4. No Python files are modified.
5. Existing tests still pass (`uv run pytest`).

## Files likely involved
- `README.md`
- `wikipedia-interest/SKILL.md`
- `AUDIT.md` (optional cleanup)

## After finishing
1. Show `git status` and list of changed files.
2. Show a short summary of what claims were corrected.
3. Run `uv run pytest -q` and show the summary line.
4. STOP. Do not start Phase 2.
