# PLAN — wikipedia-interest skill

Deadline: **27 Sep 23:59** (target submit: 27 Sep by 20:00, the rest is buffer).
Rule: one stage at a time; tick a box only when acceptance criteria (AC) pass.

## Schedule
| Day | Stages |
|---|---|
| 23 Sep | 0, start 1 |
| 24 Sep | 1, 2 |
| 25 Sep | 3, 4 |
| 26 Sep | 5, 6 |
| 27 Sep | 7, buffer, submit |

## Stage 0 — Repo setup
- [ ] Repo is already created by the user on GitHub (public, empty) and cloned locally; the project folder is that clone. Do NOT run `git push` or `gh` commands: commit locally only, the user pushes.
- [ ] MIT license, root `.gitignore` (`work/`, `.cache/`, `.env`, `__pycache__`)
- [ ] Skill dir with `pyproject.toml` (deps from CLAUDE.md), `.python-version`, `uv.lock`, empty package, `ruff` + `pytest` config
- AC: `cd wikipedia-interest && uv sync && uv run ruff check . && uv run pytest` passes on a fresh clone.

## Stage 1 — API client + fetch
- [ ] Live check of pageviews per-article and aggregate endpoints; save 2–3 real responses to `tests/fixtures/`; notes in `references/api-notes.md`
- [ ] `api.py`: User-Agent, sequential requests, backoff on 429/5xx, typed errors
- [ ] `cache.py`: disk cache keyed by URL
- [ ] `wikitrends fetch --project uk.wikipedia --article X --start --end` -> JSON
- AC: second identical call makes 0 HTTP requests; tests cover 404, 429, empty range (mocked).

## Stage 2 — Topic resolution
- [ ] `resolve`: topic + languages -> candidate articles per language (Wikidata sitelinks, fallback search), redirects resolved
- [ ] Output includes short description per candidate so the agent can confirm with the user; "not found" is explicit per language
- AC: works for 3 topics x (uk, pl, cs, en) on live API; fixtures recorded; ambiguous topic returns >1 candidate with a warning.

## Stage 3 — Metrics + reliability
- [ ] `metrics.py` + `reliability.py` exactly per CLAUDE.md spec
- [ ] Synthetic tests (must all pass): steady growth -> high confidence; single big spike -> `spike_share` high, `low/medium`; seasonal sine with no trend -> yoy ~0; platform-wide decline with flat raw -> flagged; tiny volume -> `low`; young article -> flagged
- [ ] `analyze` command -> `result.json` with per-language metrics, ranking, `caveats[]`, `next_step`
- AC: all synthetic scenarios behave as listed; hand-check 1 real topic against the Wikimedia Pageviews Analysis web tool (numbers within rounding).

## Stage 4 — Charts + PDF
- [ ] `charts.py`: comparison chart (normalized monthly, languages) + optional spike-highlight chart
- [ ] `report.py`: one-page A4 PDF per CLAUDE.md; bundled Cyrillic font; report language param
- AC: PDF is exactly 1 page; Ukrainian and English render correctly (visually checked); limitations block always present.

## Stage 5 — SKILL.md + orchestration
- [ ] `run --spec spec.json` chaining resolve -> fetch -> analyze -> report; spec saved in work dir
- [ ] Follow-ups: change languages/window/topic in spec and rerun without refetching cached data
- [ ] `SKILL.md`: when to use, 5-step workflow, exact commands, error playbook, answer template (verdict + confidence + caveats), how to confirm article choice, what NOT to claim
- [ ] `references/methodology.md`, `references/limitations.md`
- AC: from a clean state, the 3 brief examples run end-to-end via `run` in <2 min (warm cache: seconds).

## Stage 6 — Evals on cheap models
- [ ] `evals/prompts.md`: 3 brief examples + 3 follow-ups ("add language", "change window", "why low confidence?") + 1 bad input (unknown topic) + expected checkpoints
- [ ] Run each prompt via `fcc-claude` with a weak/free model (see README of FCC for config); optionally 1 run on real Haiku 4.5 via OpenRouter if budget allows
- [ ] `evals/RESULTS.md`: model, prompt, success?, number of tool calls, failures, what was changed in SKILL.md/CLI because of it
- AC: >= 5/7 prompts succeed on the weak model after at most 2 fix iterations; every failure documented.

## Stage 7 — README + roadmap + submit
- [ ] README: what/why, install, quick example with a sample PDF, design decisions and trade-offs, how results were verified (tests, hand-check, evals), limitations, AI tools used and how output was checked
- [ ] "How to evolve" section (no code): v2 related-topic discovery via categories/links and multi-topic ranking; v3 scale (DuckDB/Parquet cache, parallel fetch under rate limits, dumps); v4 extra signals (search trends, own product analytics), scheduled monitoring, confidence via bootstrap CI
- [ ] Sample output in `examples/` (one PDF + JSON)
- [ ] Fresh-clone test, then push, check repo is public
- AC: a stranger can clone, `uv sync`, run one command and get a PDF.
