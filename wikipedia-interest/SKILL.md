# wikipedia-interest Agent Skill

**Skill**: Analyze Wikipedia pageviews across language editions to assess topic interest for B2C product decisions.

**When to use**: 
- Comparing interest in a topic (e.g., "yoga", "electric cars") across multiple language editions of Wikipedia.
- Assessing the reliability of observed trends (e.g., distinguishing genuine interest spikes from noise).
- Generating shareable reports to inform localization or content investment decisions.

**Language Constraint**: Always match the language of the user's prompt in the final summary and recommendations (e.g., if user asks in Ukrainian, reply in Ukrainian).

**CLI entry point**: `wikitrends` (run from the skill directory: `cd wikipedia-interest && uv run wikitrends <cmd>`).
All commands return JSON with `work_dir` field indicating the working directory used.

## Workflow for Agents

Do NOT write custom Python scripts or manually compute metrics. Rely strictly on the CLI outputs (`wikitrends fetch`, `analyze`, `report` or `run --spec`). All metrics are pre-calculated.

Follow these steps to answer user queries about comparative interest. Each step returns a JSON object with `ok`, `data`, `warnings`, and `next_step`. Propagate `warnings` to the user; treat `next_step` as a hint for the subsequent command.

**Note**: The `run --spec` command combines all steps (fetch → analyze → report) and is recommended for most use cases.

### 1. Resolve topic to articles (optional but recommended)
Use the `resolve` subcommand (not yet exposed as a standalone CLI; see note below) to map a topic name and target languages to specific Wikipedia article titles. This step is currently internal to the `run --spec` workflow. For direct CLI use, you must know the exact article titles per language.

> **Note**: The `resolve` functionality is only available via the `run --spec` command at present. To use `fetch`/`analyze`/`report` directly, supply `--project` (e.g., `en.wikipedia`) and `--article` (underscore-separated, URL-encoded title) for each language variant you wish to compare.

### 2. Fetch pageviews data
For each language/article pair, run:
```bash
uv run wikitrends fetch --project <project> --article <article> --start <YYYYMMDD> --end <YYYYMMDD>
```
- `--project`: e.g., `en.wikipedia`, `de.wikipedia`
- `--article`: title in underscores (e.g., `Electric_car`)
- `--start`/`--end`: date range in `YYYYMMDD` (use full months only; the tool will ignore incomplete months)
- Output: JSON object containing `article_views` (daily views array) and `project_views` (monthly project views array for normalization), plus `work_dir` indicating the working directory. Saved to `work/<slug>/article_views.json` and `work/<slug>/project_views.json`.
- `next_step`: typically "Run 'wikitrends analyze' to compute metrics from this data."

### 3. Compute metrics
From the work directory containing `article_views.json`, run:
```bash
uv run wikitrends analyze
```
- Output: JSON with per-language metrics (`yoy_norm`, `trend_pct_per_year`, `spike_share`, `volume`, `first_seen`, `basket_consistency`, `yoy_ex_spikes`), a language ranking by `yoy_norm`, `warnings`, and `confidence` (high/medium/low) with `reasons[]`.
- Saved to `work/<slug>/result.json`.
- `next_step`: typically "Run 'wikitrends report' to generate a PDF summary."

### 4. Generate report
From the same work directory, run:
```bash
uv run wikitrends report
```
- Output: JSON confirming PDF generation (`ok`: true) and `next_step` (if any).
- Creates `work/<slug>/report.pdf` (one-page A4, includes verdict chart, table, and assumptions/limitations).

### 5. One-shot execution (recommended)
To avoid manual chaining, use the spec-driven mode:
```bash
uv run wikitrends run --spec spec.json
```
Where `spec.json` contains:
```json
{
  "topic": "Yoga",
  "languages": ["en", "de", "ja"],
  "window": ["20220101", "20231201"],
  "criteria": {"min_confidence": "medium"}
}
```
- The command runs fetch → analyze → report sequentially for each language.
- The spec is saved to the work directory for follow‑ups (e.g., changing only `languages` or `window` avoids refetching).
- Output: JSON containing `work_dir`, `language_results` with analysis and report data for each language, plus `charts_and_reports` with file paths.
- `next_step`: indicates completion or next actions for failed languages.

## Interpreting Output

### Metrics Definitions
- `yoy_norm`: Year‑over‑year growth of normalized views (views per million project views). Indicates relative interest trend.
- `trend_pct_per_year`: Theil‑Sen slope of monthly normalized series, expressed as % change per year relative to the series median.
- `spike_share`: Fraction of total views attributable to days where daily views exceed baseline by >4.8×MAD (robust outlier).
- `volume`: Median daily views and total views in the last 12 months (raw, not normalized).
- `confidence`: Reliability assessment (high/medium/low) based on flags:
  - Window < 24 months → downgrade (seasonality not controlled)
  - Median daily views < 20 → downgrade
  - Total 12m views < 1000 → force low
  - `spike_share` > 0.3 → downgrade
  - `yoy_norm` and `yoy_ex_spikes` differ in sign → force low
  - Article younger than window +30 days → downgrade
  - `basket_consistency` < 0.5 → downgrade (for multi‑article baskets)
  - `yoy_raw` and `yoy_norm` differ in sign → downgrade (platform‑wide trend drives result)

### Translating to Business Advice
- **Strong, reliable signal**: High confidence + positive `yoy_norm` + moderate `spike_share` (<0.3) → sustained interest; consider localization or feature investment.
- **Unreliable spike**: Low confidence due to high `spike_share` or conflicting `yoy_norm`/`yoy_ex_spikes` → interest may be driven by transient events; avoid over‑investment.
- **Platform‑wide trend**: Flag when `yoy_raw` and `yoy_norm` differ in sign → the observed raw trend is largely due to overall Wikipedia traffic changes, not topic‑specific interest.
- **Low volume**: Total 12m views < 1000 → insufficient data to draw conclusions; consider broader topics or longer windows.
- **Young article**: `first_seen` later than window start +30 days → interest may reflect article maturity rather than topic popularity.

## Error Handling
All CLI commands return JSON with:
- `ok`: false indicates failure.
- `warnings[]`: array of plain‑language messages (e.g., "No article found for 'X' in xx.wikipedia; try synonym or English title").
- `next_step`: suggestion for recovery (e.g., "Check the date format and try again.").
Exit codes:
- 0: Success
- 2: Bad input (e.g., invalid date, missing parameters)
- 3: Data/API problem (e.g., network error, persistent 429/5xx)

## Example Session
User: "Should we invest in a French‑language version of our meditation app, comparing interest in 'meditation' across English, French, and German Wikipedia over the last 2 years?"

Agent:
1. Create `spec.json` with topic "meditation", languages ["en","fr","de"], window ["20210901","20230901"].
2. Run `uv run wikitrends run --spec spec.json`.
3. Wait for completion (outputs JSON after each stage; final JSON confirms PDF generation).
4. Read `work/<slug>/report.pdf` for the verdict and table.
5. Summarize to user: e.g., "Interest in meditation is growing strongest in French Wikipedia (yoy_norm +18%, high confidence), followed by English (+12%) and German (+5%). Recommend prioritizing localization for French‑speaking users."

## Limitations (always present in reports)
- Wikipedia interest ≠ willingness to pay or product usage.
- Data limited to the `agent=user` filter (excludes spiders/anonymized traffic).
- Normalization removes platform‑wide trends but does not account for demographic differences between language editions.
- Analysis uses only full calendar months; partial months are discarded.
- Refer to `references/limitations.md` for exhaustive details.

---
*Tip for weak models (Haiku 4.5 class):* Stick to the `run --spec` command for complex queries; it hides the chaining complexity and provides clear `next_step` hints at each stage.