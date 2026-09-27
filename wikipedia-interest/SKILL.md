---
name: wikipedia-interest
description: Analyze Wikipedia pageviews across languages to judge interest in a topic, with a reliability verdict and a one-page PDF report. Use for questions about topic growth or which languages/topics to invest in.
---


# wikipedia-interest Agent Skill

**Skill**: Analyze Wikipedia pageviews across language editions to assess topic interest for B2C product decisions.

**When to use**:
- Comparing interest in a topic (e.g., "yoga", "electric cars") across multiple language editions of Wikipedia.
- Assessing the reliability of observed trends (e.g., distinguishing genuine interest spikes from noise).
- Generating shareable reports to inform localization or content investment decisions.

**Language Constraint**: Always match the language of the user's prompt in the final summary and recommendations (e.g.,

**CLI entry point**: `wikitrends` (run from the skill directory: `cd wikipedia-interest && uv run wikitrends <cmd>`).
All commands return JSON with `work_dir` field indicating the working directory used.

## Execution Control & Termination (CRITICAL FOR ALL AGENTS)

1. **One-Shot Preferred**: ALWAYS prefer running `uv run wikitrends run --spec spec.json` for full analysis workflows.
2. **NO Code Reading / Inspection**: Do NOT inspect source code (`grep`, `find`, `cat`), do NOT read internal Python modules, and do NOT attempt to reverse-engineer formula calculations. All metrics are pre-calculated by the CLI.
3. **STOP Immediately After Success**: Once `wikitrends` returns JSON with `"ok": true` and the PDF report path, **STOP executing commands immediately**.
4. **Immediate Synthesis**: Formulate your final response directly from the CLI's returned JSON output and point the user to `report.pdf`.

## Workflow for Agents

Do NOT write custom Python scripts or manually compute metrics. Rely strictly on the CLI outputs (`wikitrends fetch`, `analyze`, `report` or `run --spec`). All metrics are pre-calculated.

Follow these steps to answer user queries about comparative interest. Each step returns a JSON object with `ok`, `data`, `warnings`, and `next_step`. Propagate `warnings` to the user; treat `next_step` as a hint for the subsequent command.

### 1. Topic Resolution (HANDLED AUTOMATICALLY in `run --spec`)
The `run --spec` command automatically resolves the user's topic to Wikipedia article titles using Wikidata:
- If you know the exact article titles for each language, you can provide them via the optional `"articles"` field in `spec.json` (e.g., `{"uk": "Астрономія", "en": "Astronomy"}`)
- If `"articles"` is not provided or incomplete, the skill will attempt to resolve the topic via Wikidata search
- **Note**: If resolution fails (ambiguous, not found, or error), the skill will warn and skip that language
- **Critical**: If a fetch later returns "No data found" for an article, this typically means the article title doesn't exist in that language's Wikipedia. Report this to the user as: "no article titled X found in <lang> Wikipedia, please provide the correct title" and ask them to provide the exact article title for that language via spec.json's `"articles"` field.

### 2. One-shot execution (PRIMARY METHOD)
After resolving article titles for each language (or letting the skill resolve them automatically), construct a `spec.json` (e.g., topic, languages, window) and execute:
`uv run wikitrends run --spec spec.json`

The `spec.json` may optionally include an `"articles"` field mapping language codes to exact article titles (e.g., `{"uk": "Астрономія", "en": "Astronomy"}`) to override automatic resolution.
The `spec.json` may also optionally include a `"report_lang"` field with value `"en"` or `"uk"` to specify the language of the generated report (defaults to `"en"` if omitted).

- The command runs fetch -> analyze -> report sequentially for each language.
- Output: JSON containing `work_dir`, `language_results` with pre-calculated analysis and report data, plus `charts_and_reports` with file paths.
- **Action upon completion**: Immediately present the final answer to the user in their language and provide the path to `report.pdf`.

---

### Step-by-step CLI usage (Fallback only)

#### Resolve topic to articles (Internal / Automatic in `run --spec`)
> **Note**: To use `fetch`/`analyze`/`report` directly, supply `--project` (e.g., `en.wikipedia`) and `--article` (underscore-separated title) for each language variant.

#### Fetch pageviews data
`uv run wikitrends fetch --project <project> --article <article> --start <YYYYMMDD> --end <YYYYMMDD>`
- Output: JSON object containing `article_views` (daily views) and `project_views` (monthly project views for normalization), plus `work_dir`.

#### Compute metrics
`uv run wikitrends analyze`
- Output: JSON with per-language metrics (`yoy_norm`, `trend_pct_per_year`, `spike_share`, `volume`, `first_seen`, `basket_consistency`, `yoy_ex_spikes`), language ranking, `warnings`, and `confidence` (high/medium/low) with `reasons[]`. Saved to `work/<slug>/result.json`.

#### Generate report
`uv run wikitrends report`
- Output: Creates `work/<slug>/report.pdf` (one-page A4 summary with charts and tables).

## Interpreting Output

### Metrics Definitions
- `yoy_norm`: Year-over-year growth of normalized views (views per million project views). Indicates relative interest trend.
- `trend_pct_per_year`: Theil-Sen slope of monthly normalized series, expressed as % change per year relative to median.
- `spike_share`: Fraction of total views attributable to daily spikes (robust z-score > 4, where spike magnitude is measured as residual above rolling median baseline).
- `volume`: Median daily views and total views in the last 12 months.
- `confidence`: Reliability assessment (high/medium/low) based on automated heuristic flags.

### Translating to Business Advice
- **Strong, reliable signal**: High confidence + positive `yoy_norm` + moderate `spike_share` (<0.3) -> sustained interest; consider localization.
- **Unreliable spike**: Low confidence due to high `spike_share` or conflicting `yoy_norm`/`yoy_ex_spikes` -> transient event; avoid over-investment.
- **Platform-wide trend**: Flag when `yoy_raw` and `yoy_norm` differ in sign -> trend is driven by total Wikipedia traffic, not the topic itself.
- **Low volume**: Total 12m views < 1000 -> insufficient data to draw conclusions.

## Error Handling
All CLI commands return JSON with:
- `ok`: false indicates failure.
- `warnings[]`: array of plain-language messages.
- `next_step`: suggestion for recovery.
Exit codes:
- 0: Success
- 2: Bad input (invalid date, missing parameters)
- 3: Data/API problem (network error, persistent 429/5xx)

**Special case for missing articles**: If the fetch command returns data showing "No data found" for an article, this typically means the article title doesn't exist in that language's Wikipedia. Report this to the user as: "no article titled X found in <lang> Wikipedia, please provide the correct title" and ask them to provide the exact article title for that language.

## Limitations
- Wikipedia interest != willingness to pay or product usage.
- Data limited to `agent=user` filter (excludes bots).
- Analysis uses only full calendar months; partial months are discarded.
- Refer to `references/limitations.md` for exhaustive details.