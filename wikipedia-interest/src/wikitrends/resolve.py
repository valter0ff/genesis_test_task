"""Resolve topic to article titles per language using Wikidata."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests

from . import cache

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
DEFAULT_CONTACT = "https://github.com/valter0ff/wikipedia-interest"
REQUEST_DELAY_SECONDS = 0.1
MAX_RETRIES = 5
BACKOFF_SECONDS = 0.5
RETRY_STATUSES = {429, 500, 502, 503, 504}


class WikidataError(Exception):
    """Request failed after retries, or the API returned an unexpected response."""


def _wikidata_user_agent() -> str:
    """Wikidata requires a descriptive User-Agent with contact information."""
    return f"wikitrends/0.1 ({os.environ.get('WIKITRENDS_CONTACT', DEFAULT_CONTACT)})"


def _get_json_wikidata(params: dict[str, Any], *, permanent: bool, work_dir: Path | None = None) -> tuple[Any, int]:
    """GET Wikidata API with cache and retry. Returns (body, status); 404 is returned, not raised."""
    # Create a cache key from the parameters
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    url = f"{WIKIDATA_API}?{param_str}"

    hit = cache.get(url, work_dir=work_dir)
    if hit is not None:
        return hit

    last_error = "unknown error"
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            resp = requests.get(
                WIKIDATA_API,
                params=params,
                headers={"User-Agent": _wikidata_user_agent(), "Accept": "application/json"},
                timeout=30,
            )
        except requests.RequestException as exc:
            last_error = str(exc)
        else:
            if resp.status_code in RETRY_STATUSES:
                last_error = f"HTTP {resp.status_code}"
            elif resp.status_code in (200, 404):
                try:
                    body = resp.json()
                except ValueError as exc:
                    msg = f"Response is not valid JSON: {url}"
                    raise WikidataError(msg) from exc
                cache.put(url, body, resp.status_code, permanent=permanent, work_dir=work_dir)
                return body, resp.status_code
            else:
                msg = f"HTTP {resp.status_code} for {url}: {resp.text[:200]}"
                raise WikidataError(msg)
        time.sleep(BACKOFF_SECONDS * 2**attempt)
    msg = f"Failed after {MAX_RETRIES} attempts ({last_error}): {url}"
    raise WikidataError(msg)


def _language_to_site_code(language: str) -> str:
    """Map language code to Wikidata site code.

    Most languages follow the pattern: {lang}wiki
    Some special cases exist (from api-notes.md):
    - be_x_oldwiki for be-tarask.wikipedia.org
    """
    # Handle special case from the api-notes
    if language == "be-tarask":
        return "be_x_oldwiki"
    # Standard case: {lang}wiki
    return f"{language}wiki"


def resolve_topic(topic: str, languages: list[str]) -> dict[str, dict]:
    """
    Resolve a topic to Wikipedia article titles per language using Wikidata.

    Args:
        topic: The topic to search for (e.g., "astronomy")
        languages: List of language codes (e.g., ["uk", "en", "pl"])

    Returns:
        Dict mapping language code to result dict with keys:
        - status: "found", "ambiguous", "not_found", or "error"
        - title: article title (when status is "found")
        - description: article description (when status is "found")
        - candidates: list of candidate dicts (when status is "ambiguous")
        - message: error message (when status is "error")
    """
    # Initialize result for each language
    result = {lang: {"status": "not_found"} for lang in languages}

    try:
        # Step 1: Search for entities using wbsearchentities
        # Try with language="en" first as suggested, but we can also try without language
        # parameter to get multilingual results
        search_params = {
            "action": "wbsearchentities",
            "search": topic,
            "language": "en",  # Start with English as suggested
            "format": "json",
        }

        search_data, search_status = _get_json_wikidata(search_params, permanent=True)

        if search_status != 200:
            # If search fails, mark all languages as error
            for lang in languages:
                result[lang] = {
                    "status": "error",
                    "message": f"Wikidata search failed with HTTP {search_status}"
                }
            return result

        # Extract candidate entity IDs (limit to top 3)
        candidates = search_data.get("search", [])[:3]
        if not candidates:
            # No candidates found, mark all as not_found
            return result

        # Step 2: Get sitelinks, labels, and descriptions for candidates
        candidate_ids = [cand["id"] for cand in candidates]
        entities_params = {
            "action": "wbgetentities",
            "ids": "|".join(candidate_ids),
            "props": "sitelinks|labels|descriptions",
            "format": "json",
        }

        entities_data, entities_status = _get_json_wikidata(entities_params, permanent=True)

        if entities_status != 200:
            # If entities fetch fails, mark all languages as error
            for lang in languages:
                result[lang] = {
                    "status": "error",
                    "message": f"Wikidata entities fetch failed with HTTP {entities_status}"
                }
            return result

        entities = entities_data.get("entities", {})

        # Step 3: For each language, check which candidates have sitelinks
        for lang in languages:
            site_code = _language_to_site_code(lang)

            # Collect candidates that have this language's sitelink
            matches = []
            for cand in candidates:
                entity_id = cand["id"]
                if entity_id in entities:
                    entity = entities[entity_id]
                    sitelinks = entity.get("sitelinks", {})
                    if site_code in sitelinks:
                        sitelink = sitelinks[site_code]
                        # Get label and description in the target language if available,
                        # otherwise fall back to English or any available
                        labels = entity.get("labels", {})
                        descriptions = entity.get("descriptions", {})

                        label = labels.get(lang, {}).get("value") or \
                                labels.get("en", {}).get("value") or \
                                next(iter(labels.values()), {}).get("value", "") if labels else ""

                        description = descriptions.get(lang, {}).get("value") or \
                                    descriptions.get("en", {}).get("value") or \
                                    next(iter(descriptions.values()), {}).get("value", "") if descriptions else ""

                        matches.append({
                            "title": sitelink["title"],
                            "description": description,
                            "entity_id": entity_id,
                            "label": label or sitelink["title"]  # fallback to title if no label
                        })

            # Determine result based on matches
            if len(matches) == 1:
                # Confident single match
                match = matches[0]
                result[lang] = {
                    "status": "found",
                    "title": match["title"],
                    "description": match["description"]
                }
            elif len(matches) > 1:
                # Ambiguous: multiple candidates match
                # Remove duplicate titles (same title from different entities)
                unique_matches = []
                seen_titles = set()
                for match in matches:
                    if match["title"] not in seen_titles:
                        seen_titles.add(match["title"])
                        unique_matches.append({
                            "title": match["title"],
                            "description": match["description"]
                        })

                result[lang] = {
                    "status": "ambiguous",
                    "candidates": unique_matches
                }
            # else: no matches, keep status as "not_found"

    except WikidataError as e:
        # Handle Wikidata-specific errors
        for lang in languages:
            result[lang] = {
                "status": "error",
                "message": str(e)
            }
    except Exception as e:  # noqa: BLE001
        # Handle any other unexpected errors
        for lang in languages:
            result[lang] = {
                "status": "error",
                "message": f"Unexpected error: {e!s}"
            }

    return result