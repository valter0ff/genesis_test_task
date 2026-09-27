"""Basic test for run command."""
import json
from pathlib import Path
import pytest
from unittest.mock import patch

from wikitrends import cli


def test_run_basic(tmp_path, monkeypatch):
    """Test that run command works with valid spec."""
    # Create a spec file in the tmp directory
    spec_file = tmp_path / "spec.json"
    spec_data = {
        "topic": "Test",
        "languages": ["en"],
        "window": ["20230101", "20231231"]
    }
    with spec_file.open("w") as f:
        json.dump(spec_data, f)
    
    # Change current working directory to tmp_path
    monkeypatch.chdir(tmp_path)
    
    # Capture the SystemExit to get the output
    with patch("sys.argv", ["wikitrends", "run", "--spec", str(spec_file)]):
        with pytest.raises(SystemExit) as exc_info:
            cli.main()
    
    # Check that the command ran (exit code 0 for success, 1 for partial success due to warnings)
    assert exc_info.value.code in [0, 1]
