# Wikipedia Interest Analyzer

A standalone Agent Skill for analyzing Wikipedia pageviews to help B2C app founders
judge how interest in a topic is trending, and how far that trend can be trusted.

## Overview

The skill fetches Wikipedia pageview data, computes normalized metrics (year-over-year
growth, a robust trend, spike detection), assesses how reliable the result is, and
generates a one-page PDF report with a chart and a summary table. It is designed to
be driven by an AI agent through a small set of CLI commands with JSON output, but
can also be run directly by a developer.

**What actually works today:**
- Fetch daily pageviews for one article on one Wikipedia language edition, with disk
  caching (`fetch`).
- Compute year-over-year growth, a seasonality-robust trend (Theil-Sen on a 12-month
  rolling sum), spike detection (robust z-score), and a `high`/`medium`/`low`
  confidence rating with plain-language reasons (`analyze`).
- Generate a one-page A4 PDF with a chart, a metrics table, and the confidence reasons
  (`report`).
- Run the full pipeline for one or more languages from a spec file (`run --spec`).
- Multiple languages in one `run` are analyzed independently, one report per language
  — there is no cross-language ranking or combined comparison chart yet.

## Known limitations (please read before using)

- **No topic-to-article resolution.** The `topic` field in `spec.json` is used
  *literally* as the Wikipedia article title in every requested language. There is
  no Wikidata lookup or translation step. If you ask for `"topic": "astronomy"` on
  `uk.wikipedia`, it will fail, because the Ukrainian article is titled
  `Астрономія`. **You must supply the exact article title for each language
  yourself** (open `https://<lang>.wikipedia.org/wiki/<Title>` to check).
- **Report language is hardcoded to Ukrainian** in the current build (both the
  `analyze` command and `run` pass `lang="uk"` unconditionally). English report
  text is not currently reachable through the CLI, even for an English-language
  topic. Localizing this properly (via a `--lang` flag or a `report_lang` field in
  `spec.json`) is the top item for the next iteration.
- **Only single-article topics are tested end-to-end.** Multi-article "baskets" (a
  topic covered by more than one article) are implemented and unit-tested in
  `metrics.py`, but not exercised through the CLI in a live run.
- Wikipedia interest measures attention, not willingness to pay or product demand.
- Normalization uses total monthly project views (`agent=user`) to remove
  platform-wide traffic trends; it does not control for differences in editor or
  reader demographics between language editions.
- A trend/YoY figure requires at least 24 full calendar months of data; shorter
  windows return `null` for those fields and a `low` confidence rating.

## Installation

```bash
cd wikipedia-interest
uv sync
```
This installs runtime dependencies (`requests`, `numpy`, `matplotlib`, `fpdf2`) and
dev tools (`pytest`, `ruff`) from `uv.lock` — no other setup needed.

## Usage

### CLI commands

Run with `uv run wikitrends <command>` from the `wikipedia-interest` directory.

| Command | Purpose |
|---|---|
| `fetch` | Download daily pageviews for one article on one language edition. |
| `analyze` | Compute metrics + reliability from cached pageview data. |
| `report` | Generate the one-page PDF from an `analyze` result. |
| `run --spec spec.json` | Fetch + analyze + report for one or more languages. |

Every command prints one JSON object to stdout: `ok`, `data`, `warnings[]`,
`next_step`. Exit codes: `0` success, `2` bad input, `3` data/API problem.

`analyze`'s `data` contains:
- `metrics`: `yoy_raw`, `yoy_norm`, `yoy_ex_spikes`, `trend_pct_per_year`,
  `spike_share`, `spike_days`, `volume` (`median_daily_12m`, `total_12m`),
  `first_seen`, `young_article`, `basket_consistency`, `months`.
- `reliability`: `confidence` (`high`/`medium`/`low`), `flags` (rule codes that
  fired), `reasons` (matching plain-language sentences).
- `headline`: a one-sentence verdict combining direction, magnitude and confidence.

### Example: is interest in astronomy growing on Ukrainian Wikipedia?

`spec.json` — note the topic is the **exact Ukrainian article title**, not a
translation of the English word:
```json
{
  "topic": "Астрономія",
  "languages": ["uk"],
  "window": ["20240901", "20260801"]
}
```
```bash
uv run wikitrends run --spec spec.json
```
This fetches daily views for `uk.wikipedia`, computes metrics and a confidence
rating, and writes `work/<slug>/uk/report.pdf`.

### Manual step-by-step

```bash
uv run wikitrends fetch --project uk.wikipedia --article Астрономія --start 20240901 --end 20260801
uv run wikitrends analyze --work-dir work/<slug>
uv run wikitrends report --work-dir work/<slug>
```

## Development & testing

```bash
uv run ruff check .
uv run pytest -v          # unit tests, fixtures + synthetic data, no network
uv run pytest -m live     # optional: live calls against the real Wikimedia API
```

## How this was verified

- **Fresh-clone check**: `git clone` into an empty directory, `uv sync && uv run
  ruff check . && uv run pytest` — 0 lint issues, 37/37 tests pass.
- **Metrics correctness on synthetic data** (`tests/test_metrics.py`): steady
  growth, a single large spike on a declining baseline, pure seasonality with no
  trend, a known linear decline (checked against its exact expected slope), a
  young article, an inconsistent multi-article basket, and a too-short window —
  each asserted against the specific expected numbers, not just "doesn't crash".
- **Reliability rubric** (`tests/test_reliability.py`): one test per rule
  (`window_short`, `very_low_volume`, `low_daily_volume` alone, `spike_driven_sign`,
  `young_article`, `inconsistent_basket`, `platform_trend`, and the all-clear case),
  each built from real `metrics.analyze_topic()` output, not hand-crafted dicts.
- **One live end-to-end run**: `Астрономія` on `uk.wikipedia`, Sep 2024–Aug 2026,
  inspected manually — the PDF is one page, Cyrillic text renders correctly, and
  the numbers in the report match the JSON output.
- **Not yet done**: a number-for-number hand-check against the Wikimedia Pageviews
  Analysis web tool (pageviews.wmcloud.org) for the same article/window — the live
  run above confirms the pipeline works end-to-end, but the exact totals have not
  been independently cross-checked.

## AI tools used, and how their output was checked

Development combined two AI tools with different roles:
- **Claude (chat)** acted as architect and reviewer: wrote the metrics and
  reliability specification (formulas, edge cases, the exact test scenarios
  below), reviewed every diff pulled from this public GitHub repo before it was
  accepted, and caught several bugs this way (a `dict` where an `int` was
  expected in `analyze_topic`'s output; a bold Cyrillic font never registered,
  crashing PDF generation on non-Latin text; a leftover import of a deleted
  module that would have crashed the `run` command; a report table column too
  narrow for Ukrainian labels).
- **Claude Code**, running against free-tier models proxied through
  [Free Claude Code](https://github.com/Alishahryar1/free-claude-code) (primarily
  NVIDIA NIM's `nemotron-3-super-120b-a12b`, with Gemini/OpenRouter free models as
  fallback), wrote and iterated on the actual implementation from those
  specifications.

Every implementation stage was checked the same way: automated tests with
concrete expected values (not just "it runs"), `ruff` for lint, and a fresh-clone
run before considering a stage done. Several rounds of agent self-reports turned
out to be incomplete or inaccurate (tests that didn't cover what was asked, a
leftover bug the agent claimed was fixed) — these were only caught by pulling the
actual code from GitHub and reading it, which is why "verified" above lists
specific checks rather than repeating the agent's own summary.

## Roadmap

**Next up (biggest gap):** implement `resolve.py` — look up a topic on Wikidata
and resolve it to the correct article title per language via `sitelinks`, so the
user doesn't have to supply exact native titles by hand. Also: make report
language a real parameter instead of a hardcoded string.

- **v2 — related-topic discovery**: use Wikipedia's category graph / "what links
  here" to suggest related topics; rank several topics in one report.
- **v3 — scale**: replace the per-URL JSON cache with DuckDB/Parquet for
  multi-article, multi-language aggregation; parallelize fetches within
  Wikimedia's rate limits; support dump-based processing for history beyond the
  API's retention window.
- **v4 — additional signals**: cross-reference with Google Trends or other
  external signals; correlate with the user's own product analytics if supplied;
  scheduled monitoring with alerts on significant changes.

## License

MIT — see the LICENSE file.
