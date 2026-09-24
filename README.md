# Wikipedia Interest Analyzer

A standalone Agent Skill for analyzing Wikipedia pageviews across language editions to help B2C app founders decide which topics and languages to invest in.

## Overview

This tool fetches Wikipedia pageview data, computes normalized metrics (year-over-year growth, trend slope, spike share, etc.), assesses reliability, and generates a one‑page PDF report with charts and a summary table. Designed to be used by AI agents (e.g., Claude Haiku) via a simple CLI, but also usable directly by developers.

**Key features**:
- Resolve topic names to Wikipedia article titles in multiple languages (via Wikidata or per‑wiki search).
- Fetch daily pageview data (cached to avoid redundant API calls).
- Compute metrics exactly as specified: `yoy_norm`, `trend_pct_per_year`, `spike_share`, volume, reliability flags, and confidence.
- Generate a shareable A4 PDF report with a comparison chart, metrics table, and assumptions/limitations section.
- Support iterative follow‑ups (e.g., “add Czech”, “extend window to 3 years”) without refetching cached data.
- No compiled binaries; reproducible Python environment managed by `uv`.

## Installation

1. Clone the repository (or copy the skill directory).
2. Navigate to the skill directory:
   ```bash
   cd wikipedia-interest
   ```
3. Synchronize the virtual environment and install dependencies:
   ```bash
   uv sync
   ```
   This installs runtime dependencies (`requests`, `numpy`, `matplotlib`, `fpdf2`) and development tools (`pytest`, `ruff`).

## Usage

### CLI Commands

The entry point is `wikitrends` (run with `uv run wikitrends <command>` from the skill directory).

| Command | Purpose |
|---------|---------|
| `fetch` | Download daily pageview data for a given project (language edition) and article title. |
| `analyze` | Compute metrics from cached pageview data. |
| `report` | Generate a one‑page PDF report from analyzed data. |
| `run --spec spec.json` | One‑shot execution: resolve → fetch → analyze → report using a JSON specification. |

Each command outputs a single JSON object to stdout (logs go to stderr) with:
- `ok`: boolean indicating success.
- `data`: command‑specific result.
- `warnings[]`: array of plain‑language messages.
- `next_step`: hint for the subsequent command.

Exit codes: `0` (success), `2` (bad input), `3` (data/API problem).

### Example Workflow

Suppose you want to compare interest in "yoga" across English, French, and German Wikipedia over the last 24 months.

1. **Create a spec file** (`spec.json`):
   ```json
   {
     "topic": "Yoga",
     "languages": ["en", "fr", "de"],
     "window": ["20210901", "20230831"],
     "criteria": {}
   }
   ```

2. **Run the skill**:
   ```bash
   uv run wikitrends run --spec spec.json
   ```
   The tool will:
   - Resolve "yoga" to article titles in each language (using Wikidata sitelinks, fallback to search).
   - Fetch daily pageviews for each resolved article (caching responses).
   - Compute metrics and produce a confidence assessment.
   - Generate `report.pdf` in the work directory.

3. **Read the output**:
   - Check the final JSON for `ok`: true and locate the generated PDF.
   - Open `work/<slug>/report.pdf` to see the verdict, chart, table, and assumptions.

### Direct Command Chaining (Advanced)

If you prefer to run each step manually:

```bash
# Fetch for English Wikipedia
uv run wikitrends fetch --project en.wikipedia --article Yoga --start 20210901 --end 20230831
# -> returns JSON with next_step: "Run 'wikitrends analyze' to compute metrics from this data."

# Analyze (uses the work directory from the fetch command)
uv run wikitrends analyze
# -> returns JSON with next_step: "Run 'wikitrends report' to generate a PDF summary."

# Report
uv run wikitrends report
# -> returns JSON confirming PDF generation.
```

## Development & Testing

- **Linting**: `uv run ruff check .`
- **Tests**: `uv run pytest -v`
  - Unit tests use recorded fixtures; no network calls.
  - To run live API tests (optional): `uv run pytest -m live`
- **Type hints**: Throughout the codebase; mypy can be added if desired.

## Iterative Future Improvements (Roadmap)

As requested in the requirements, here are possible evolutions without changing the core skill contract:

### v2: Related‑Topic Discovery
- Use Wikipedia category graph or “what links here” to suggest related topics (e.g., for “yoga”, surface “meditation”, “pilates”).
- Multi‑topic ranking: compute a composite interest score across a topic cluster to inform broader content investments.

### v3: Scale to Large Corpora
- Replace JSON cache with DuckDB/Parquet for efficient multi‑article, multi‑language aggregations.
- Parallelize fetches within Wikimedia rate limits (respecting `User-Agent` and backoff).
- Support dump‑based processing for historical analysis beyond the API’s retention limits.

### v4: Additional Signals
- Integrate Google Trends (via `pytrends`) or social‑media signals to triangulate Wikipedia interest.
- Incorporate product‑specific analytics (if provided by the user) to correlate interest with conversion.
- Scheduled monitoring: track interest trends over time and alert on significant changes.

## Verification & Limits

- **Verified on**: macOS/Linux with Python 3.11+, `uv` 0.4.x.
- **Tested models**: CLI outputs validated with synthetic fixtures; end‑end runs checked against the Wikimedia Pageviews Analysis web tool for a few real topics.
- **Limitations** (always present in reports):
  - Wikipedia interest measures attention, not willingness to pay or product usage.
  - Data limited to `agent=user` (excludes spiders and automated traffic).
  - Normalization removes platform‑wide trends but does not control for editor‑demographic differences across language editions.
  - Analysis uses only full calendar months; incomplete months are discarded.
  - Refer to `references/limitations.md` for exhaustive details.

## License

MIT – see the LICENSE file.

---

*Developed with Claude Code.*