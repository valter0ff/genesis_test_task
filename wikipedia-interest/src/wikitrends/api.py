"""
Wikimedia API client with caching and retry logic.
"""
import json
import time
import urllib.parse
from datetime import date, timedelta
from typing import Any

import requests

from . import cache

# Constants
WIKIMEDIA_API = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
USER_AGENT_TEMPLATE = "wikitrends/0.1 (<repo-url>; {contact})"
DEFAULT_HEADERS = {
    "Accept": "application/json",
}
# Delay between requests to avoid hitting rate limits too fast
REQUEST_DELAY_SECONDS = 0.1  # 100ms
# Retry settings
MAX_RETRIES = 5
BACKOFF_FACTOR = 0.5  # seconds, will be multiplied by 2^(retry-1)


class APIError(Exception):
    """Base exception for API errors."""


def _build_user_agent(contact: str | None = None) -> str:
    """Build the User-Agent header value."""
    if contact is None:
        contact = "<repo-url>"  # placeholder
    return USER_AGENT_TEMPLATE.format(contact=contact)


def _make_request(
    url: str,
    params: dict[str, Any] | None = None,
    work_dir: Any | None = None,
    use_cache: bool = True,
) -> tuple[Any, int]:
    """
    Make a GET request with caching, retry, and delay.
    Returns (data, status_code) or raises APIError on failure after retries.
    If use_cache is True and work_dir is provided, caching is attempted.
    """
    headers = {
        "User-Agent": _build_user_agent(),
        **DEFAULT_HEADERS,
    }

    # If caching is enabled and work_dir provided, try to get cached response
    if use_cache and work_dir is not None:
        cached_data, _ = cache.get_cached_response(work_dir, url)
        if cached_data is not None:
            return cached_data, 200  # Assume cached data is valid

    # We will need to fetch; apply delay before request to be nice
    time.sleep(REQUEST_DELAY_SECONDS)

    last_exception: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            # If we get a successful response, break
            if resp.status_code < 400:
                # Cache the response if caching enabled
                if use_cache and work_dir is not None:
                    try:
                        data = resp.json()
                        cache.cache_response(work_dir, url, data)
                    except (json.JSONDecodeError, OSError):
                        # If we can't cache, just continue
                        pass
                return resp.json(), resp.status_code
            # If we get a 429 or 5xx, we will retry after backoff
            if resp.status_code in (429, 500, 502, 503, 504):
                last_exception = APIError(
                    f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
                # Exponential backoff
                wait_time = BACKOFF_FACTOR * (2 ** attempt)
                time.sleep(wait_time)
                continue
            # For other status codes (like 404, 400), we do not retry
            # We'll return the error response (or raise?)
            # For 404, we want to return the JSON error body so the caller can handle it.
            # We'll return the JSON and status code.
            try:
                return resp.json(), resp.status_code
            except json.JSONDecodeError:
                # If not JSON, return text
                return {"text": resp.text}, resp.status_code
        except requests.RequestException as e:
            last_exception = e
            # Wait before retry
            wait_time = BACKOFF_FACTOR * (2 ** attempt)
            time.sleep(wait_time)
            continue

    # If we exhausted retries, raise the last exception
    raise last_exception or APIError("Unknown error after retries")


def _encode_title(title: str) -> str:
    """
    Replace spaces with underscores and then percent-encode with safe=''.
    This ensures that slashes are also encoded.
    """
    # Replace spaces with underscores
    title = title.replace(" ", "_")
    # Percent-encode everything except the unreserved characters (but we set safe='')
    # So everything that is not alphanumeric or -._~ will be encoded.
    return urllib.parse.quote(title, safe="")


def get_article_views_daily(
    project: str,
    article: str,
    start_date: str,
    end_date: str,
    work_dir: Any | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Fetch daily views for an article between start_date and end_date (inclusive).
    Returns a list of dicts with keys: date (YYYYMMDD), views (int).
    Also returns a list of warning messages.
    If the API returns 404 (no data), we treat it as all zeros and add a warning.
    """
    # Validate dates format? We'll assume they are correct.
    encoded_article = _encode_title(article)
    url = f"{WIKIMEDIA_API}/per-article/{project}/all-access/user/{encoded_article}/daily/{start_date}/{end_date}"

    try:
        data, status_code = _make_request(url, work_dir=work_dir, use_cache=True)
    except APIError as e:
        # If we fail after retries, we treat as error and return empty data with warning.
        return [], [f"Failed to fetch data after {MAX_RETRIES} retries: {e!s}"]

    warnings: list[str] = []
    items: list[dict[str, Any]] = []

    if status_code == 200:
        # Success: parse the items
        raw_items = data.get("items", [])
        # Build a map from date to views for quick lookup
        view_map = {}
        for item in raw_items:
            # item has keys: project, article, granularity, timestamp, access, agent, views
            # timestamp is like YYYYMMDDHH
            date_str = item["timestamp"][:8]  # YYYYMMDD
            views = item["views"]
            view_map[date_str] = views

        # Generate a dense list for every day in the range
        start = date.strptime(start_date, "%Y%m%d")
        end = date.strptime(end_date, "%Y%m%d")
        current = start
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            views = view_map.get(date_str, 0)
            items.append({"date": date_str, "views": views})
            current += timedelta(days=1)

    elif status_code == 404:
        # No data for the range: treat as all zeros
        warnings.append(
            f"No data found for article '{article}' in project '{project}' "
            f"from {start_date} to {end_date}. Assuming zero views for all days."
        )
        # Generate a dense list of zeros
        start = date.strptime(start_date, "%Y%m%d")
        end = date.strptime(end_date, "%Y%m%d")
        current = start
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            items.append({"date": date_str, "views": 0})
            current += timedelta(days=1)
    else:
        # Other error status codes
        warnings.append(
            f"Unexpected HTTP {status_code} when fetching article views: {data.get('detail', 'No details')}"
        )
        # Return empty items
        items = []

    return items, warnings


def get_project_views_monthly(
    project: str,
    start_date: str,
    end_date: str,
    work_dir: Any | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Fetch monthly aggregate views for a project between start_date and end_date (inclusive).
    Returns a list of dicts with keys: date (YYYYMMDD), views (int).
    Also returns a list of warning messages.
    """
    url = f"{WIKIMEDIA_API}/aggregate/{project}/all-access/user/monthly/{start_date}/{end_date}"

    try:
        data, status_code = _make_request(url, work_dir=work_dir, use_cache=True)
    except APIError as e:
        return [], [f"Failed to fetch data after {MAX_RETRIES} retries: {e!s}"]

    warnings: list[str] = []
    items: list[dict[str, Any]] = []

    if status_code == 200:
        raw_items = data.get("items", [])
        for item in raw_items:
            # item has keys: project, access, agent, granularity, timestamp, views
            timestamp = item["timestamp"]  # YYYYMMDDHH
            date_str = timestamp[:8]  # YYYYMMDD (first day of month)
            views = item["views"]
            items.append({"date": date_str, "views": views})
        # The items are already in order? We'll sort just in case.
        items.sort(key=lambda x: x["date"])
    elif status_code == 404:
        warnings.append(
            f"No monthly aggregate data found for project '{project}' "
            f"from {start_date} to {end_date}. Assuming zero views for all months."
        )
        # Generate a dense list of zeros for each month in the range
        start = date.strptime(start_date, "%Y%m%d")
        end = date.strptime(end_date, "%Y%m%d")
        # We'll iterate by month
        current = start
        while current <= end:
            date_str = current.strftime("%Y%m01")  # first day of month
            items.append({"date": date_str, "views": 0})
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    else:
        warnings.append(
            f"Unexpected HTTP {status_code} when fetching project views: {data.get('detail', 'No details')}"
        )
        items = []

    return items, warnings