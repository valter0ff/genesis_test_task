"""Analysis engine for Wikipedia pageviews data."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any


def _load_cached_data(work_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Load cached article views and project views from work directory.

    Returns:
        Tuple of (article_views, project_views, warnings)
    """
    warnings = []

    # Load article views
    article_file = work_dir / "article_views.json"
    if not article_file.exists():
        msg = f"Article views data not found in {article_file}. Run 'wikitrends fetch' first."
        raise FileNotFoundError(msg)

    try:
        with article_file.open(encoding="utf-8") as f:
            article_data = json.load(f)
        article_views = article_data if isinstance(article_data, list) else []
    except json.JSONDecodeError as exc:
        msg = f"Failed to parse article views data: {exc}"
        raise ValueError(msg) from exc

    # Load project views (if available)
    project_file = work_dir / "project_views.json"
    project_views = []
    if project_file.exists():
        try:
            with project_file.open(encoding="utf-8") as f:
                project_data = json.load(f)
            project_views = project_data if isinstance(project_data, list) else []
        except json.JSONDecodeError as exc:
            warnings.append(f"Failed to parse project views data: {exc}")
    else:
        warnings.append("Project views data not found. Normalization will be skipped.")

    return article_views, project_views, warnings


def _normalize_views(
    article_views: list[dict[str, Any]],
    project_views: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Normalize article views using project aggregate views.

    Args:
        article_views: List of dicts with 'date' and 'views' keys
        project_views: List of dicts with 'date' and 'views' keys (monthly)

    Returns:
        List of dicts with original data plus 'normalized_views'
    """
    if not project_views:
        # If no project data, return original views as normalized
        for item in article_views:
            item["normalized_views"] = item["views"]
        return article_views

    # Create lookup for project views by month (YYYYMM)
    project_by_month: dict[str, float] = {}
    for item in project_views:
        date_str = item["date"]  # YYYYMMDD
        month_key = date_str[:6]  # YYYYMM
        project_by_month[month_key] = float(item["views"])

    # Normalize each article view
    normalized_views = []
    for item in article_views:
        date_str = item["date"]
        month_key = date_str[:6]
        article_view_count = float(item["views"])

        if month_key in project_by_month and project_by_month[month_key] > 0:
            # Normalize: views per million project views
            normalized = (article_view_count / project_by_month[month_key]) * 1_000_000
        else:
            # Fallback to raw views if project data missing
            normalized = article_view_count

        normalized_item = item.copy()
        normalized_item["normalized_views"] = normalized
        normalized_views.append(normalized_item)

    return normalized_views


def _calculate_summary_statistics(views: list[float]) -> dict[str, Any]:
    """Calculate summary statistics for a series of views.

    Args:
        views: List of view counts

    Returns:
        Dictionary with statistics
    """
    if not views:
        return {
            "mean": 0.0,
            "median": 0.0,
            "max": 0.0,
            "min": 0.0,
            "total": 0.0,
            "peak_date": None,
        }

    return {
        "mean": float(statistics.mean(views)),
        "median": float(statistics.median(views)),
        "max": float(max(views)),
        "min": float(min(views)),
        "total": float(sum(views)),
    }


def _calculate_last_12_months_metrics(data: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate total and median views for the last 12 months of data.

    Args:
        data: List of dicts with 'date' and 'normalized_views' keys, sorted by date ascending

    Returns:
        Dictionary with 'total_views_12m' and 'median_views_12m'
    """
    if not data:
        return {"total_views_12m": 0.0, "median_views_12m": 0.0}

    # Data should already be sorted by date ascending, but let's ensure it
    sorted_data = sorted(data, key=lambda x: x["date"])

    # Take the last 365 days (approximately 12 months)
    # If we have less than 365 days, use all available data
    last_12m_data = sorted_data[-365:] if len(sorted_data) > 365 else sorted_data

    # Extract normalized views for the last 12 months
    views = [item["normalized_views"] for item in last_12m_data]

    if not views:
        return {"total_views_12m": 0.0, "median_views_12m": 0.0}

    return {
        "total_views_12m": float(sum(views)),
        "median_views_12m": float(statistics.median(views)),
    }


def _detect_spikes_zscore(views: list[float], threshold: float = 3.5) -> list[bool]:
    """Detect spikes using z-score method.

    Args:
        views: List of view counts
        threshold: Z-score threshold for spike detection (default 3.5)

    Returns:
        List of booleans indicating spike positions
    """
    if len(views) < 2:
        return [False] * len(views)

    mean_val = statistics.mean(views)
    try:
        stdev_val = statistics.stdev(views)
    except statistics.StatisticsError:
        # Not enough variation for stdev
        return [False] * len(views)

    if stdev_val == 0:
        return [False] * len(views)

    z_scores = [(abs(v - mean_val) / stdev_val) for v in views]
    return [z > threshold for z in z_scores]


def _calculate_trend_slope(views: list[float]) -> float:
    """Calculate trend slope using linear regression.

    Args:
        views: List of view counts over time

    Returns:
        Slope of the trend line (views per time unit)
    """
    if len(views) < 2:
        return 0.0

    # Simple linear regression: y = mx + b
    # where x is time index (0, 1, 2, ...) and y is views
    n = len(views)
    x_vals = list(range(n))

    # Calculate sums needed for slope formula
    sum_x = sum(x_vals)
    sum_y = sum(views)
    sum_xy = sum(x * y for x, y in zip(x_vals, views))
    sum_x2 = sum(x * x for x in x_vals)

    # Slope m = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x*sum_x)
    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    return float(slope)


def _calculate_relative_growth(views: list[float]) -> float:
    """Calculate relative growth over the period.

    Args:
        views: List of view counts over time

    Returns:
        Relative growth as fraction (e.g., 0.5 for 50% growth)
    """
    if len(views) < 2:
        return 0.0

    first_views = views[0]
    last_views = views[-1]

    if first_views == 0:
        return float('inf') if last_views > 0 else 0.0

    return (last_views - first_views) / first_views


def analyze_data(
    work_dir: Path | str,
) -> dict[str, Any]:
    """Analyze Wikipedia pageviews data from work directory.

    Args:
        work_dir: Path to work directory containing cached data

    Returns:
        Dictionary with analysis results
    """
    work_path = Path(work_dir)

    # Load cached data
    try:
        article_views, project_views, warnings = _load_cached_data(work_path)
    except (FileNotFoundError, ValueError) as exc:
        return {
            "ok": False,
            "data": {},
            "warnings": [str(exc)],
            "next_step": "Run 'wikitrends fetch' to generate data first.",
        }

    if not article_views:
        return {
            "ok": False,
            "data": {},
            "warnings": ["No article views data found."],
            "next_step": "Check that fetch command completed successfully.",
        }

    # Extract dates and views
    dates = [item["date"] for item in article_views]
    raw_views = [item["views"] for item in article_views]

    # Normalize views
    normalized_article_views = _normalize_views(article_views, project_views)
    normalized_views = [item["normalized_views"] for item in normalized_article_views]

    # Calculate statistics for raw views
    raw_stats = _calculate_summary_statistics(raw_views)

    # Calculate statistics for normalized views
    norm_stats = _calculate_summary_statistics(normalized_views)

    # Detect spikes
    raw_spikes = _detect_spikes_zscore(raw_views)
    norm_spikes = _detect_spikes_zscore(normalized_views)

    # Calculate trends
    raw_trend_slope = _calculate_trend_slope(raw_views)
    norm_trend_slope = _calculate_trend_slope(normalized_views)

    # Calculate relative growth
    raw_relative_growth = _calculate_relative_growth(raw_views)
    norm_relative_growth = _calculate_relative_growth(normalized_views)

    # Find peak dates
    raw_peak_idx = raw_views.index(max(raw_views)) if raw_views else None
    norm_peak_idx = normalized_views.index(max(normalized_views)) if normalized_views else None

    raw_peak_date = dates[raw_peak_idx] if raw_peak_idx is not None else None
    norm_peak_date = dates[norm_peak_idx] if norm_peak_idx is not None else None

    # Calculate spike statistics
    raw_spike_count = sum(raw_spikes)
    norm_spike_count = sum(norm_spikes)
    raw_spike_share = (raw_spike_count / len(raw_views)) if raw_views else 0.0
    norm_spike_share = (norm_spike_count / len(normalized_views)) if normalized_views else 0.0

    # Calculate 12-month metrics for normalized views
    last_12m_metrics = _calculate_last_12_months_metrics(normalized_article_views)

    # Prepare result
    result = {
        "ok": True,
        "data": {
            "date_range": {
                "start": dates[0] if dates else None,
                "end": dates[-1] if dates else None,
                "days": len(dates),
            },
            "raw_views": {
                "statistics": raw_stats,
                "trend_slope_per_day": raw_trend_slope,
                "relative_growth": raw_relative_growth,
                "peak_date": raw_peak_date,
                "peak_value": raw_stats["max"],
                "spike_count": raw_spike_count,
                "spike_share": raw_spike_share,
            },
            "normalized_views": {
                "statistics": norm_stats,
                "trend_slope_per_day": norm_trend_slope,
                "relative_growth": norm_relative_growth,
                "peak_date": norm_peak_date,
                "peak_value": norm_stats["max"],
                "spike_count": norm_spike_count,
                "spike_share": norm_spike_share,
                "total_views_12m": last_12m_metrics["total_views_12m"],
                "median_views_12m": last_12m_metrics["median_views_12m"],
            },
            "notes": [
                "Normalized views = (article views / project views) * 1,000,000",
                "Trend slope is in views per day",
                "Relative growth = (end - start) / start",
                "Spike detection uses z-score with threshold 3.5",
                "12-month metrics are based on the last 365 days of data",
            ],
        },
        "warnings": warnings,
        "next_step": "Run 'wikitrends report' to generate PDF charts and reliability assessment.",
    }

    return result