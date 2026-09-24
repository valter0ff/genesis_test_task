# wikipedia-interest — Agent Skill

Build a standalone **Agent Skill** (SKILL.md + own code) that lets an AI agent analyze
Wikipedia pageviews across language editions, judge how far the result can be trusted,
draw charts and produce a shareable one-page PDF report. Audience: B2C app founders
deciding which topics / languages to invest in.

Deliverable: public GitHub repo. **Deadline: 27 Sep 23:59.** Work from `PLAN.md`, stage by stage.

## Non-negotiable requirements (from the brief)
- Skill = `SKILL.md` + real code doing the data work. The agent must NOT have to write code per request.
- No compiled binaries in the repo. Reproducible env (`uv` + lockfile).
- ALL custom material (code, tests, evals, fonts, docs for the skill) lives inside the skill dir.
- Must be easy for a fast cheap model (Haiku 4.5 class): few commands, JSON output, explicit `next_step`.
- Recommendations must be data-backed; assumptions and limitations must be visible in every result and report.
- Support follow-ups ("add Czech", "make it 3 years") without refetching data.

## Layout
```
/                          README.md (for humans: approach, verification, limits, roadmap), CLAUDE.md, PLAN.md
wikipedia-interest/        <- THE SKILL
  SKILL.md                 short, imperative, <150 lines
  pyproject.toml, uv.lock, .python-version
  src/wikitrends/          cli.py, api.py, cache.py, resolve.py, metrics.py, reliability.py, charts.py, report.py
  references/              methodology.md, api-notes.md, limitations.md (agent reads on demand)
  assets/fonts/            DejaVuSans*.ttf (Cyrillic support; license file next to it)
  tests/                   pytest, fixtures/ (real recorded API responses), synthetic series
  evals/                   prompts.md, run_eval.md, RESULTS.md
```

## Stack
Python >= 3.11, `uv`, `pytest`, `ruff`. Runtime deps only in `[project.dependencies]`: `requests`, `numpy`, `matplotlib`, `fpdf2`.
Dev tools (`pytest`, `ruff`) go in `[dependency-groups] dev = [...]` (PEP 735; add with `uv add --dev pytest ruff`).
`uv sync` installs the `dev` group by default, so plain `uv sync` is enough. Do NOT put pytest/ruff into runtime deps or extras.
No pandas/scipy unless clearly justified. Type hints everywhere. Small pure functions for metrics.
CLI entry point `wikitrends` via `[project.scripts]`; run as `cd wikipedia-interest && uv run wikitrends <cmd>`.

## CLI contract (design for a weak agent)
Commands: `resolve`, `fetch`, `analyze`, `report`, and `run --spec spec.json` (does all four).
- stdout = ONE JSON object only. Logs/progress -> stderr. Exit code 0 ok, 2 bad input, 3 data/API problem.
- Every JSON has: `ok`, `data`, `warnings[]`, `next_step` (plain-language hint for the agent).
- Errors are actionable: say what is wrong and what to try ("no article found for 'X' in cs; try synonym or English title").
- A `spec.json` (topic(s), languages, window, criteria) is saved in the work dir so follow-ups only change fields.
- Default work dir `./work/<slug>/` (gitignored): `spec.json`, `cache/`, `result.json`, `charts/`, `report.pdf`.

## Wikimedia API rules
- Pageviews: `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}`
  and `.../pageviews/aggregate/{project}/{access}/{agent}/{granularity}/{start}/{end}`. Project like `uk.wikipedia`.
  Dates `YYYYMMDD`. Article title: underscores, URL-encoded. Data starts July 2015.
- Use `agent=user` (excludes spiders/automated), `access=all-access`.
- Resolve titles: Wikidata `wbsearchentities` -> `wbgetentities&props=sitelinks` for titles per wiki;
  fallback to per-wiki `action=query&list=search`; resolve redirects with `redirects=1`.
- **Always send a descriptive User-Agent with contact** (env `WIKITRENDS_CONTACT`, default a repo URL).
- Requests strictly sequential, small delay; on 429/5xx exponential backoff (max 5 tries). Rate limits exist and may change.
- **Verify endpoints with a live call before coding against them; save real responses as test fixtures. Never invent response shapes.**
- Cache every response on disk (key = URL). Only the current/incomplete day is not cached forever.
- Fetch DAILY series (needed for spike detection), aggregate to monthly locally. Use only full months.

## Metrics spec (implement exactly, test on synthetic data)
Per (topic, language): basket = sum of daily views over confirmed articles.
Normalization: `norm = basket_views / project_total_views * 1e6` (views per million project views) — removes the
platform-wide traffic trend. Default window: last 24 full months.

| Metric | Definition |
|---|---|
| `yoy_raw`, `yoy_norm` | last 12 months / previous 12 months - 1 (raw and normalized) |
| `trend_pct_per_year` | Theil–Sen slope of monthly normalized series, as % of its median per year |
| `spike_share` | robust z = (x - median) / (1.4826*MAD) on daily series; days with z > 4 are spikes; share of window views above baseline that comes from spike days |
| `volume` | median daily views and total last-12m views |
| `first_seen` | first day with views. The API omits days with zero views (verify in stage 1a): absent days = 0 views, a 404 on a range = no views in that range (article may or may not exist: check existence separately). Flag if `first_seen` is later than window start + 30 days (article younger than window) |
| `basket_consistency` | share of articles in basket with positive `yoy_norm` (only if >1 article) |
| `yoy_ex_spikes` | `yoy_norm` recomputed with spike days replaced by baseline |

Comparing languages: rank by `yoy_norm` AND show audience scale (views/12m) separately. Never rank by absolute views.

## Reliability rubric (`confidence`: high / medium / low, always with `reasons[]`)
Start `high`, downgrade one level per flag (min low); some flags force `low`:
- window < 24 months -> seasonality not controlled (downgrade)
- median daily views < 20 (downgrade); total 12m views < 1000 (force low)
- `spike_share` > 0.3 (downgrade); `yoy_norm` and `yoy_ex_spikes` differ in sign (force low)
- article younger than window, see `first_seen` (downgrade)
- basket_consistency < 0.5 (downgrade)
- `yoy_raw` and `yoy_norm` differ in sign (downgrade; say platform-wide trend drives the result)
Reasons are plain sentences the agent can quote. The script decides confidence; the agent only reports it.

## Report (one page A4 PDF)
Top: 1-2 sentence verdict + confidence. Middle: comparison chart (normalized monthly series, languages) and a small
table (yoy_norm, trend, volume, confidence). Bottom: "Assumptions and limitations" (always present: interest != willingness
to pay; Wikipedia views != app demand; window; agent=user; normalization; flagged reasons). Report language = user's language.
Cyrillic must render (bundled TTF). Charts: readable in grayscale, labelled axes, source + date in footer.

## Working rules for you (the coding agent)
1. Read `PLAN.md`; do ONE stage at a time; tick the checkbox only when acceptance criteria pass.
2. Before saying "done": `uv run ruff check . && uv run pytest` must pass. Show the output.
3. Commit after each stage (`git commit -m "stage N: ..."`). Never run `git push` (the user pushes). Never commit secrets, `work/`, caches, `.env`.
4. No network in unit tests: use recorded fixtures. Keep one optional `pytest -m live` test.
5. Do not add features beyond the plan. If something in this file seems wrong or impossible, stop and say so.
6. Write `SKILL.md` for a weak model: numbered steps, exact commands, what to do on each error, what to say to the user.
7. Keep README.md honest: what was verified, on which models, what is not covered.
