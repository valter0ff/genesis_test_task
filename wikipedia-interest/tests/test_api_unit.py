import json
from pathlib import Path
from unittest.mock import patch

import pytest

from wikitrends import api, cli


def test_dense_fill_missing_days(fixture_data):
    """Test that missing days in API response are filled with zeros."""
    fixture = fixture_data("per_article_daily_uk_astronomia.json")
    original_items = fixture["json"]["items"]
    filtered_items = original_items[:1]  # Only day 1

    with patch("wikitrends.api._get_json") as mock_get_json:
        mock_get_json.return_value = ({"items": filtered_items}, 200)

        items, _ = api.get_article_views_daily(
            project="uk.wikipedia",
            article="Test Article",
            start_date="20240101",
            end_date="20240102",
        )

        assert len(items) == 2
        assert items[0]["date"] == "20240101"
        assert items[1]["date"] == "20240102"
        assert items[1]["views"] == 0  # Missing day filled with 0


def test_404_response_treated_as_zeros():
    """Test that 404 response is treated as all zeros with a warning."""
    with patch("wikitrends.api._get_json") as mock_get_json:
        mock_get_json.return_value = ({"detail": "Not found"}, 404)

        items, warnings = api.get_article_views_daily(
            project="uk.wikipedia",
            article="Nonexistent Article",
            start_date="20240101",
            end_date="20240102",
        )

        assert len(items) == 2
        assert all(item["views"] == 0 for item in items)
        assert len(warnings) == 1
        assert "No data found" in warnings[0]


def test_429_retry_then_success(tmp_path):
    """Test that 429 status triggers retries and eventually succeeds."""
    mock_responses = []

    mock_resp1 = patch("requests.Response").start()
    mock_resp1.status_code = 429
    mock_responses.append(mock_resp1)

    mock_resp2 = patch("requests.Response").start()
    mock_resp2.status_code = 429
    mock_responses.append(mock_resp2)

    mock_resp3 = patch("requests.Response").start()
    mock_resp3.status_code = 200
    mock_resp3.json.return_value = {
        "items": [{"timestamp": "2024010100", "views": 100}]
    }
    mock_responses.append(mock_resp3)

    call_count = 0

    def mock_get_side_effect(*args, **kwargs):
        nonlocal call_count
        resp = mock_responses[call_count]
        call_count += 1
        return resp

    with patch("requests.get", side_effect=mock_get_side_effect), patch("time.sleep"):
        items, _ = api.get_article_views_daily(
            project="uk.wikipedia",
            article="Test Article 429 Unique",  # Уникальное название статьи, чтобы не попадать в кэш
            start_date="20240101",
            end_date="20240101",
            work_dir=tmp_path,  # Использование изолированной директории
        )

    assert call_count == 3
    assert len(items) == 1
    assert items[0]["views"] == 100


def test_cache_hit_second_call(tmp_path):
    """Test that second identical call uses cache and makes 0 HTTP requests."""
    mock_data = {"items": [{"timestamp": "2024010100", "views": 50}]}

    with patch("requests.get") as mock_http_get:
        mock_resp = patch("requests.Response").start()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_http_get.return_value = mock_resp

        # First call
        items1, warnings1 = api.get_article_views_daily(
            project="uk.wikipedia",
            article="Test Article",
            start_date="20240101",
            end_date="20240101",
            work_dir=tmp_path,
        )

        # Second call
        items2, warnings2 = api.get_article_views_daily(
            project="uk.wikipedia",
            article="Test Article",
            start_date="20240101",
            end_date="20240101",
            work_dir=tmp_path,
        )

        assert mock_http_get.call_count == 1
        assert items1 == items2
        assert warnings1 == warnings2


def test_invalid_date_returns_exit_code_2():
    """Test that invalid date returns exit code 2."""
    with patch("sys.argv", ["wikitrends", "fetch", "--project", "uk.wikipedia", "--article", "Test", "--start", "20240230", "--end", "20240102"]), \
         pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 2


def test_valid_date_passes_validation():
    """Test valid dates."""
    assert cli._validate_date("20240101")
    assert not cli._validate_date("20240230")


@pytest.fixture
def fixture_data():
    """Fixture to load test data from fixtures directory relative to test location."""
    fixtures_dir = Path(__file__).parent / "fixtures"

    def _load_fixture(filename):
        with (fixtures_dir / filename).open(encoding="utf-8") as f:
            return json.load(f)

    return _load_fixture
