# Wikipedia Interest Analyzer

An Agent Skill that lets an AI assistant analyze Wikipedia pageviews to help B2C
app founders judge whether interest in a topic is growing, and how far that trend
can be trusted — delivered as a one-page PDF report.

## For the end user (a founder talking to an AI agent)

This skill follows the Agent Skills format: a directory containing `SKILL.md`
plus supporting code, which a compatible AI agent can discover and use on its
own. We built and tested it specifically with **Claude Code**: place or symlink
the `wikipedia-interest/` directory under `.claude/skills/wikipedia-interest/` in
the folder you run Claude Code from, and it is picked up automatically — no
further configuration needed. (The Agent Skills convention — auto-discovering a `SKILL.md` in a skills directory — is specific to Claude Code / claude.ai; other AI products don't
scan for skills this way. Nothing in `SKILL.md`'s content is Claude-specific,
so a different tool-calling agent could in principle be given its instructions
manually, but this hasn't been tested. The "works on a cheap/fast model"
requirement was verified by swapping the underlying model — not the agent
harness — running free-tier models like NVIDIA Nemotron through Claude Code
via a local proxy.)

Once installed, you don't run any commands yourself — you talk to the agent in
plain language, for example:

> "We're considering adding an astronomy course to our education app. Is
> interest in this topic growing on Ukrainian Wikipedia over the last 2 years,
> and how much can we trust that growth?"

The agent will:
1. Resolve your topic to the exact Wikipedia article title in each language you
   asked about (via Wikidata). If it can't find a confident match, it will ask
   you to confirm or provide the exact article title.
2. Fetch the pageview data and compute the trend, growth, and a `high`/`medium`/
   `low` confidence rating with plain-language reasons.
3. Reply with a short verdict in your own language, and generate a one-page PDF
   report with a chart and the same numbers, saved locally.
4. You can follow up naturally — "add Polish", "make it 3 years", "why is
   confidence low?" — without the agent redoing work it already has cached.

The rest of this README is for developers: how the skill is built, how to run it
directly, and how it was verified.

## Overview

The skill fetches Wikipedia pageview data, resolves a topic to the right article
per language via Wikidata, computes normalized metrics (year-over-year growth, a
robust trend, spike detection), assesses how reliable the result is, and
generates a one-page PDF report. It is driven by an AI agent through a small set
of CLI commands with JSON output (see `SKILL.md` for the agent's own workflow).

**What works today:**
- Resolve a topic to the correct article title per language via Wikidata, with a
  manual override (`spec.articles`) for when resolution is ambiguous or wrong.
- Fetch daily pageviews per article, with disk caching.
- Compute year-over-year growth (raw and normalized), a seasonality-robust trend
  (Theil-Sen on a 12-month rolling sum), spike detection (robust z-score), and a
  `high`/`medium`/`low` confidence rating with plain-language reasons, in English
  or Ukrainian (`report_lang`).
- Generate a one-page A4 PDF with a chart, a metrics table, and the confidence
  reasons, labeled in the chosen report language.
- Run the full pipeline for one or more languages from a spec file (`run --spec`).

**Known limitation:** multiple languages in one `run` are still analyzed
independently, one report per language — there is no combined ranking or
comparison chart across languages yet (planned next, see Roadmap).

## Installation

```bash
cd wikipedia-interest
uv sync
```

## Usage

### CLI commands

Run with `uv run wikitrends <command>` from the `wikipedia-interest` directory.
Every command prints one JSON object to stdout: `ok`, `data`, `warnings[]`,
`next_step`. Exit codes: `0` success, `2` bad input, `3` data/API problem.

| Command | Purpose |
|---|---|
| `fetch` | Download daily pageviews for one article on one language edition. |
| `analyze` | Compute metrics + reliability from cached pageview data. |
| `report` | Generate the one-page PDF from an `analyze` result. |
| `run --spec spec.json` | Resolve + fetch + analyze + report for one or more languages. |

`spec.json` fields:
- `topic` (required): the topic, in any language — resolved via Wikidata per
  target language.
- `languages` (required): list of language codes, e.g. `["uk", "pl"]`.
- `window`: `[start, end]` as `YYYYMMDD`.
- `articles` (optional): `{"uk": "Exact Title"}` — skips Wikidata resolution for
  that language and uses the given title directly. Use this when resolution
  fails or you already know the exact title.
- `report_lang` (optional, default `"en"`): `"en"` or `"uk"` — language of the
  PDF report, the reliability reasons, and the headline.

`analyze`'s `data` contains:
- `metrics`: `yoy_raw`, `yoy_norm`, `yoy_ex_spikes`, `trend_pct_per_year`,
  `spike_share`, `spike_days`, `volume` (`median_daily_12m`, `total_12m`),
  `first_seen`, `young_article`, `basket_consistency`, `months`.
- `reliability`: `confidence` (`high`/`medium`/`low`), `flags`, `reasons`.
- `headline`: a one-sentence verdict combining direction, magnitude and confidence.

### Example

```json
{
  "topic": "astronomy",
  "languages": ["uk"],
  "window": ["20240901", "20260801"],
  "report_lang": "uk"
}
```
```bash
uv run wikitrends run --spec spec.json
```
`topic` here is in English — resolution finds the Ukrainian article
(`Астрономія`) automatically. If resolution is ambiguous or fails for a
language, the JSON output's `warnings` will say so; add that language's exact
title under `articles` and rerun.

## Development & testing

```bash
uv run ruff check .
uv run pytest -v          # unit tests, fixtures + synthetic data, no network
uv run pytest -m live     # optional: live calls against the real Wikimedia/Wikidata API
```

## How this was verified

- **Fresh-clone check**: `uv sync && uv run ruff check . && uv run pytest` on a
  clean clone — 0 lint issues, 42/42 tests pass.
- **Metrics correctness on synthetic data**: steady growth, a single large spike,
  pure seasonality, a known linear decline (checked against its exact expected
  slope), a young article, an inconsistent multi-article basket, a too-short
  window — each asserted against specific expected numbers.
- **A realistic-noise regression test**: a Phase-2 change to `spike_share`'s
  formula was caught in review because it falsely flagged ordinary noisy data as
  spike-dominated (verified: ~0.38 vs the correct ~0.02–0.04); the formula was
  reverted and a test with Gaussian daily noise plus a few genuine spikes now
  guards against this regressing silently.
- **Reliability rubric**: one test per rule, each built from real
  `metrics.analyze_topic()` output, not hand-crafted dicts.
- **One live end-to-end run**: `Астрономія` on `uk.wikipedia`, inspected
  manually — one-page PDF, Cyrillic renders correctly, numbers match the JSON.
- **Not yet done**: a number-for-number hand-check against the Wikimedia
  Pageviews Analysis web tool (pageviews.wmcloud.org) for the same window.

## AI tools used, and how their output was checked

This project used five AI tools, each in a different role, coordinated by the
developer.

- **The developer** acted as orchestrator: decided which tool handled which
  part of the work, connected outputs between them (e.g. carrying a spec from
  one architect's plan into another's execution), manually ran and inspected
  test output and live CLI runs rather than trusting a tool's own summary, and
  hand-edited several files directly (config, stray-file cleanup, small fixes)
  when that was faster and safer than another prompt round-trip.
- **Claude (chat)** acted as lead architect and code reviewer for most of the
  build: wrote the metrics and reliability specification, reviewed diffs pulled
  directly from this public GitHub repo (not from the coding agent's own
  summaries) before accepting them, and caught several real bugs this way — a
  `dict` where an `int` was expected; a bold Cyrillic font never registered,
  crashing PDF generation; a leftover import of a deleted module that would have
  crashed the `run` command; a report table column too narrow for Ukrainian
  labels; and a statistical regression (see `spike_share` above) introduced by
  another AI's change, only caught by computing the metric on realistic
  synthetic data rather than trusting the passing test suite.
- **ChatGPT** acted as a second architect for a later phase of the work,
  producing `IMPLEMENTATION_PLAN.md`, `ARCHITECTURE_DECISIONS.md`,
  `PROJECT_STATUS.md` and `AGENT_HANDOFF.md` to hand off well-scoped, reviewable
  phases to the coding agent.
- **Grok** and **Gemini** were used at points during the multi-AI collaboration
  (see `ARCHITECTURE_DECISIONS.md`, ADR-006) alongside Claude and ChatGPT as
  additional architects/reviewers on specific decisions.
- **Claude Code**, running against free-tier models proxied through
  [Free Claude Code](https://github.com/Alishahryar1/free-claude-code) (NVIDIA
  NIM's `nemotron-3-super-120b-a12b`, with Gemini/OpenRouter fallbacks), wrote
  and iterated on the implementation from the architects' specifications.

Every stage was checked the same way regardless of which AI proposed it:
automated tests with concrete expected values, `ruff`, and a fresh-clone run.
Agent self-reports were repeatedly incomplete or inaccurate (tests that didn't
cover what was asked, a claimed fix that left a second call site broken, a
"no issues" lint claim contradicted by a fresh environment) — these were only
caught by pulling the actual code from GitHub and reading or running it, which
is why "verified" above lists specific checks rather than any agent's summary.
## Roadmap

- **Next up**: cross-language ranking and a combined comparison chart when
  `languages` has more than one entry (currently each language is analyzed and
  reported independently).
- **v2**: related-topic discovery via Wikipedia's category graph; rank several
  topics in one report.
- **v3**: replace the per-URL JSON cache with DuckDB/Parquet for larger-scale
  aggregation; parallelize fetches within Wikimedia's rate limits; support
  dump-based processing for history beyond the API's retention window.
- **v4**: cross-reference with external signals (e.g. search trends); correlate
  with the user's own product analytics if supplied; scheduled monitoring with
  alerts on significant trend changes.

## License

MIT — see the LICENSE file.
