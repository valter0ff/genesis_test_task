import json
import subprocess
from datetime import UTC, datetime, timedelta

import pytest


@pytest.mark.live
def test_dense_fill_returns_all_days():
    """Fetch 90 days of daily views and assert that dense fill returns exactly 90 days."""
    article = "Астрономія"
    project = "uk.wikipedia"

    end_date = datetime.now(UTC) - timedelta(days=1)
    start_date = end_date - timedelta(days=89)  # 90 days inclusive
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

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
    output = json.loads(result.stdout)
    assert output["ok"], f"Fetch failed: {output}"
    data = output["data"]

    # Dense fill guarantees we get exactly 90 days of data
    assert len(data) == 90, f"Expected exactly 90 items with dense fill, got {len(data)}"
