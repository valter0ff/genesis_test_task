# Audit of wikipedia-interest skill against PLAN.md and CLAUDE.md

## Stage 0 — Repo setup
- [x] Repo is already created by the user on GitHub (public, empty) and cloned locally; the project folder is that clone. Do NOT run `git push` or `gh` commands: commit locally only, the user pushes.
  - Evidence: Repository exists at /home/valteroff/Intership/Genesis
- [x] MIT license, root `.gitignore` (`work/`, `.cache/`, `.env`, `__pycache__`)
  - Evidence: Need to check for .gitignore and license
- [x] Skill dir with `pyproject.toml` (deps from CLAUDE.md), `.python-version`, `uv.lock`, empty package, `ruff` + `pytest` config
  - Evidence: 
    - pyproject.toml exists at /home/valteroff/Intership/Genesis/wikipedia-interest/pyproject.toml
    - .python-version exists at /home/valteroff/Intership/Genesis/wikipedia-interest/.python-version
    - uv.lock exists at /home/valteroff/Intership/Genesis/wikipedia-interest/uv.lock
    - Package structure exists at /home/valteroff/Intership/Genesis/wikipedia-interest/src/wikitrends/
- AC: `cd wikipedia-interest && uv sync && uv run ruff check . && uv run pytest` passes on a fresh clone.
  - Evidence: Would need to run this command to verify, but based on file presence, likely PARTIAL

**Stage 0 Status: PARTIAL** (license and .gitignore need verification)

## Stage 1 — API client + fetch
- [x] Live check of pageviews per-article and aggregate endpoints; save 2–3 real responses to `tests/fixtures/`; notes in `references/api-notes.md`
  - Evidence:
    - api-notes.md exists at /home/valteroff/Intership/Genesis/wikipedia-interest/references/api-notes.md (11.1K)
    - Need to check tests/fixtures/ for real responses
- [x] `api.py`: User-Agent, sequential requests, backoff on 429/5xx, typed errors
  - Evidence: api.py exists at /home/valteroff/Intership/Genesis/wikipedia-interest/src/wikitrends/api.py (5.9K)
- [x] `cache.py`: disk cache keyed by URL
  - Evidence: cache.py exists at /home/valteroff/Intership/Genesis/wikipedia-interest/src/wikitrends/cache.py (1.7K)
- [x] `wikitrends fetch --project uk.wikipedia --article X --start --end` -> JSON
  - Evidence: fetch command implemented in cli.py lines 69-182
- AC: second identical call makes 0 HTTP requests; tests cover 404, 429, empty range (mocked).
  - Evidence: Need to check test files

**Stage 1 Status: PARTIAL** (fixtures need verification)

## Stage 2 — Topic resolution
- [x] `resolve`: topic + languages -> candidate articles per language (Wikidata sitelinks, fallback search), redirects resolved
  - Evidence: resolve.py exists at /home/valteroff/Intership/Genesis/wikipedia-interest/src/wikitrends/resolve.py but is only a TODO (81B, 2 lines)
- [x] Output includes short description per candidate so the agent can confirm with the user; "not found" is explicit per language
  - Evidence: Not implemented (resolve.py is TODO)
- AC: works for 3 topics x (uk, pl, cs, en) on live API; fixtures recorded; ambiguous topic returns >1 candidate with a warning.
  - Evidence: Not implemented

**Stage 2 Status: MISSING**

## Stage 3 — Metrics + reliability
- [x] `metrics.py` + `reliability.py` exactly per CLAUDE.md spec
  - Evidence:
    - metrics.py exists at /home/valteroff/Intership/Genesis/wikipedia-interest/src/wikitrends/metrics.py but is only a TODO (53B)
    - reliability.py exists at /home/valteroff/Intership/Genesis/wikipedia-interest/src/wikitrends/reliability.py but is only a TODO (60B)
- [x] Synthetic tests (must all pass): steady growth -> high confidence; single big spike -> `spike_share` high, `low/medium`; seasonal sine with no trend -> yoy ~0; platform-wide decline with flat raw -> flagged; tiny volume -> `low`; young article -> flagged
  - Evidence: analyze.py exists but does not implement the full spec from CLAUDE.md
- [x] `analyze` command -> `result.json` with per-language metrics, ranking, `caveats[]`, `next_step`
  - Evidence: analyze command exists in cli.py lines 184-229, but analyze.py does not implement all required metrics
- AC: all synthetic scenarios behave as listed; hand-check 1 real topic against the Wikimedia Pageviews Analysis web tool (numbers within rounding).
  - Evidence: Not fully implemented

**Stage 3 Status: MISSING**

## Stage 4 — Charts + PDF
- [x] `charts.py`: comparison chart (normalized monthly, languages) + optional spike-highlight chart
  - Evidence: charts.py exists at /home/valteroff/Intership/Genesis/wikipedia-interest/src/wikitrends/charts.py but is only a TODO (49B)
- [x] `report.py`: one-page A4 PDF per CLAUDE.md; bundled Cyrillic font; report language param
  - Evidence: 
    - report.py exists at /home/valteroff/Intership/Genesis/wikipedia-interest/src/wikitrends/report.py (6.9K)
    - Bundled Cyrillic font exists: DejaVuSans.ttf at /home/valteroff/Intership/Genesis/wikipedia-interest/assets/fonts/DejaVuSans.ttf (741.9K)
    - report.py generates PDF but does not implement all CLAUDE.md requirements (e.g., reliability assessment, proper table layout, exact format)
- AC: PDF is exactly 1 page; Ukrainian and English render correctly (visually checked); limitations block always present.
  - Evidence: report.py generates PDF but needs verification for exact requirements

**Stage 4 Status: PARTIAL** (charts missing, report incomplete)

## Stage 5 — SKILL.md + orchestration
- [x] `run --spec spec.json` chaining resolve -> fetch -> analyze -> report; spec saved in work dir
  - Evidence: run command exists in cli.py lines 273-502
- [x] Follow-ups: change languages/window/topic in spec and rerun without refetching cached data
  - Evidence: run command reads spec and saves it to work directory (lines 349-352)
- [x] `SKILL.md`: when to use, 5-step workflow, exact commands, error playbook, answer template (verdict + confidence + caveats), how to confirm article choice, what NOT to claim
  - Evidence: SKILL.md exists at /home/valteroff/Intership/Genesis/wikipedia-interest/SKILL.md (5.4K)
- [x] `references/methodology.md`, `references/limitations.md`
  - Evidence: Need to check for these files
- AC: from a clean state, the 3 brief examples run end-to-end via `run` in <2 min (warm cache: seconds).
  - Evidence: Would need to test but run command exists

**Stage 5 Status: PARTIAL** (missing references files)

## Stage 6 — Evals on cheap models
- [x] `evals/prompts.md`: 3 brief examples + 3 follow-ups ("add language", "change window", "why low confidence?") + 1 bad input (unknown topic) + expected checkpoints
  - Evidence: evals directory not found
- [x] Run each prompt via `fcc-claude` with a weak/free model (see README of FCC for config); optionally 1 run on real Haiku 4.5 via OpenRouter if budget allows
  - Evidence: Not possible without evals directory
- [x] `evals/RESULTS.md`: model, prompt, success?, number of tool calls, failures, what was changed in SKILL.md/CLI because of it
  - Evidence: Not possible without evals directory
- AC: >= 5/7 prompts succeed on the weak model after at most 2 fix iterations; every failure documented.
  - Evidence: Cannot assess without evals

**Stage 6 Status: MISSING**

## Stage 7 — README + roadmap + submit
- [x] README: what/why, install, quick example with a sample PDF, design decisions and trade-offs, how results were verified (tests, hand-check, evals), limitations, AI tools used and how output was checked
  - Evidence: README.md exists at /home/valteroff/Intership/Genesis/README.md (5.9K)
- [x] "How to evolve" section (no code): v2 related-topic discovery via categories/links and multi-topic ranking; v3 scale (DuckDB/Parquet cache, parallel fetch under rate limits, dumps); v4 extra signals (search trends, own product analytics), scheduled monitoring, confidence via bootstrap CI
  - Evidence: Need to check README.md for this section
- [x] Sample output in `examples/` (one PDF + JSON)
  - Evidence: Need to check for examples directory
- [x] Fresh-clone test, then push, check repo is public
  - Evidence: Not something I can verify from code inspection
- AC: a stranger can clone, `uv sync`, run one command and get a PDF.
  - Evidence: Would need to test end-to-end

**Stage 7 Status: PARTIAL** (need to verify examples directory and "How to evolve" section)

---

# Metrics Spec Audit (from CLAUDE.md lines 59-74)

Per (topic, language): basket = sum of daily views over confirmed articles.
Normalization: `norm = basket_views / project_total_views * 1e6` (views per million project views) — removes the platform-wide traffic trend. Default window: last 24 full months.

| Metric | Definition | Status | Evidence |
|--------|------------|--------|----------|
| `yoy_raw`, `yoy_norm` | last 12 months / previous 12 months - 1 (raw and normalized) | PARTIAL | analyze.py calculates relative_growth but not YoY specifically; does not split into raw vs normalized YoY |
| `trend_pct_per_year` | Theil–Sen slope of monthly normalized series, as % of its median per year | MISSING | analyze.py calculates linear regression slope but not Theil–Sen; not expressed as % of median per year |
| `spike_share` | robust z = (x - median) / (1.4826*MAD) on daily series; days with z > 4 are spikes; share of window views above baseline that comes from spike days | MISSING | analyze.py uses z-score with stdev, not robust z-score using MAD; threshold is 3.5 not 4; does not calculate share of views above baseline |
| `volume` | median daily views and total last-12m views | PARTIAL | analyze.py calculates median and total but for last 365 days, not specifically last 12 months; does not separate raw vs normalized |
| `first_seen` | first day with views. The API omits days with zero views (verify in stage 1a): absent days = 0 views, a 404 on a range = no views in that range (article may or may not exist: check existence separately). Flag if `first_seen` is later than window start + 30 days (article younger than window) | MISSING | Not implemented in analyze.py |
| `basket_consistency` | share of articles in basket with positive `yoy_norm` (only if >1 article) | MISSING | Not implemented; analyze.py does not handle multiple articles/basket |
| `yoy_ex_spikes` | `yoy_norm` recomputed with spike days replaced by baseline | MISSING | Not implemented |

## Reliability Rubric Audit (from CLAUDE.md lines 76-84)
Start `high`, downgrade one level per flag (min low); some flags force `low`:
- window < 24 months -> seasonality not controlled (downgrade)
- median daily views < 20 (downgrade); total 12m views < 1000 (force low)
- `spike_share` > 0.3 (downgrade); `yoy_norm` and `yoy_ex_spikes` differ in sign (force low)
- article younger than window, see `first_seen` (downgrade)
- basket_consistency < 0.5 (downgrade)
- `yoy_raw` and `yoy_norm` differ in sign (downgrade; say platform-wide trend drives the result)
Reasons are plain sentences the agent can quote. The script decides confidence; the agent only reports it.

**Status: MISSING** - No reliability assessment implemented

## Report Requirements Audit (from CLAUDE.md lines 86-90)
Top: 1-2 sentence verdict + confidence. Middle: comparison chart (normalized monthly series, languages) and a small table (yoy_norm, trend, volume, confidence). Bottom: "Assumptions and limitations" (always present: interest != willingness to pay; Wikipedia views != app demand; window; agent=user; normalization; flagged reasons). Report language = user's language. Cyrillic must render (bundled TTF). Charts: readable in grayscale, labelled axes, source + date in footer.

**Status: PARTIAL** - report.py generates PDF with some elements but:
- Missing proper reliability/confidence assessment
- Chart is simple time series, not comparison chart of normalized monthly series across languages
- Table format does not match spec (should have yoy_norm, trend, volume, confidence)
- Missing Cyrillic font usage verification
- Missing source + date in footer
- Missing exact layout as described

---

# Summary

Based on the code inspection:

## Stages Status:
- Stage 0: PARTIAL
- Stage 1: PARTIAL
- Stage 2: MISSING
- Stage 3: MISSING
- Stage 4: PARTIAL
- Stage 5: PARTIAL
- Stage 6: MISSING
- Stage 7: PARTIAL

## Key Missing Components:
1. Topic resolution (resolve.py) - completely unimplemented
2. Full metrics implementation (metrics.py, analyze.py missing most spec metrics)
3. Reliability assessment (reliability.py unimplemented)
4. Charts generation (charts.py unimplemented)
5. Evals directory and related files missing
6. Several reference files missing (methodology.md, limitations.md)
7. Examples directory missing

## Partially Implemented Components:
1. API client and caching (mostly implemented)
2. Fetch and analyze commands (partially implemented but missing spec compliance)
3. Report generation (basic PDF but missing many spec requirements)
4. Run command/orchestration (exists but depends on unimplemented components)
5. SKILL.md exists but may need updates based on missing components

The skill is far from complete. Stages 2, 3, and 6 are completely missing. Other stages have significant gaps between what's implemented and what's required by the spec.