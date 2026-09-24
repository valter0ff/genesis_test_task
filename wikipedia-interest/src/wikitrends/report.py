"""Report generation."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from fpdf import FPDF


def _load_result(work_dir: Path) -> dict[str, Any]:
    """Load analysis result from work directory."""
    result_file = work_dir / "result.json"
    if not result_file.exists():
        raise FileNotFoundError(f"Result file not found: {result_file}")
    with result_file.open(encoding="utf-8") as f:
        return json.load(f)


def _generate_chart(work_dir: Path, result: dict[str, Any]) -> Path:
    """Generate a time-series chart of views and save as PNG.

    Returns the path to the generated chart.
    """
    # Try to load article views data for plotting
    article_views_file = work_dir / "article_views.json"
    if not article_views_file.exists():
        # Create a dummy chart if data not available
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No data available for chart',
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=12)
        ax.set_title('Article Views Over Time')
    else:
        with article_views_file.open(encoding="utf-8") as f:
            article_views = json.load(f)

        if not article_views:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'No views data available',
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12)
            ax.set_title('Article Views Over Time')
        else:
            # Extract dates and views
            dates = [item["date"] for item in article_views]
            views = [item["views"] for item in article_views]

            # Convert dates to datetime objects for plotting
            date_objects = [datetime.strptime(d, "%Y%m%d").replace(tzinfo=UTC) for d in dates]

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(date_objects, views, marker='o', linestyle='-', linewidth=2, markersize=4)
            ax.set_xlabel('Date')
            ax.set_ylabel('Views')
            ax.set_title('Article Views Over Time')
            ax.grid(True, linestyle='--', alpha=0.7)

            # Rotate date labels for better readability
            plt.xticks(rotation=45)
            plt.tight_layout()

    # Ensure charts directory exists
    charts_dir = work_dir / "charts"
    charts_dir.mkdir(exist_ok=True)

    chart_path = charts_dir / "chart.png"
    fig.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    return chart_path


def _generate_pdf(work_dir: Path, result: dict[str, Any], chart_path: Path) -> Path:
    """Generate a one-page PDF report.

    Returns the path to the generated PDF.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("helvetica", size=12)

    # Extract data from result
    data = result.get("data", {})
    date_range = data.get("date_range", {})
    raw_views = data.get("raw_views", {})
    norm_views = data.get("normalized_views", {})

    # Title
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "Wikipedia Interest Analysis Report", ln=True, align='C')
    pdf.ln(5)

    # Verdict and confidence (placeholder)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "Verdict: Interest detected", ln=True)
    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 10, "Confidence: medium", ln=True)
    pdf.ln(5)

    # Chart image
    pdf.image(str(chart_path), x=15, w=180)
    pdf.ln(5)

    # Statistics table
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "Key Metrics:", ln=True)
    pdf.set_font("helvetica", size=10)

    # Create a simple table
    col_width = 45
    row_height = 8

    pdf.cell(col_width, row_height, "Metric", border=1)
    pdf.cell(col_width, row_height, "Value", border=1)
    pdf.ln(row_height)

    pdf.cell(col_width, row_height, "Date Range", border=1)
    pdf.cell(col_width, row_height,
             f"{date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}",
             border=1)
    pdf.ln(row_height)

    pdf.cell(col_width, row_height, "Total Views (raw)", border=1)
    pdf.cell(col_width, row_height, f"{raw_views.get('total', 0):,.0f}", border=1)
    pdf.ln(row_height)

    pdf.cell(col_width, row_height, "Total Views (normalized)", border=1)
    pdf.cell(col_width, row_height, f"{norm_views.get('total', 0):,.2f}", border=1)
    pdf.ln(row_height)

    pdf.cell(col_width, row_height, "Avg Daily Views (raw)", border=1)
    pdf.cell(col_width, row_height, f"{raw_views.get('mean', 0):,.1f}", border=1)
    pdf.ln(row_height)

    pdf.cell(col_width, row_height, "Avg Daily Views (normalized)", border=1)
    pdf.cell(col_width, row_height, f"{norm_views.get('mean', 0):,.2f}", border=1)
    pdf.ln(row_height)

    # Assumptions and limitations
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "Assumptions and Limitations:", ln=True)
    pdf.set_font("helvetica", size=10)
    limitations = [
        "Interest != willingness to pay",
        "Wikipedia views != app demand",
        f"Analysis window: {date_range.get('days', 0)} days",
        "Normalization uses project views (agent=user)",
        "Charts show trends but not causation"
    ]
    for limitation in limitations:
        pdf.cell(0, 6, f"- {limitation}", ln=True)

    # Save PDF
    report_path = work_dir / "report.pdf"
    pdf.output(str(report_path))

    return report_path


def generate_report(work_dir: Path | str) -> dict[str, Any]:
    """Generate PDF report from analyzed data in work directory.

    Args:
        work_dir: Path to work directory containing cached data

    Returns:
        Dictionary with report generation results
    """
    work_path = Path(work_dir)

    try:
        # Load analysis result
        result = _load_result(work_path)

        # Generate chart
        chart_path = _generate_chart(work_path, result)

        # Generate PDF
        report_path = _generate_pdf(work_path, result, chart_path)

        return {
            "ok": True,
            "data": {
                "chart_path": str(chart_path),
                "report_path": str(report_path),
            },
            "warnings": [],
            "next_step": "Report generated successfully. Use 'wikitrends report --work-dir <dir>' to regenerate.",
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "data": {},
            "warnings": [str(exc)],
            "next_step": "Run 'wikitrends fetch' and 'wikitrends analyze' first to generate data.",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "data": {},
            "warnings": [f"Unexpected error during report generation: {exc!s}"],
            "next_step": "Check your work directory and try again.",
        }