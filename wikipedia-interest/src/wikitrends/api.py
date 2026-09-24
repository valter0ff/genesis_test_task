"""Wikimedia Pageviews client: sequential requests, retry with backoff, disk cache."""

from __future__ import annotations

import os
import time
import urllib.parse
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from . import cache

API_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
DEFAULT_CONTACT = "https://github.com/valter0ff/wikipedia-interest"
REQUEST_DELAY_SECONDS = 0.1
MAX_RETRIES = 5
BACKOFF_SECONDS = 0.5
RETRY_STATUSES = {429, 500, 502, 503, 504}
EARLIEST_DATE = date(2015, 7, 1)  # Pageviews data starts here
RECENT_DAYS = 3  # data this fresh may still be revised, so it is cached only briefly
DATE_LEN = 8


class APIError(Exception):
    """Request failed after retries, or the API returned an unexpected response."""


def parse_date(value: str) -> date:
    """Parse YYYYMMDD strictly; raise ValueError with a clear message otherwise."""
    if len(value) == DATE_LEN and value.isdigit():
        try:
            return datetime.strptime(value, "%Y%m%d").replace(tzinfo=UTC).date()
        except ValueError:
            pass
    msg = f"Invalid date '{value}': use a real calendar date in YYYYMMDD format."
    raise ValueError(msg)


def user_agent() -> str:
    """Wikimedia requires a descriptive User-Agent with contact information."""
    return f"wikitrends/0.1 ({os.environ.get('WIKITRENDS_CONTACT', DEFAULT_CONTACT)})"


def encode_title(title: str) -> str:
    """Spaces -> underscores, then full percent-encoding (so 'AC/DC' -> 'AC%2FDC')."""
    return urllib.parse.quote(title.strip().replace(" ", "_"), safe="")


def _today() -> date:
    return datetime.now(UTC).date()


def _get_json(url: str, *, permanent: bool, work_dir: Path | None = None) -> tuple[Any, int]:
    """GET with cache and retry. Returns (body, status); 404 is returned, not raised."""
    hit = cache.get(url, work_dir=work_dir)
    if hit is not None:
        return hit
    last_error = "unknown error"
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": user_agent(), "Accept": "application/json"},
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
                    raise APIError(msg) from exc
                cache.put(url, body, resp.status_code, permanent=permanent, work_dir=work_dir)
                return body, resp.status_code
            else:
                msg = f"HTTP {resp.status_code} for {url}: {resp.text[:200]}"
                raise APIError(msg)
        time.sleep(BACKOFF_SECONDS * 2**attempt)
    msg = f"Failed after {MAX_RETRIES} attempts ({last_error}): {url}"
    raise APIError(msg)


def _prepare_range(start_date: str, end_date: str) -> tuple[date, date, list[str]]:
    """Validate dates; clamp the end to yesterday."""
    start, end = parse_date(start_date), parse_date(end_date)
    warnings: list[str] = []
    if start < EARLIEST_DATE:
        msg = "Start date is before 20150701: Wikimedia pageviews data starts in July 2015."
        raise ValueError(msg)
    if start > end:
        msg = "Start date must not be after end date."
        raise ValueError(msg)
    yesterday = _today() - timedelta(days=1)
    if end > yesterday:
        end = yesterday
        warnings.append(
            f"End date moved to {end:%Y%m%d}: today's and future data are not available yet."
        )
    if start > end:
        msg = "The whole range is in the future: no data available yet."
        raise ValueError(msg)
    return start, end, warnings


def get_article_views_daily(
    project: str, article: str, start_date: str, end_date: str, work_dir: Path | None = None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Daily views (agent=user, all-access) for every day in the range, inclusive."""
    start, end, warnings = _prepare_range(start_date, end_date)
    url = (
        f"{API_BASE}/per-article/{project}/all-access/user/"
        f"{encode_title(article)}/daily/{start:%Y%m%d}/{end:%Y%m%d}"
    )
    permanent = end < _today() - timedelta(days=RECENT_DAYS)
    body, status = _get_json(url, permanent=permanent, work_dir=work_dir)

    views_by_day: dict[str, int] = {}
    if status == 404:
        warnings.append(
            f"No data found for '{article}' on {project} between {start:%Y%m%d} and {end:%Y%m%d}."
        )
    else:
        for item in body.get("items", []):
            views_by_day[item["timestamp"][:8]] = item["views"]

    days: list[dict[str, Any]] = []
    day = start
    while day <= end:
        key = f"{day:%Y%m%d}"
        days.append({"date": key, "views": views_by_day.get(key, 0)})
        day += timedelta(days=1)
    return days, warnings


def get_project_views_monthly(
    project: str, start_date: str, end_date: str, work_dir: Path | None = None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Monthly total views of a whole project."""
    start, end, warnings = _prepare_range(start_date, end_date)
    url = (
        f"{API_BASE}/aggregate/{project}/all-access/user/monthly/"
        f"{start:%Y%m%d}/{end:%Y%m%d}"
    )
    permanent = end < _today() - timedelta(days=RECENT_DAYS)
    body, status = _get_json(url, permanent=permanent, work_dir=work_dir)
    if status == 404:
        msg = f"No aggregate data for project '{project}': check the name (e.g. uk.wikipedia)."
        raise APIError(msg)
    items = sorted(
        ({"date": i["timestamp"][:8], "views": i["views"]} for i in body.get("items", [])),
        key=lambda x: x["date"],
    )
    return items, warnings
