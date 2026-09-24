import json
import subprocess
from datetime import UTC, datetime, timedelta

import pytest


@pytest.mark.live
def test_zero_view_days_are_omitted():
    """Fetch 90 days of daily views for a low-traffic article and assert that zero-view days are omitted."""
    # Use a low-traffic article; we use "Астрономія" (may or may not have zero days, but test will fail if none)
    article = "Астрономія"
    project = "uk.wikipedia"

    # Compute date range: last 90 days up to yesterday
    end_date = datetime.now(UTC) - timedelta(days=1)
    start_date = end_date - timedelta(days=89)  # inclusive, so 90 days total
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    # Run the fetch command via the CLI
    cmd = [
        "wikitrends",
        "fetch",
        "--project",
        project,
        "--article",
        article,
        "--start",
        start_str,
        "--end",
        end_str,
        "--granularity",
        "daily",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    # Parse JSON output
    output = json.loads(result.stdout)
    assert output["ok"], f"Fetch failed: {output}"
    data = output["data"]
    # The data should be a list of items (daily views)
    items = data
    # Assert that the number of items is less than 90 (i.e., some days with zero views are omitted)
    assert len(items) < 90, f"Expected less than 90 items (zero-view days omitted), got {len(items)} items. This may indicate that the article had views every day or the dense-fill logic is not implemented."