"""Unit tests for report generation."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from wikitrends import report

# Minimal 1x1 black pixel PNG (base64 decoded)
MINIMAL_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'


def test_load_result_success():
    """Test loading analysis result successfully."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)
        result_data = {
            "ok": True,
            "data": {"test": "value"},
            "warnings": [],
            "next_step": "test",
        }
        result_file = work_path / "result.json"
        with result_file.open("w", encoding="utf-8") as f:
            json.dump(result_data, f)

        loaded = report._load_result(work_path)
        assert loaded == result_data


def test_load_result_file_not_found():
    """Test loading result when file does not exist."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)
        with pytest.raises(FileNotFoundError):
            report._load_result(work_path)


def test_generate_chart_with_data():
    """Test chart generation with article views data."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)
        # Create article views data
        article_views = [
            {"date": "20240101", "views": 100},
            {"date": "20240102", "views": 150},
            {"date": "20240103", "views": 200},
        ]
        article_file = work_path / "article_views.json"
        with article_file.open("w", encoding="utf-8") as f:
            json.dump(article_views, f)

        # Dummy result (not used in chart generation when data exists)
        result = {"data": {}}

        chart_path = report._generate_chart(work_path, result)
        assert chart_path.exists()
        assert chart_path.suffix == ".png"
        # Check that the charts directory was created
        assert (work_path / "charts").exists()


def test_generate_chart_without_data():
    """Test chart generation when article views data is missing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)
        # No article views file
        result = {"data": {}}

        chart_path = report._generate_chart(work_path, result)
        assert chart_path.exists()
        assert chart_path.suffix == ".png"


def test_generate_pdf():
    """Test PDF generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)
        # Create a minimal result
        result = {
            "data": {
                "date_range": {"start": "20240101", "end": "20240103", "days": 3},
                "raw_views": {"total": 450, "mean": 150.0},
                "normalized_views": {"total": 0.45, "mean": 0.15},
            }
        }
        # Create a minimal valid PNG file
        charts_dir = work_path / "charts"
        charts_dir.mkdir()
        chart_path = charts_dir / "chart.png"
        chart_path.write_bytes(MINIMAL_PNG)

        pdf_path = report._generate_pdf(work_path, result, chart_path)
        assert pdf_path.exists()
        assert pdf_path.suffix == ".pdf"


def test_generate_report_success():
    """Test successful report generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)
        # Create result.json
        result_data = {
            "ok": True,
            "data": {
                "date_range": {"start": "20240101", "end": "20240103", "days": 3},
                "raw_views": {"total": 450, "mean": 150.0, "median": 150.0},
                "normalized_views": {"total": 0.45, "mean": 0.15, "median": 0.15},
            },
            "warnings": [],
            "next_step": "test",
        }
        result_file = work_path / "result.json"
        with result_file.open("w", encoding="utf-8") as f:
            json.dump(result_data, f)

        # Create article views data for charting
        article_views = [
            {"date": "20240101", "views": 100},
            {"date": "20240102", "views": 150},
            {"date": "20240103", "views": 200},
        ]
        article_file = work_path / "article_views.json"
        with article_file.open("w", encoding="utf-8") as f:
            json.dump(article_views, f)

        # Run report generation
        output = report.generate_report(work_path)

        assert output["ok"] is True
        assert "chart_path" in output["data"]
        assert "report_path" in output["data"]
        assert Path(output["data"]["chart_path"]).exists()
        assert Path(output["data"]["report_path"]).exists()
        assert output["warnings"] == []
        assert "Report generated successfully" in output["next_step"]


def test_generate_report_missing_result():
    """Test report generation when result.json is missing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)
        # Do not create result.json
        output = report.generate_report(work_path)

        assert output["ok"] is False
        assert len(output["warnings"]) > 0
        assert "Result file not found" in output["warnings"][0]
        assert "fetch" in output["next_step"].lower() and "analyze" in output["next_step"].lower()


def test_generate_report_exception_handling():
    """Test report generation handles unexpected exceptions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_path = Path(tmp_dir)
        # Create a valid result.json and article_views.json so that we get to chart generation
        result_data = {
            "ok": True,
            "data": {
                "date_range": {"start": "20240101", "end": "20240103", "days": 3},
                "raw_views": {"total": 450, "mean": 150.0, "median": 150.0},
                "normalized_views": {"total": 0.45, "mean": 0.15, "median": 0.15},
            },
            "warnings": [],
            "next_step": "test",
        }
        result_file = work_path / "result.json"
        with result_file.open("w", encoding="utf-8") as f:
            json.dump(result_data, f)

        article_views = [
            {"date": "20240101", "views": 100},
            {"date": "20240102", "views": 150},
            {"date": "20240103", "views": 200},
        ]
        article_file = work_path / "article_views.json"
        with article_file.open("w", encoding="utf-8") as f:
            json.dump(article_views, f)

        # Mock _generate_chart to raise an exception
        with patch('wikitrends.report._generate_chart', side_effect=Exception("Test exception")):
            output = report.generate_report(work_path)

        assert output["ok"] is False
        assert len(output["warnings"]) > 0
        assert "Unexpected error" in output["warnings"][0]