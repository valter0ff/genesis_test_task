"""Tests for the resolve module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from wikitrends import resolve


def load_fixture(name: str) -> dict:
    """Load a test fixture from tests/fixtures/."""
    fixture_path = Path(__file__).parent / "fixtures" / name
    with fixture_path.open() as f:
        return json.load(f)


def test_resolve_single_match():
    """Test resolving a topic with a single confident match."""
    # Load search fixture
    search_fixture = load_fixture("wikidata_search_astronomy.json")
    # Create entities fixture with labels and descriptions (since wbgetentities
    # was called with props=sitelinks|labels|descriptions)
    entities_fixture = {
        "entities": {
            "Q333": {
                "type": "item",
                "id": "Q333",
                "sitelinks": {
                    "ukwiki": {"title": "Астрономія", "badges": []},
                    "enwiki": {"title": "Astronomy", "badges": ["Q17437798"]},
                },
                "labels": {
                    "uk": {"language": "uk", "value": "Астрономія"},
                    "en": {"language": "en", "value": "Astronomy"}
                },
                "descriptions": {
                    "uk": {"language": "uk", "value": "наука про небесні тіла та явники во Всесвіті"},
                    "en": {"language": "en", "value": "natural science studying celestial objects and phenomena in the cosmos"}
                }
            }
        },
        "success": 1
    }

    # Mock the Wikidata API calls
    with patch("wikitrends.resolve._get_json_wikidata") as mock_get_json:
        # First call: wbsearchentities
        mock_get_json.side_effect = [
            (search_fixture["json"], 200),  # search results
            (entities_fixture, 200),  # entity sitelinks+labels+descriptions
        ]

        # Resolve "astronomy" for Ukrainian and English
        result = resolve.resolve_topic("astronomy", ["uk", "en"])

        # Check Ukrainian result
        assert result["uk"]["status"] == "found"
        assert result["uk"]["title"] == "Астрономія"
        assert "natural science" in result["uk"]["description"] or "наука про небесні тіла" in result["uk"]["description"]

        # Check English result
        assert result["en"]["status"] == "found"
        assert result["en"]["title"] == "Astronomy"
        assert "natural science" in result["en"]["description"]


def test_resolve_ambiguous():
    """Test resolving a topic that matches multiple entities."""
    # Create a search fixture with multiple entities that have sitelinks for the same language
    search_fixture = {
        "searchinfo": {"search": "mercury"},
        "search": [
            {
                "id": "Q308",  # Element
                "title": "Q308",
                "display": {
                    "label": {"value": "Mercury", "language": "en"},
                    "description": {"value": "chemical element", "language": "en"}
                }
            },
            {
                "id": "Q312",  # Planet
                "title": "Q312",
                "display": {
                    "label": {"value": "Mercury", "language": "en"},
                    "description": {"value": "planet in the Solar System", "language": "en"}
                }
            }
        ],
        "search-continue": 0,
        "success": 1
    }

    # Create entities fixture where both have enwiki sitelinks but with different titles
    entities_fixture = {
        "entities": {
            "Q308": {
                "sitelinks": {
                    "enwiki": {"title": "Mercury", "badges": []}
                },
                "labels": {
                    "en": {"language": "en", "value": "Mercury"}
                },
                "descriptions": {
                    "en": {"language": "en", "value": "chemical element"}
                }
            },
            "Q312": {
                "sitelinks": {
                    "enwiki": {"title": "Mercury (planet)", "badges": []}
                },
                "labels": {
                    "en": {"language": "en", "value": "Mercury"}
                },
                "descriptions": {
                    "en": {"language": "en", "value": "planet in the Solar System"}
                }
            }
        },
        "success": 1
    }

    with patch("wikitrends.resolve._get_json_wikidata") as mock_get_json:
        mock_get_json.side_effect = [
            (search_fixture, 200),
            (entities_fixture, 200),
        ]

        result = resolve.resolve_topic("mercury", ["en"])

        # Should be ambiguous with two candidates
        assert result["en"]["status"] == "ambiguous"
        assert len(result["en"]["candidates"]) == 2
        # Check that we got both titles
        titles = {c["title"] for c in result["en"]["candidates"]}
        assert titles == {"Mercury", "Mercury (planet)"}


def test_resolve_no_sitelink():
    """Test resolving a topic where entity has no sitelink for requested language."""
    # Search fixture that finds an entity
    search_fixture = {
        "searchinfo": {"search": "sometopic"},
        "search": [
            {
                "id": "Q12345",
                "title": "Q12345",
                "display": {
                    "label": {"value": "Some Topic", "language": "en"},
                    "description": {"value": "A topic", "language": "en"}
                }
            }
        ],
        "search-continue": 0,
        "success": 1
    }

    # Entities fixture where the entity has no sitelink for the requested language
    entities_fixture = {
        "entities": {
            "Q12345": {
                "sitelinks": {
                    # Has frwiki and dewiki but not enwiki
                    "frwiki": {"title": "Sujet", "badges": []},
                    "dewiki": {"title": "Ein Thema", "badges": []}
                },
                "labels": {
                    "en": {"language": "en", "value": "Some Topic"}
                },
                "descriptions": {
                    "en": {"language": "en", "value": "A topic"}
                }
            }
        },
        "success": 1
    }

    with patch("wikitrends.resolve._get_json_wikidata") as mock_get_json:
        mock_get_json.side_effect = [
            (search_fixture, 200),
            (entities_fixture, 200),
        ]

        # Try to resolve for English (no enwiki sitelink)
        result = resolve.resolve_topic("some topic", ["en"])

        # Should be not_found
        assert result["en"]["status"] == "not_found"


def test_resolve_network_error():
    """Test handling of network/API errors."""
    with patch("wikitrends.resolve._get_json_wikidata") as mock_get_json:
        # Simulate a network error on the first call (search)
        mock_get_json.side_effect = Exception("Network timeout")

        result = resolve.resolve_topic("topic", ["en"])

        # Should have error status
        assert result["en"]["status"] == "error"
        assert "Network timeout" in result["en"]["message"]