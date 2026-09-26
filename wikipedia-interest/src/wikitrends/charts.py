"""Chart generation."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib

# Use non-interactive backend
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .metrics import normalize, to_monthly


def _load_article_views(work_dir: Path) -> tuple[list[float], str]:
    """Load article views and return daily views list and start date (YYYY-MM-DD).

    Returns:
        (daily_views, start_date) where daily_views is a list of floats
        and start_date is a string in YYYY-MM-DD format.
    """
    article_file = work_dir / "article_views.json"
    with article_file.open(encoding="utf-8") as f:
        article_data = json.load(f)

    # Expecting a list of {"date": "YYYYMMDD", "views": int}
    sorted_article = sorted(article_data, key=lambda x: x["date"])
    dates = [item["date"] for item in sorted_article]
    daily_views = [float(item["views"]) for item in sorted_article]

    if dates:
        start_date = f"{dates[0][:4]}-{dates[0][4:6]}-{dates[0][6:8]}"
    else:
        start_date = ""

    return daily_views, start_date


def _load_project_views(work_dir: Path) -> dict[str, float]:
    """Load project views and return monthly dict { "YYYY-MM": views }."""
    project_file = work_dir / "project_views.json"
    with project_file.open(encoding="utf-8") as f:
        project_data = json.load(f)

    project_monthly: dict[str, float] = {}
    for item in project_data:
        date_str = item["date"]  # YYYYMMDD
        month_key = date_str[:6]  # YYYYMM
        views = float(item["views"])
        project_monthly[month_key] = project_monthly.get(month_key, 0.0) + views

    return project_monthly


def generate_chart(work_dir: Path | str) -> dict[str, Any]:
    """Generate a normalized monthly views chart and save as PNG.

    Args:
        work_dir: Path to work directory containing article_views.json and project_views.json.

    Returns:
        Dictionary with chart generation results.
    """
    work_path = Path(work_dir)

    try:
        # Load data
        daily_views, start_date = _load_article_views(work_path)
        project_monthly = _load_project_views(work_path)

        if not daily_views or not start_date:
            # Create an empty chart with a message
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'No article views data available for chart',
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12)
            ax.set_title('Normalized Monthly Views')
        else:
            # Convert daily views to monthly sums (only full months)
            basket_monthly = to_monthly(daily_views, start_date)

            # Normalize by project views
            normalized_monthly = normalize(basket_monthly, project_monthly)

            if not normalized_monthly:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, 'Insufficient data for normalized monthly chart',
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax.transAxes, fontsize=12)
                ax.set_title('Normalized Monthly Views')
            else:
                # Sort months chronologically
                sorted_months = sorted(normalized_monthly.keys())
                values = [normalized_monthly[m] for m in sorted_months]

                # Convert month strings to datetime objects for plotting
                # We'll use the first day of the month for plotting
                dates_plot = [datetime.strptime(month, "%Y-%m").replace(day=1, tzinfo=UTC)
                              for month in sorted_months]

                # Set up the plot
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(dates_plot, values, marker='o', linestyle='-', linewidth=2, markersize=4)
                ax.set_xlabel('Date')
                ax.set_ylabel('Views per million project views')
                ax.set_title('Normalized Monthly Views')
                ax.grid(True, linestyle='--', alpha=0.7)

                # Format the x-axis to show months nicely
                ax.xaxis.set_major_formatter(plt.DateFormatter('%Y-%m'))
                plt.xticks(rotation=45)
                plt.tight_layout()

        # Ensure charts directory exists
        charts_dir = work_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        chart_path = charts_dir / "chart.png"
        fig.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        return {
            "ok": True,
            "data": {
                "chart_path": str(chart_path),
            },
            "warnings": [],
            "next_step": "Chart generated successfully.",
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
            "warnings": [f"Unexpected error during chart generation: {exc!s}"],
            "next_step": "Check your work directory and try again.",
        }