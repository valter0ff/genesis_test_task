"""Report generation."""

import json
from pathlib import Path
from typing import Any

from fpdf import FPDF

# Try to import our charts module
try:
    from . import charts
except ImportError:
    charts = None  # type: ignore


def _load_result(work_dir: Path) -> dict[str, Any]:
    """Load analysis result from work directory."""
    result_file = work_dir / "result.json"
    if not result_file.exists():
        raise FileNotFoundError(f"Result file not found: {result_file}")
    with result_file.open(encoding="utf-8") as f:
        return json.load(f)


def _generate_chart(work_dir: Path, result: dict[str, Any]) -> Path:
    """Generate a time-series chart of normalized monthly views and save as PNG.

    The `result` argument is kept for compatibility with the tests but is not used.
    Chart data is loaded from the work directory.

    Returns the path to the generated chart.
    """
    if charts is None:
        # Fallback: create a simple placeholder chart
        return _generate_placeholder_chart(work_dir)

    try:
        chart_result = charts.generate_chart(work_dir)
        if chart_result.get("ok", False):
            return Path(chart_result["data"]["chart_path"])
        else:
            # Chart generation failed, create placeholder
            return _generate_placeholder_chart(work_dir)
    except Exception as _exc:  # noqa: BLE001
        # Fallback to placeholder on any error
        return _generate_placeholder_chart(work_dir)


def _generate_placeholder_chart(work_dir: Path) -> Path:
    """Generate a placeholder chart when data is unavailable."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.text(0.5, 0.5, 'Chart data not available',
            horizontalalignment='center', verticalalignment='center',
            transform=ax.transAxes, fontsize=12)
    ax.set_title('Normalized Monthly Views')

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

    # Add DejaVuSans font for Cyrillic support
    font_path = Path(__file__).parent.parent.parent / "assets" / "fonts" / "DejaVuSans.ttf"
    try:
        if font_path.exists():
            pdf.add_font('DejaVu', '', str(font_path), uni=True)
            pdf.set_font('DejaVu', '', 12)
        else:
            pdf.set_font("helvetica", size=12)
    except Exception as _exc:  # noqa: BLE001
        pdf.set_font("helvetica", size=12)

    # Extract data from result
    data = result.get("data", {})
    metrics = data.get("metrics", {})
    reliability = data.get("reliability", {})
    headline = data.get("headline", "No headline available")

    # Title
    try:
        pdf.set_font('DejaVu', '', 16)
    except Exception as _exc:  # noqa: BLE001
        pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "Wikipedia Interest Analysis Report", ln=True, align='C')
    pdf.ln(5)

    # Verdict and confidence
    try:
        pdf.set_font('DejaVu', 'B', 12)
    except Exception as _exc:  # noqa: BLE001
        pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, headline, ln=True)

    confidence = reliability.get("confidence", "unknown")
    try:
        pdf.set_font('DejaVu', '', 12)
    except Exception as _exc:  # noqa: BLE001
        pdf.set_font("helvetica", size=12)
    pdf.cell(0, 10, f"Confidence: {confidence}", ln=True)
    pdf.ln(5)

    # Chart image
    pdf.image(str(chart_path), x=15, w=180)
    pdf.ln(5)

    # Statistics table
    try:
        pdf.set_font('DejaVu', 'B', 12)
    except Exception as _exc:  # noqa: BLE001
        pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "Key Metrics:", ln=True)
    try:
        pdf.set_font('DejaVu', '', 10)
    except Exception as _exc:  # noqa: BLE001
        pdf.set_font("helvetica", size=10)

    # Create a simple table
    col_width = 55
    row_height = 8

    pdf.cell(col_width, row_height, "Metric", border=1)
    pdf.cell(col_width, row_height, "Value", border=1)
    pdf.ln(row_height)

    yoy_norm = metrics.get("yoy_norm")
    trend = metrics.get("trend_pct_per_year")
    volume = metrics.get("volume", {})
    median_daily = volume.get("median_daily_12m", 0.0)
    total_12m = volume.get("total_12m", 0.0)

    # Format values
    yoy_str = f"{yoy_norm:.1%}" if yoy_norm is not None else "N/A"
    trend_str = f"{trend:+.1f}%/year" if trend is not None else "N/A"
    median_str = f"{median_daily:.1f}" if median_daily is not None else "N/A"
    total_str = f"{total_12m:,.0f}" if total_12m is not None else "N/A"

    pdf.cell(col_width, row_height, "YoY Change (normalized)", border=1)
    pdf.cell(col_width, row_height, yoy_str, border=1)
    pdf.ln(row_height)

    pdf.cell(col_width, row_height, "Trend", border=1)
    pdf.cell(col_width, row_height, trend_str, border=1)
    pdf.ln(row_height)

    pdf.cell(col_width, row_height, "Median Daily Views (last 12m)", border=1)
    pdf.cell(col_width, row_height, median_str, border=1)
    pdf.ln(row_height)

    pdf.cell(col_width, row_height, "Total Views (last 12m)", border=1)
    pdf.cell(col_width, row_height, total_str, border=1)
    pdf.ln(row_height)

    pdf.cell(col_width, row_height, "Confidence", border=1)
    pdf.cell(col_width, row_height, confidence.upper(), border=1)
    pdf.ln(row_height)

    # Assumptions and limitations
    pdf.ln(10)
    try:
        pdf.set_font('DejaVu', 'B', 12)
    except Exception as _exc:  # noqa: BLE001
        pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "Assumptions and Limitations:", ln=True)
    try:
        pdf.set_font('DejaVu', '', 10)
    except Exception as _exc:  # noqa: BLE001
        pdf.set_font("helvetica", size=10)

    limitations = [
        "Interest != willingness to pay",
        "Wikipedia views != app demand",
        "Analysis window: last 24 full months",
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
    except Exception as _exc:  # noqa: BLE001
        return {
            "ok": False,
            "data": {},
            "warnings": [f"Unexpected error during report generation: {_exc!s}"],
            "next_step": "Check your work directory and try again.",
        }