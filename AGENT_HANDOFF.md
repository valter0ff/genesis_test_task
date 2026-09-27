# Agent Handoff

## Current task
PHASE 3 — Report language parameter

## Objective
Stop hard-coding Ukrainian as the report language.
Make report language configurable via `spec.json` and pass it through the pipeline.

## Context
- `reliability.py` already supports `lang` (`en` / `uk`) for reasons and headlines.
- `report.py` already has label dictionaries for `en` and `uk`.
- The problem is mainly in the orchestration path: `analyze` / `run` currently force `lang="uk"` in places.
- SKILL.md promises that the skill should match the user's language when possible.

## Do

1. Add optional field to `spec.json`:

   ```json
   {
     "report_lang": "en"
   }
   ```

   Supported values for now: `"en"` and `"uk"`.

2. Wire `report_lang` through:
   - `run --spec`
   - `analyze` (when called from `run`, and ideally when called standalone if feasible)
   - reliability assessment (`assess` / headline)
   - PDF report generation

3. Default behaviour when `report_lang` is missing:
   - Prefer a sensible default (for example `"en"`, or infer from the first requested language if it is `uk`/`en`).
   - Document the chosen default clearly.

4. Ensure:
   - `report_lang: "en"` → English headline, reasons, table labels
   - `report_lang: "uk"` → Ukrainian headline, reasons, table labels

5. Update `SKILL.md` to document the new `report_lang` field.
6. Add or adjust tests if there is a clean place to lock the behaviour (even a small unit/integration style check is enough).
7. Keep single-language behaviour backward-compatible when the field is omitted.

## Do not

- Implement cross-language comparison (Phase 4)
- Redesign the whole CLI
- Add full i18n framework or many new languages
- Change metrics formulas
- Break existing JSON schema in a non-additive way

## Acceptance criteria

- `spec.json` can contain `"report_lang": "en"` or `"report_lang": "uk"`.
- English request path produces English report text.
- Ukrainian path still works.
- When `report_lang` is omitted, behaviour is defined and documented.
- Existing tests still pass.
- `SKILL.md` mentions the new field.

## Files likely involved

- `src/wikitrends/cli.py`
- `src/wikitrends/reliability.py` (already mostly ready)
- `src/wikitrends/report.py`
- `wikipedia-interest/SKILL.md`
- possibly a small test file

## After finishing

1. Show the key diffs (especially where `lang="uk"` was previously hardcoded).
2. Show how `report_lang` flows from `spec` → `analyze` / `report`.
3. Run `uv run pytest -q` and show the summary.
4. Stop. Do not start Phase 4.
