"""Metrics calculation."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta


def to_monthly(daily: list[float], start: str) -> dict[str, float]:
    """Convert daily series to monthly sums, only for full months.

    Args:
        daily: list of floats, one value per calendar day starting at `start`.
        start: ISO date string (YYYY-MM-DD) of the first day in `daily`.

    Returns:
        dict mapping "YYYY-MM" to the sum of daily values for that month,
        but only if the month is complete (every one of its days is present in `daily`).
    """
    start_date = date.fromisoformat(start)
    monthly_sums: dict[str, float] = defaultdict(float)
    day_counts: dict[str, int] = defaultdict(int)

    for i, value in enumerate(daily):
        current_date = start_date + timedelta(days=i)
        month_key = current_date.strftime("%Y-%m")
        monthly_sums[month_key] += value
        day_counts[month_key] += 1

    # Determine which months are complete.
    result: dict[str, float] = {}
    for month_key, total in monthly_sums.items():
        year, month = map(int, month_key.split("-"))
        # First day of the month.
        month_start = date(year, month, 1)
        # First day of the next month.
        if month == 12:
            next_month_start = date(year + 1, 1, 1)
        else:
            next_month_start = date(year, month + 1, 1)
        days_in_month = (next_month_start - month_start).days
        if day_counts[month_key] == days_in_month:
            result[month_key] = total
    return result


def normalize(article_monthly: dict[str, float], project_monthly: dict[str, float]) -> dict[str, float]:
    """Normalize article monthly views by project monthly views.

    Args:
        article_monthly: dict mapping "YYYY-MM" to article views for that month.
        project_monthly: dict mapping "YYYY-MM" to project views for that month.

    Returns:
        dict mapping "YYYY-MM" to normalized views (article / project * 1e6)
        only for months present in both.
    """
    result: dict[str, float] = {}
    for month, article_views in article_monthly.items():
        if month in project_monthly:
            project_views = project_monthly[month]
            if project_views > 0:
                result[month] = article_views / project_views * 1_000_000
    return result


def yoy(monthly: dict[str, float]) -> float | None:
    """Year-over-year growth rate.

    Args:
        monthly: dict mapping "YYYY-MM" to float values.

    Returns:
        (sum of last 12 monthly values) / (sum of previous 12) - 1,
        or None if fewer than 24 monthly values or denominator <= 0.
    """
    if len(monthly) < 24:
        return None

    sorted_months = sorted(monthly.keys())
    last_12 = sorted_months[-12:]
    prev_12 = sorted_months[-24:-12]

    sum_last = sum(monthly[m] for m in last_12)
    sum_prev = sum(monthly[m] for m in prev_12)

    if sum_prev <= 0:
        return None
    return sum_last / sum_prev - 1.0


def theil_sen_pct_per_year(monthly: dict[str, float]) -> float | None:
    """Compute Theil-Sen slope on 12-month rolling sum of monthly values.

    Args:
        monthly: dict mapping "YYYY-MM" to float values.

    Returns:
        slope as % per year, or None if fewer than 6 rolling values (i.e. fewer than 17 monthly values)
        or median of rolling <= 0.
    """
    if len(monthly) < 17:
        return None

    sorted_months = sorted(monthly.keys())
    monthly_values = [monthly[m] for m in sorted_months]

    # Compute 12-month rolling sum.
    rolling: list[float] = []
    for i in range(len(monthly_values) - 11):
        rolling.append(sum(monthly_values[i:i + 12]))

    if len(rolling) < 6:
        return None

    # Median of rolling values.
    sorted_rolling = sorted(rolling)
    n = len(sorted_rolling)
    if n % 2 == 1:
        median_rolling = sorted_rolling[n // 2]
    else:
        median_rolling = (sorted_rolling[n // 2 - 1] + sorted_rolling[n // 2]) / 2.0

    if median_rolling <= 0:
        return None

    # All pairwise slopes.
    slopes: list[float] = []
    for i in range(len(rolling)):
        for j in range(i + 1, len(rolling)):
            slopes.append((rolling[j] - rolling[i]) / (j - i))

    slopes.sort()
    n_slopes = len(slopes)
    if n_slopes % 2 == 1:
        theil_sen_slope = slopes[n_slopes // 2]
    else:
        theil_sen_slope = (slopes[n_slopes // 2 - 1] + slopes[n_slopes // 2]) / 2.0

    # Convert to % per year.
    return theil_sen_slope * 12 / median_rolling * 100.0


def find_spikes(daily: list[float]) -> tuple[list[bool], list[float], float]:
    """Detect spikes in daily series using robust z-score.

    Args:
        daily: list of floats, one value per calendar day.

    Returns:
        flags: list of booleans, True for spike days.
        baseline: list of floats, the rolling median baseline for each day.
        spike_share: fraction of total views that come from spike days (above baseline).
    """
    from statistics import median

    n = len(daily)
    if n == 0:
        return [], [], 0.0

    half_window = 14
    baseline: list[float] = [0.0] * n
    for i in range(n):
        start = max(0, i - half_window)
        end = min(n, i + half_window + 1)
        window = daily[start:end]
        baseline[i] = median(window)

    residuals = [daily[i] - baseline[i] for i in range(n)]
    median_residual = median(residuals)
    mad = median([abs(r - median_residual) for r in residuals])
    scale = 1.4826 * mad

    effective_scale = [max(scale, math.sqrt(max(b, 1))) for b in baseline]
    flags = [residuals[i] / effective_scale[i] > 4 for i in range(n)]

    spike_views = sum(daily[i] - baseline[i] for i in range(n) if flags[i])
    total_views = sum(daily)
    spike_share = spike_views / total_views if total_views != 0 else 0.0
    return flags, baseline, spike_share


def remove_spikes(daily: list[float], flags: list[bool], baseline: list[float]) -> list[float]:
    """Replace flagged days with baseline value."""
    return [baseline[i] if flags[i] else daily[i] for i in range(len(daily))]


def analyze_topic(articles: dict[str, list[float]], start: str, project_monthly: dict[str, float]) -> dict:
    """Analyze a topic (set of articles) and return metrics."""
    if not articles:
        return {
            "months": {},
            "yoy_raw": None,
            "yoy_norm": None,
            "yoy_ex_spikes": None,
            "trend_pct_per_year": None,
            "spike_share": 0.0,
            "spike_days": 0,
            "volume": {"median_daily_12m": 0.0, "total_12m": 0.0},
            "first_seen": None,
            "young_article": True,
            "basket_consistency": None,
        }

    # Use the length of the first article's daily list.
    first_article_daily = next(iter(articles.values()))
    n_days = len(first_article_daily)

    basket_daily = [0.0] * n_days
    for daily_list in articles.values():
        for i in range(min(n_days, len(daily_list))):
            basket_daily[i] += daily_list[i]

    basket_monthly = to_monthly(basket_daily, start)
    normalized_monthly = normalize(basket_monthly, project_monthly)

    yoy_raw = yoy(basket_monthly)
    yoy_norm = yoy(normalized_monthly)

    flags, baseline, spike_share = find_spikes(basket_daily)
    basket_daily_no_spikes = remove_spikes(basket_daily, flags, baseline)
    basket_monthly_no_spikes = to_monthly(basket_daily_no_spikes, start)
    normalized_monthly_no_spikes = normalize(basket_monthly_no_spikes, project_monthly)
    yoy_ex_spikes = yoy(normalized_monthly_no_spikes)

    trend_pct_per_year = theil_sen_pct_per_year(normalized_monthly)

    spike_days = sum(1 for f in flags if f)

    if n_days >= 365:
        last_365 = basket_daily[-365:]
    else:
        last_365 = basket_daily[:]

    total_12m = sum(last_365)
    sorted_last_365 = sorted(last_365)
    n_last = len(sorted_last_365)
    if n_last == 0:
        median_daily_12m = 0.0
    elif n_last % 2 == 1:
        median_daily_12m = sorted_last_365[n_last // 2]
    else:
        median_daily_12m = (sorted_last_365[n_last // 2 - 1] + sorted_last_365[n_last // 2]) / 2.0

    first_seen_idx = None
    for i, value in enumerate(basket_daily):
        if value > 0:
            first_seen_idx = i
            break
    first_seen: str | None = None
    if first_seen_idx is not None:
        start_date = date.fromisoformat(start)
        first_seen_date = start_date + timedelta(days=first_seen_idx)
        first_seen = first_seen_date.isoformat()

    young_article = False
    if first_seen_idx is None:
        young_article = True
    else:
        if first_seen_idx > 30:
            young_article = True

    basket_consistency: float | None = None
    if len(articles) > 1:
        positive_count = 0
        for daily_list in articles.values():
            article_monthly = to_monthly(daily_list, start)
            article_normalized = normalize(article_monthly, project_monthly)
            article_yoy_norm = yoy(article_normalized)
            if article_yoy_norm is not None and article_yoy_norm > 0:
                positive_count += 1
        basket_consistency = positive_count / len(articles)

    return {
        "months": normalized_monthly,
        "yoy_raw": yoy_raw,
        "yoy_norm": yoy_norm,
        "yoy_ex_spikes": yoy_ex_spikes,
        "trend_pct_per_year": trend_pct_per_year,
        "spike_share": spike_share,
        "spike_days": spike_days,
        "volume": {
            "median_daily_12m": median_daily_12m,
            "total_12m": total_12m,
        },
        "first_seen": first_seen,
        "young_article": young_article,
        "basket_consistency": basket_consistency,
    }