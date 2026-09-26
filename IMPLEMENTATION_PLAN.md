# Implementation Plan

Each phase is designed to be given as a **single prompt** to the coding agent.
After each phase: run tests → review diff → update `PROJECT_STATUS.md` → commit.

---

## PHASE 0 — Freeze baseline
**Goal:** Create an objective starting point.

**Tasks:**
1. Run full test suite (`uv run pytest -v`) and record exact count.
2. Run one real CLI example (astronomy / uk) and keep the `work/` output.
3. Confirm fresh-clone path still works (`uv sync && uv run pytest`).
4. Commit current state with message: `chore: freeze baseline before final hardening`.

**Do not change any code.**

**Acceptance criteria:**
- Test count recorded in `PROJECT_STATUS.md`
- One working PDF + result.json exist under `work/` or `examples/`
- Clean git status after the commit

---

## PHASE 1 — Documentation consistency
**Goal:** Make README + SKILL.md match reality. No behaviour changes.

**Files likely involved:**
- `README.md`
- `wikipedia-interest/SKILL.md`
- possibly `AUDIT.md` / `PLAN.md` (mark as historical if needed)

**Fix claims about:**
- Automatic topic resolution (it now exists)
- Report language (currently limited)
- Multi-language behaviour (independent reports, no ranking yet)
- Spike threshold and `spike_share` definition
- Known limitations

**Do not** change Python code.

**Acceptance criteria:**
- No statement in README/SKILL contradicts the current code
- Obsolete “TODO / not implemented” removed where the feature already exists

---

## PHASE 2 — Statistical correctness (small hardening)
**Goal:** Make definitions consistent across code, tests and docs.

**Likely tasks:**
1. Confirm / align `spike_share` formula (excess from spikes / total excess above baseline vs total views).
2. Confirm spike threshold (z > 4) is the same in code, tests and documentation.
3. Confirm volume window is “last 12 full calendar months” (or document the actual rule).
4. Add/adjust a couple of synthetic tests if any edge case is missing.

**Files:**
- `src/wikitrends/metrics.py`
- `tests/test_metrics.py`
- docs if needed

**Acceptance criteria:**
- All existing + new tests pass
- Definition of every metric is identical in code ↔ tests ↔ README/SKILL

---

## PHASE 3 — Report language parameter
**Goal:** Stop hard-coding Ukrainian.

**Tasks:**
1. Add optional `report_lang` (or `lang`) field to `spec.json`.
2. Pass it through `run` → `analyze` → `report`.
3. Support at least `en` and `uk`.
4. Default: if missing, try to infer from first language or fall back to `en`.
5. Update SKILL.md with the new field.

**Files:**
- `cli.py`
- `reliability.py` (already has lang)
- `report.py`
- `SKILL.md`
- tests

**Acceptance criteria:**
- `report_lang: "en"` → English headline + labels + reasons
- `report_lang: "uk"` → Ukrainian
- Single-language runs still work exactly as before when field is omitted

---

## PHASE 4 — Cross-language comparison (core missing feature)
**Goal:** When several languages are requested, produce a real comparison.

**4.1 New module**
Create `src/wikitrends/comparison.py`.

**Input:** list of per-language analysis results
**Output:** structured comparison object, e.g.:

```json
{
  "ranking": [
    {"lang": "pl", "yoy_norm": 0.31, "trend_pct_per_year": 18.2, "confidence": "high", "volume_median": 42},
    {"lang": "cs", "yoy_norm": 0.14, "trend_pct_per_year": 11.0, "confidence": "medium", "volume_median": 28}
  ],
  "summary": "Polish shows stronger recent growth than Czech…",
  "caveats": ["…"]
}
```

**Rules:**

- Rank primarily by yoy_norm (then trend, then confidence)
- Never use raw view counts for ranking
- Keep the text cautious (attention ≠ demand)

**4.2 Wire into run --spec**
When len(languages) > 1, call comparison and include the result in the final JSON.

**4.3 Tests**

- Unit tests with synthetic per-language metrics
- No network

**Acceptance criteria:**

- Single-language behaviour unchanged
- Multi-language run returns a comparison section
- All tests pass


## PHASE 5 — Comparative chart
**Goal:** One clear visual for multi-language.
**Tasks:**

- Add a bar chart (or multi-line normalized series) comparing languages.
- Include it in the PDF when comparison exists.
- Keep single-language chart as-is.

**Files:**

- charts.py
- report.py

**Acceptance criteria:**

- Multi-language PDF contains the comparative chart
- Still fits on one page (or gracefully becomes two pages only if unavoidable)

---

## PHASE 6 — PDF polish
**Goal:** Make the report look submission-ready.

**Add / improve:**

- Source line: “Source: Wikimedia Pageviews API”
- Analysis period
- Generation timestamp
- Clear “Assumptions and limitations” block (always present)
- Comparison table when multi-language

**Acceptance criteria:**

- Visual check of one Ukrainian and one English PDF
- Limitations block always present

---

## PHASE 7 — SKILL.md agent workflow
**Goal:** Make the skill easy for a weak model.

**Update workflow to:**

1. Understand request
2. Build / adjust spec.json (use articles override when needed)
3. run --spec
4. Read JSON (especially warnings, reliability, comparison)
5. Synthesize answer in the user’s language
6. Point to the PDF
7. Stop

**Emphasize:**

- Never recalculate metrics
- Always surface low confidence and caveats
- For ambiguous resolution — ask the user or use articles override

---

## PHASE 8 — Hardening & error paths
**Goal:** No silent failures.

**Check / improve:**

- API 429 / 5xx / timeout
- Invalid language / missing article
- Empty data
- Corrupt cache
- Invalid spec.json
- Chart generation failure (must not turn into ok: true with empty chart)

**Acceptance criteria:**

- Clear ok: false + useful warnings + sensible next_step for the main failure modes

---

## PHASE 9 — Evaluation suite
**Goal:** Prove the skill works on realistic prompts.

**Create evals/:**

- prompts.md — 6–7 scenarios from context.md + follow-ups + edge cases
- RESULTS.md — model used, success/failure, number of tool calls, notes

**Scenarios (minimum):**

- Single language astronomy (uk)
- Compare PL vs CS intermittent fasting
- Learning English across several languages
- Follow-up “add German”
- Ambiguous topic
- Very low-volume topic
- Short window / young article

**Acceptance criteria:**

- At least 5/7 scenarios succeed on a cheap model after ≤ 2 fix iterations
- Results documented

---

## PHASE 10 — Final packaging
**Goal:** Stranger can clone and get a PDF in < 2 minutes.

**Tasks:**

- Put one good example (PDF + JSON) into examples/
- Final README polish (install, quick start, limitations, how verified, AI tools used)
- Fresh-clone test one last time
- Update PROJECT_STATUS.md → “Ready for submission”

---
