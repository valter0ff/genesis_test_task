"""Unit tests for the analysis engine."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from wikitrends import analyze, cli


def test_load_cached_data_success():
    """Test loading cached data successfully."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)

        # Create test article views data
        article_views = [
            {"date": "20240101", "views": 100},
            {"date": "20240102", "views": 150},
            {"date": "20240103", "views": 200},
        ]
        article_file = work_path / "article_views.json"
        with article_file.open("w", encoding="utf-8") as f:
            json.dump(article_views, f)

        # Create test project views data
        project_views = [
            {"date": "20240101", "views": 1000000},
            {"date": "20240201", "views": 1100000},
        ]
        project_file = work_path / "project_views.json"
        with project_file.open("w", encoding="utf-8") as f:
            json.dump(project_views, f)

        # Test loading
        loaded_article, loaded_project, warnings = analyze._load_cached_data(work_path)

        assert loaded_article == article_views
        assert loaded_project == project_views
        assert warnings == []


def test_load_cached_data_missing_article():
    """Test loading when article views file is missing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)

        with pytest.raises(FileNotFoundError, match="Article views data not found"):
            analyze._load_cached_data(work_path)


def test_load_cached_data_invalid_json():
    """Test loading with invalid JSON."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)

        # Create invalid JSON file
        article_file = work_path / "article_views.json"
        with article_file.open("w", encoding="utf-8") as f:
            f.write("invalid json")

        with pytest.raises(ValueError, match="Failed to parse article views data"):
            analyze._load_cached_data(work_path)


def test_normalize_views_with_project_data():
    """Test normalization with project data."""
    article_views = [
        {"date": "20240101", "views": 1000},
        {"date": "20240102", "views": 2000},
    ]

    project_views = [
        {"date": "20240101", "views": 1000000},  # January: 1M views
        {"date": "20240201", "views": 1200000},  # February: 1.2M views
    ]

    normalized = analyze._normalize_views(article_views, project_views)

    # January: (1000 / 1000000) * 1000000 = 1000
    # January: (2000 / 1000000) * 1000000 = 2000
    assert normalized[0]["normalized_views"] == 1000.0
    assert normalized[1]["normalized_views"] == 2000.0


def test_normalize_views_without_project_data():
    """Test normalization without project data (fallback to raw views)."""
    article_views = [
        {"date": "20240101", "views": 1000},
        {"date": "20240102", "views": 2000},
    ]

    normalized = analyze._normalize_views(article_views, [])

    assert normalized[0]["normalized_views"] == 1000.0
    assert normalized[1]["normalized_views"] == 2000.0


def test_calculate_summary_statistics():
    """Test summary statistics calculation."""
    views = [100, 200, 300, 400, 500]

    stats = analyze._calculate_summary_statistics(views)

    assert stats["mean"] == 300.0
    assert stats["median"] == 300.0
    assert stats["max"] == 500.0
    assert stats["min"] == 100.0
    assert stats["total"] == 1500.0


def test_calculate_summary_statistics_empty():
    """Test summary statistics with empty list."""
    stats = analyze._calculate_summary_statistics([])

    assert stats["mean"] == 0.0
    assert stats["median"] == 0.0
    assert stats["max"] == 0.0
    assert stats["min"] == 0.0
    assert stats["total"] == 0.0


def test_detect_spikes_zscore():
    """Test spike detection using z-score."""
    # Create data with clear spike
    views = [100, 100, 100, 100, 1000, 100, 100, 100, 100]

    spikes = analyze._detect_spikes_zscore(views, threshold=2.0)

    # Only the spike day (index 4) should be detected
    assert spikes == [False, False, False, False, True, False, False, False, False]


def test_detect_spikes_zscore_no_spikes():
    """Test spike detection with no spikes."""
    views = [100, 100, 100, 100, 100]

    spikes = analyze._detect_spikes_zscore(views, threshold=2.0)

    assert all(not spike for spike in spikes)


def test_calculate_trend_slope():
    """Test trend slope calculation."""
    # Steadily increasing data
    views = [100, 200, 300, 400, 500]

    slope = analyze._calculate_trend_slope(views)

    # Should be positive (increasing trend)
    assert slope > 0

    # Steadily decreasing data
    views = [500, 400, 300, 200, 100]

    slope = analyze._calculate_trend_slope(views)

    # Should be negative (decreasing trend)
    assert slope < 0


def test_calculate_relative_growth():
    """Test relative growth calculation."""
    # 100 to 200 is 100% growth
    views = [100, 200]
    growth = analyze._calculate_relative_growth(views)
    assert growth == 1.0  # 100% growth

    # 200 to 100 is -50% growth
    views = [200, 100]
    growth = analyze._calculate_relative_growth(views)
    assert growth == -0.5  # -50% growth

    # Same values
    views = [100, 100]
    growth = analyze._calculate_relative_growth(views)
    assert growth == 0.0  # 0% growth


def test_analyze_data_success():
    """Test full analysis pipeline."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)

        # Create test article views data (10 days)
        article_views = []
        for i in range(10):
            article_views.append({
                "date": f"2024010{i+1}",
                "views": 100 + (i * 50)  # 100, 150, 200, ..., 550
            })
        article_file = work_path / "article_views.json"
        with article_file.open("w", encoding="utf-8") as f:
            json.dump(article_views, f)

        # Create test project views data
        project_views = [
            {"date": "20240101", "views": 2000000},  # 2M views
            {"date": "20240201", "views": 2200000},  # 2.2M views
        ]
        project_file = work_path / "project_views.json"
        with project_file.open("w", encoding="utf-8") as f:
            json.dump(project_views, f)

        # Run analysis
        result = analyze.analyze_data(work_path)

        assert result["ok"] is True
        assert "data" in result
        assert result["data"]["date_range"]["days"] == 10
        assert result["data"]["raw_views"]["statistics"]["mean"] > 0
        assert result["data"]["normalized_views"]["statistics"]["mean"] > 0
        assert "next_step" in result


def test_analyze_data_missing_work_dir():
    """Test analysis with missing work directory."""
    result = analyze.analyze_data("/nonexistent/path")

    assert result["ok"] is False
    assert len(result["warnings"]) > 0
    # Should mention that article views data is not found
    assert "Article views data not found" in result["warnings"][0]


def test_cli_analyze_command():
    """Test the analyze CLI command."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)

        # Create test article views data
        article_views = [
            {"date": "20240101", "views": 100},
            {"date": "20240102", "views": 200},
        ]
        article_file = work_path / "article_views.json"
        with article_file.open("w", encoding="utf-8") as f:
            json.dump(article_views, f)

        # Create test project views data
        project_views = [
            {"date": "20240101", "views": 1000000},
        ]
        project_file = work_path / "project_views.json"
        with project_file.open("w", encoding="utf-8") as f:
            json.dump(project_views, f)

        # Test CLI analyze command
        test_args = [
            "wikitrends",
            "analyze",
            "--work-dir",
            str(work_path),
        ]

        with patch("sys.argv", test_args):
            # Capture stdout and stderr
            import io
            import sys
            old_stdout = sys.stdout
            sys.stdout = mystdout = io.StringIO()
            try:
                cli.main()
            except SystemExit as e:
                # Capture the exit code
                exit_code = e.code
                # Get the output
                output = mystdout.getvalue()
                sys.stdout = old_stdout

                # Check that we got a JSON response
                if output.strip():
                    result = json.loads(output)
                    assert result["ok"] is True
                    assert "data" in result
                assert exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])