"""Tests for reliability.py."""

from src.wikitrends.metrics import analyze_topic
from src.wikitrends.reliability import assess


def test_window_short():
    """Test scenario with fewer than 24 full months of data -> confidence low, flags contains window_short."""
    # Create daily data for only 12 months - less than 24 months of monthly data
    # We need data that gives us exactly 12 full months
    start_date = "2025-01-01"  # Start 1 year ago

    # Article data: steady growth over 12 months
    # 365 days for non-leap year 2025
    article_daily = [10.0] * 365

    # Project data: also steady to allow normalization
    project_daily = [1000.0] * 365

    articles = {"Article1": article_daily}

    # Convert daily to monthly for project data (needed for analyze_topic)
    from src.wikitrends.metrics import to_monthly
    project_monthly = to_monthly(project_daily, start_date)

    m = analyze_topic(articles, start_date, project_monthly)

    # Should have only 12 months of data (< 24)
    assert m["months"] == 12

    result = assess(m)
    assert result["confidence"] == "low"
    assert "window_short" in result["flags"]
    # window_short should force low confidence, so level should be 0 (low)


def test_very_low_volume():
    """Test scenario with near-zero daily views -> confidence low, flags contains very_low_volume."""
    start_date = "2024-01-01"  # 2 years of data

    # Very low article views: 1 view per day for 2 years
    # 2024 (leap) + 2025 = 366 + 365 = 731 days
    article_daily = [1.0] * 731

    # Normal project views
    project_daily = [1000.0] * 731

    articles = {"Article1": article_daily}

    from src.wikitrends.metrics import to_monthly
    project_monthly = to_monthly(project_daily, start_date)

    m = analyze_topic(articles, start_date, project_monthly)

    # Should have 24 months of data
    assert m["months"] == 24
    # Total views should be low: 1 * 731 = 731 < 1000
    assert m["volume"]["total_12m"] < 1000

    result = assess(m)
    assert result["confidence"] == "low"
    assert "very_low_volume" in result["flags"]


def test_low_daily_volume_alone():
    """Test scenario with median ~12/day but total_12m > 1000, everything else clean -> confidence medium, flags == [low_daily_volume]."""
    start_date = "2024-01-01"  # 2 years of data

    # Low daily views: median ~12/day but total > 1000
    # Use slightly increasing data to ensure positive yoy_raw
    article_daily = []
    for day in range(731):
        # Start at 11.5 and increase very slightly to 12.5 over 2 years
        value = 11.5 + (1.0 * day / 731)
        article_daily.append(value)

    # Project views: grow at SLIGHTLY slower rate than article views
    # This ensures normalized views show slight growth (matching yoy_raw > 0)
    # Article grows from 11.5 to 12.5 (ratio of 12.5/11.5 = 1.087)
    # Let project grow from 1000 to 1000 * 1.05 = 1050 (slower growth)
    # So normalized views = article/project will grow slightly
    project_daily = []
    for day in range(731):
        # Project grows from 1000 to 1050 over the period
        project_value = 1000.0 + (50.0 * day / 731)
        project_daily.append(project_value)

    articles = {"Article1": article_daily}

    from src.wikitrends.metrics import to_monthly
    project_monthly = to_monthly(project_daily, start_date)

    m = analyze_topic(articles, start_date, project_monthly)

    # Should have 24 months of data
    assert m["months"] == 24
    # Median daily should be around 12
    assert 11.0 <= m["volume"]["median_daily_12m"] <= 13.0
    # Total views should be > 1000
    assert m["volume"]["total_12m"] > 1000
    # No spikes, not young article, consistent basket (only 1 article), no platform trend
    assert m["spike_share"] == 0.0
    assert m["young_article"] == False
    assert m["basket_consistency"] is None  # Only 1 article
    assert m["yoy_raw"] is not None and m["yoy_norm"] is not None
    assert m["yoy_ex_spikes"] is not None
    # yoy_norm and yoy_ex_spikes should have same sign (no spikes)
    assert (m["yoy_norm"] >= 0) == (m["yoy_ex_spikes"] >= 0)
    # yoy_raw and yoy_norm should have same sign (no platform trend) - both should be positive
    assert m["yoy_raw"] > 0
    assert m["yoy_norm"] > 0

    result = assess(m)
    assert result["confidence"] == "medium"
    assert result["flags"] == ["low_daily_volume"]


def test_spike_driven_sign():
    """Test scenario with flat/declining series with one huge spike added -> flags contains spike_driven_sign, confidence low."""
    start_date = "2024-01-01"  # 2 years of data

    # Create declining series: 30 views/day decreasing to 10 views/day over 2 years
    article_daily = []
    for day in range(731):
        # Decline from 30 to 10 over 731 days
        value = 30.0 - (20.0 * day / 731)
        article_daily.append(value)

    # Add one huge spike in the second half to make yoy_norm positive but yoy_ex_spikes negative
    article_daily[500] = 8000.0  # Large spike

    # Normal project views
    project_daily = [1000.0] * 731

    articles = {"Article1": article_daily}

    from src.wikitrends.metrics import to_monthly
    project_monthly = to_monthly(project_daily, start_date)

    m = analyze_topic(articles, start_date, project_monthly)

    # Should have 24 months of data
    assert m["months"] == 24
    # Should have significant spike share
    assert m["spike_share"] > 0.3
    # Check that we have values for yoy_norm and yoy_ex_spikes
    assert m["yoy_norm"] is not None
    assert m["yoy_ex_spikes"] is not None
    # With declining baseline (-) and large positive spike:
    # - yoy_norm: likely positive (last 12 months includes spike vs previous 12 months mostly baseline)
    # - yoy_ex_spikes: should be negative (reflects the declining baseline with spike removed)
    # So they should have different signs, triggering spike_driven_sign

    result = assess(m)
    # Should be low confidence due to spike_driven_sign forcing low
    assert result["confidence"] == "low"
    assert "spike_driven_sign" in result["flags"]


def test_young_article():
    """Test scenario with series with zeros for first 6 months then flat -> flags contains young_article."""
    start_date = "2024-01-01"  # 2 years of data

    # Article with zero views for first 6 months (~180 days), then 25 views/day
    # 6 months ≈ 180 days (approximate)
    article_daily = [0.0] * 180 + [25.0] * (731 - 180)

    # Normal project views
    project_daily = [1000.0] * 731

    articles = {"Article1": article_daily}

    from src.wikitrends.metrics import to_monthly
    project_monthly = to_monthly(project_daily, start_date)

    m = analyze_topic(articles, start_date, project_monthly)

    # Should have 24 months of data
    assert m["months"] == 24
    # Article first seen after day 180, which is > 30 days into window
    assert m["young_article"] == True
    assert m["first_seen"] is not None
    # Median should be > 20 now (since we're using 25 views/day after 6 months)
    assert m["volume"]["median_daily_12m"] > 20

    result = assess(m)
    # Should be medium confidence (only young_article downgrade)
    assert result["confidence"] == "medium"
    assert "young_article" in result["flags"]


def test_inconsistent_basket():
    """Test scenario with 3 articles, only 1 growing -> flags contains inconsistent_basket."""
    start_date = "2024-01-01"  # 2 years of data

    # Article 1: growing (5 -> 15 views/day over 2 years)
    article1_daily = []
    for day in range(731):
        # Linear growth from 5 to 15 over 731 days
        value = 5.0 + (10.0 * day / 731)
        article1_daily.append(value)

    # Article 2: flat/declining (10 -> 5 views/day)
    article2_daily = []
    for day in range(731):
        value = 10.0 - (5.0 * day / 731)
        article2_daily.append(value)

    # Article 3: flat/declining (10 -> 5 views/day)
    article3_daily = []
    for day in range(731):
        value = 10.0 - (5.0 * day / 731)
        article3_daily.append(value)

    articles = {
        "Article1": article1_daily,
        "Article2": article2_daily,
        "Article3": article3_daily
    }

    # Normal project views
    project_daily = [1000.0] * 731

    from src.wikitrends.metrics import to_monthly
    project_monthly = to_monthly(project_daily, start_date)

    m = analyze_topic(articles, start_date, project_monthly)

    # Should have 24 months of data
    assert m["months"] == 24
    # Should have basket_consistency < 0.5 (only 1 out of 3 articles growing)
    assert m["basket_consistency"] is not None
    assert m["basket_consistency"] < 0.5

    result = assess(m)
    # Should be downgraded for inconsistent_basket
    assert "inconsistent_basket" in result["flags"]
    # Depending on other factors, confidence could be medium or low
    # But at least the flag should be present


def test_platform_trend():
    """Test scenario with flat raw article views but project totals declining ~30%/year -> flags contains platform_trend."""
    start_date = "2024-01-01"  # 2 years of data

    # Article views: flat over time (15 views/day constant)
    article_daily = [15.0] * 731

    # Project views: declining ~30% per year
    # Year 1 (2024, leap year): 366 days at 1000 views/day
    # Year 2 (2025): 365 days at 700 views/day (30% decline)
    project_daily = []
    for day in range(731):
        if day < 366:  # First year (2024, leap year)
            project_daily.append(1000.0)
        else:  # Second year (2025)
            project_daily.append(700.0)

    articles = {"Article1": article_daily}

    from src.wikitrends.metrics import to_monthly
    project_monthly = to_monthly(project_daily, start_date)

    m = analyze_topic(articles, start_date, project_monthly)

    # Should have 24 months of data
    assert m["months"] == 24
    # Raw article views should be flat (yoy_raw ~ 0)
    # Normalized views should show growth because project views declined
    # So yoy_raw and yoy_norm should have different signs

    result = assess(m)
    # Should be downgraded for platform_trend
    assert "platform_trend" in result["flags"]


def test_all_clear():
    """Test scenario with steady growth, no other issues -> confidence high, flags == []."""
    start_date = "2024-01-01"  # 2 years of data

    # Article views: steady growth (20 -> 30 views/day over 2 years)
    # Start at 20 to ensure median > 20
    article_daily = []
    for day in range(731):
        value = 20.0 + (10.0 * day / 731)  # Grows from 20 to 30
        article_daily.append(value)

    # Project views: stable (constant)
    project_daily = [1000.0] * 731

    articles = {"Article1": article_daily}

    from src.wikitrends.metrics import to_monthly
    project_monthly = to_monthly(project_daily, start_date)

    m = analyze_topic(articles, start_date, project_monthly)

    # Should have 24 months of data
    assert m["months"] == 24
    # Should have growth
    assert m["yoy_norm"] is not None and m["yoy_norm"] > 0
    # No spikes
    assert m["spike_share"] == 0.0
    # Not young article (views from day 1)
    assert m["young_article"] == False
    # Consistent basket (only 1 article, so basket_consistency is None)
    assert m["basket_consistency"] is None
    # No platform trend (project views stable)
    assert m["yoy_raw"] is not None and m["yoy_norm"] is not None
    assert (m["yoy_raw"] >= 0) == (m["yoy_norm"] >= 0)
    # No spike-driven sign (no spikes)
    assert m["yoy_ex_spikes"] is not None
    assert (m["yoy_norm"] >= 0) == (m["yoy_ex_spikes"] >= 0)
    # Good volume - median should be around 25
    assert m["volume"]["median_daily_12m"] >= 20
    assert m["volume"]["total_12m"] >= 1000

    result = assess(m)
    # Should be high confidence with no flags
    assert result["confidence"] == "high"
    assert result["flags"] == []
    # Should have all_clear reason when no other flags
    if len(result["flags"]) == 0:
        # When flags is empty, the assess function uses ["all_clear"] as codes
        # Check for the English "all_clear" message
        assert any("No reliability warnings" in reason and "enough data" in reason for reason in result["reasons"])


if __name__ == "__main__":
    # Run the tests
    import pytest
    pytest.main([__file__, "-v"])