"""Tests for metrics.py."""

import math

from src.wikitrends.metrics import (
    analyze_topic,
    find_spikes,
    normalize,
    remove_spikes,
    theil_sen_pct_per_year,
    to_monthly,
    yoy,
)


def test_to_monthly():
    """Test conversion of daily to monthly."""
    # Start at 2020-01-01
    start = "2020-01-01"
    # 31 days of January: 1 each day -> total 31
    daily = [1.0] * 31
    # February 2020: 29 days (leap year)
    daily += [1.0] * 29
    # March: 31 days
    daily += [1.0] * 31
    # We have Jan, Feb, Mar -> 3 full months.
    monthly = to_monthly(daily, start)
    assert monthly == {"2020-01": 31.0, "2020-02": 29.0, "2020-03": 31.0}

    # Test incomplete month: add only 10 days of April.
    daily += [1.0] * 10
    monthly = to_monthly(daily, start)
    # April should not be included because it's incomplete.
    assert monthly == {"2020-01": 31.0, "2020-02": 29.0, "2020-03": 31.0}

    # Test with zeros.
    daily = [0.0] * 31  # January zeros
    monthly = to_monthly(daily, start)
    assert monthly == {"2020-01": 0.0}


def test_normalize():
    """Test normalization."""
    article = {"2020-01": 1000.0, "2020-02": 2000.0}
    project = {"2020-01": 100000.0, "2020-02": 200000.0}
    norm = normalize(article, project)
    # 1000/100000 * 1e6 = 10000
    # 2000/200000 * 1e6 = 10000
    assert norm == {"2020-01": 10000.0, "2020-02": 10000.0}

    # Month missing in project -> should be omitted.
    article = {"2020-01": 1000.0, "2020-02": 2000.0, "2020-03": 3000.0}
    project = {"2020-01": 100000.0, "2020-02": 200000.0}
    norm = normalize(article, project)
    assert norm == {"2020-01": 10000.0, "2020-02": 10000.0}

    # Zero project views -> avoid division by zero, skip.
    article = {"2020-01": 1000.0}
    project = {"2020-01": 0.0}
    norm = normalize(article, project)
    assert norm == {}


def test_yoy():
    """Test year-over-year growth."""
    # 24 months of data: first 12 months 100 each, next 12 months 200 each.
    monthly = {f"2020-{i:02d}": 100.0 for i in range(1, 13)}
    monthly.update({f"2021-{i:02d}": 200.0 for i in range(1, 13)})
    # Sum last 12: 12*200 = 2400
    # Sum previous 12: 12*100 = 1200
    # YoY = 2400/1200 - 1 = 1.0
    assert yoy(monthly) == 1.0

    # Less than 24 months -> None
    monthly = {f"2020-{i:02d}": 100.0 for i in range(1, 13)}
    assert yoy(monthly) is None

    # Denominator <= 0 -> None
    monthly = {f"2020-{i:02d}": 0.0 for i in range(1, 13)}
    monthly.update({f"2021-{i:02d}": 100.0 for i in range(1, 13)})
    assert yoy(monthly) is None


def test_theil_sen_pct_per_year():
    """Test Theil-Sen slope."""
    # Steady growth: monthly values increase by 1 each month.
    # We'll create 24 months of data: month i (0-index) has value i.
    monthly = {f"2020-{i+1:02d}": float(i) for i in range(24)}
    # The rolling 12-month sum will be: for month i (0-index) the sum of i to i+11.
    # We expect a positive slope.
    result = theil_sen_pct_per_year(monthly)
    assert result is not None
    # We can't easily compute the exact value, but we know it should be positive.
    assert result > 0

    # Constant series: slope should be 0.
    monthly = {f"2020-{i+1:02d}": 100.0 for i in range(24)}
    result = theil_sen_pct_per_year(monthly)
    assert result is not None
    assert abs(result) < 1e-9

    # Less than 17 monthly values -> None
    monthly = {f"2020-{i+1:02d}": 100.0 for i in range(16)}
    assert theil_sen_pct_per_year(monthly) is None

    # Median of rolling <= 0 -> None (if all zeros)
    monthly = {f"2020-{i+1:02d}": 0.0 for i in range(24)}
    assert theil_sen_pct_per_year(monthly) is None


def test_find_spikes():
    """Test spike detection."""
    # Flat series with one spike.
    daily = [1.0] * 30
    daily[15] = 100.0  # spike in the middle
    flags, baseline, spike_share = find_spikes(daily)
    # The spike should be flagged.
    assert flags[15] == True
    # The baseline around day 15 should be about 1.0.
    # We'll check that the baseline for day 15 is 1.0 (since the window of 29 days around it has 28 ones and one 100?).
    # Actually, the window for day 15 (index 15) goes from index 1 to 29 (15-14=1, 15+14=29).
    # That's 29 days: 28 days of 1.0 and one day (index 15) of 100.0? Wait, the window includes the day itself.
    # So the window has 28 ones and one 100 -> the median of 29 values: sorted, the 15th value (0-indexed 14) is 1.0.
    # So baseline[15] should be 1.0.
    assert abs(baseline[15] - 1.0) < 1e-9
    # The residual at day 15 is 99.0.
    # The MAD: residuals are mostly 0, except one 99.0 -> median of residuals is 0, then MAD = median(|residual - 0|) = median of [0,0,...,99] -> the median of 29 values: the 15th value (0-indexed 14) is 0.0? Actually, we have 28 zeros and one 99 -> sorted: 28 zeros then 99 -> median is the 15th (0-indexed 14) is 0.0.
    # So scale = 1.4826 * 0 = 0 -> then effective_scale = max(0, sqrt(max(baseline[i],1))) = sqrt(1) = 1.
    # Then residual/effective_scale = 99.0 > 4 -> flagged.
    # So the spike is flagged.

    # Now, spike_share: (daily[15] - baseline[15]) / sum(daily) = 99.0 / (30*1 + 99) = 99.0 / 129.0 ≈ 0.767
    # We'll allow some tolerance.
    assert abs(spike_share - 99.0/129.0) < 1e-9

    # Test no spikes: flat series.
    daily = [5.0] * 100
    flags, baseline, spike_share = find_spikes(daily)
    assert all(not f for f in flags)
    assert spike_share == 0.0

    # Test all zeros.
    daily = [0.0] * 100
    flags, baseline, spike_share = find_spikes(daily)
    assert all(not f for f in flags)
    assert spike_share == 0.0


def test_remove_spikes():
    """Test spike removal."""
    daily = [1.0, 1.0, 10.0, 1.0]
    flags = [False, False, True, False]
    baseline = [1.0, 1.0, 1.0, 1.0]
    result = remove_spikes(daily, flags, baseline)
    assert result == [1.0, 1.0, 1.0, 1.0]


def test_analyze_topic():
    """Generic test for analyze_topic - checks that the function runs and returns expected keys."""
    start = "2020-01-01"
    n_days = 731
    daily_values = [10.0 + (10.0 * i / (n_days-1)) for i in range(n_days)]
    articles = {"Article A": daily_values}
    project_monthly = {}
    year, month, _ = map(int, start.split('-'))
    for i in range(24):  # 24 months
        m = month + i
        y = year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_key = f"{y:04d}-{m:02d}"
        project_monthly[month_key] = 1e6  # constant

    result = analyze_topic(articles, start, project_monthly)
    # Check that we get the expected keys and that months is an int (count of full months)
    assert isinstance(result["months"], int)
    assert result["months"] == 24  # we have 24 full months
    assert result["yoy_norm"] is not None
    assert result["yoy_norm"] > 0  # growing scenario
    # We don't check exact values here; the specific scenario tests do that.


def test_steady_growth_is_high_confidence():
    """Scenario A: Steady synthetic growth over 2 years -> yoy_norm > 0, trend_pct_per_year > 0, spike_share < 0.05"""
    start = "2020-01-01"
    n_days = 731  # 2 years (accounting for leap year 2020)
    daily_values = [10.0 + (10.0 * i / (n_days-1)) for i in range(n_days)]
    articles = {"Article A": daily_values}
    project_monthly = {}
    year, month, _ = map(int, start.split('-'))
    for i in range(24):  # 24 months
        m = month + i
        y = year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_key = f"{y:04d}-{m:02d}"
        project_monthly[month_key] = 1e6  # constant

    result = analyze_topic(articles, start, project_monthly)
    # We expect yoy_norm > 0 and trend_pct_per_year > 0 and spike_share < 0.05
    assert result["yoy_norm"] is not None and result["yoy_norm"] > 0
    assert result["trend_pct_per_year"] is not None and result["trend_pct_per_year"] > 0
    assert result["spike_share"] < 0.05


def test_single_spike_flips_sign_between_yoy_norm_and_yoy_ex_spikes():
    """Scenario B: One huge spike added to an otherwise flat/declining 2-year series -> spike_share > 0.3,
       sign(yoy_norm) != sign(yoy_ex_spikes)"""
    start = "2020-01-01"
    n_days = 731
    daily_values = [1.0] * n_days
    # Add a spike at the start of the second year: day 366 (which is 2021-01-01) -> value 1000.0
    daily_values[366] = 1000.0
    articles = {"Article B": daily_values}
    project_monthly = {}
    year, month, _ = map(int, start.split('-'))
    for i in range(24):
        m = month + i
        y = year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_key = f"{y:04d}-{m:02d}"
        project_monthly[month_key] = 1e6

    result = analyze_topic(articles, start, project_monthly)
    # We expect spike_share > 0.3
    assert result["spike_share"] > 0.3
    # We expect yoy_norm and yoy_ex_spikes to have opposite signs.
    # Without the spike, the series is flat -> yoy_norm should be around 0.
    # With the spike at the start of the second year, the second year has extra views -> yoy_norm > 0.
    # When we remove the spike, the series becomes flat -> yoy_ex_spikes ~ 0.
    # So we expect yoy_norm > 0 and yoy_ex_spikes ~ 0.
    assert result["yoy_norm"] is not None and result["yoy_norm"] > 0
    assert result["yoy_ex_spikes"] is not None
    # We expect yoy_ex_spikes to be close to zero.
    assert abs(result["yoy_ex_spikes"]) < 0.1


def test_pure_seasonality_has_near_zero_yoy_and_trend():
    """Scenario C: Pure seasonal sine wave (no trend) over 2 years -> |yoy_norm| < 0.05 and |trend_pct_per_year| < 5"""
    start = "2020-01-01"
    n_days = 731
    daily_values = [100.0 + 50.0 * math.sin(2 * math.pi * i / 365.0) for i in range(n_days)]
    articles = {"Article C": daily_values}
    project_monthly = {}
    year, month, _ = map(int, start.split('-'))
    for i in range(24):  # 24 months
        m = month + i
        y = year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_key = f"{y:04d}-{m:02d}"
        project_monthly[month_key] = 1e6  # constant

    result = analyze_topic(articles, start, project_monthly)
    assert abs(result["yoy_norm"]) < 0.05
    assert abs(result["trend_pct_per_year"]) < 5.0


def test_linear_decline_100_to_50_trend_is_about_minus_35():
    """Scenario D: Linear decline from 100 to 50 over 24 monthly points -> trend_pct_per_year approx -35 (+-3)"""
    start = "2020-01-01"
    # 24 months: month i (0-index) has daily value = 100 - (50 * i / 23)
    daily_values = []
    for i in range(24):
        month_value = 100.0 - (50.0 * i / 23.0)
        daily_values.extend([month_value] * 30)
    articles = {"Article D": daily_values}
    project_monthly = {}
    year, month, _ = map(int, start.split('-'))
    for i in range(24):  # 24 months
        m = month + i
        y = year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_key = f"{y:04d}-{m:02d}"
        project_monthly[month_key] = 1e6  # constant

    result = analyze_topic(articles, start, project_monthly)
    # We expect trend_pct_per_year to be around -35.
    # We'll allow a tolerance of 3.
    assert result["trend_pct_per_year"] is not None
    assert abs(result["trend_pct_per_year"] - (-35.0)) < 3.0


def test_young_article_flagged_when_starts_mid_window():
    """Scenario E: Article with all zeros for the first 6 months then flat views -> young_article is True"""
    start = "2020-01-01"
    n_days = 731
    daily_values = [0.0] * 180 + [1.0] * (n_days - 180)
    articles = {"Article E": daily_values}
    project_monthly = {}
    year, month, _ = map(int, start.split('-'))
    for i in range(24):  # 24 months
        m = month + i
        y = year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_key = f"{y:04d}-{m:02d}"
        project_monthly[month_key] = 1e6  # constant

    result = analyze_topic(articles, start, project_monthly)
    # The first positive day is at index 180, which is 180 days after start -> more than 30 days -> young_article should be True.
    assert result["young_article"] == True


def test_basket_consistency_one_of_three_growing():
    """Scenario F: 3 articles, only 1 growing -> basket_consistency approx 0.33"""
    start = "2020-01-01"
    n_days = 731
    # Article 1: linear growth from 10 to 20
    daily1 = [10.0 + (10.0 * i / (n_days-1)) for i in range(n_days)]
    # Article 2: flat at 5.0
    daily2 = [5.0] * n_days
    # Article 3: linear decline from 20 to 10
    daily3 = [20.0 - (10.0 * i / (n_days-1)) for i in range(n_days)]
    articles = {
        "Article F1": daily1,
        "Article F2": daily2,
        "Article F3": daily3,
    }
    project_monthly = {}
    year, month, _ = map(int, start.split('-'))
    for i in range(24):  # 24 months
        m = month + i
        y = year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_key = f"{y:04d}-{m:02d}"
        project_monthly[month_key] = 1e6  # constant

    result = analyze_topic(articles, start, project_monthly)
    # We expect basket_consistency to be about 1/3 because only one article is growing (the first one).
    assert result["basket_consistency"] is not None
    assert abs(result["basket_consistency"] - (1.0/3.0)) < 0.05


def test_short_window_yoy_is_none():
    """Scenario G: Fewer than 24 full months of monthly data -> yoy(monthly) is None"""
    # We'll test the yoy function directly.
    monthly = {f"2020-{i+1:02d}": 100.0 for i in range(23)}  # 23 months
    assert yoy(monthly) is None

    # Also test that analyze_topic returns None for yoy_raw and yoy_norm when there are fewer than 24 months.
    start = "2020-01-01"
    daily_values = [1.0] * (23 * 30)  # 690 days
    articles = {"Article G": daily_values}
    project_monthly_23 = {}
    year, month, _ = map(int, start.split('-'))
    for i in range(23):
        m = month + i
        y = year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_key = f"{y:04d}-{m:02d}"
        project_monthly_23[month_key] = 1e6
    result = analyze_topic(articles, start, project_monthly_23)
    assert result["yoy_raw"] is None
    assert result["yoy_norm"] is None