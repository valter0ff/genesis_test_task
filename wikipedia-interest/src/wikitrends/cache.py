"""
Simple disk cache for API responses.
"""
import json
import time
from pathlib import Path
from typing import Any

CACHE_DIR_NAME = "cache"
MAX_AGE_SECONDS = 3 * 24 * 60 * 60  # 3 days


def _get_cache_dir(work_dir: Path) -> Path:
    """Return the cache directory, creating it if necessary."""
    cache_dir = work_dir / CACHE_DIR_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cache_path(work_dir: Path, url: str) -> Path:
    """Generate a cache file path for the given URL."""
    # Use a simple hash of the URL to avoid filesystem issues with special chars.
    # We'll use the URL itself but replace problematic characters.
    # For simplicity, we'll use the URL's netloc and path, and replace / and ? with _.
    # However, to avoid collisions, we can use a hash.
    import hashlib

    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return _get_cache_dir(work_dir) / f"{url_hash}.json"


def get_cached_response(work_dir: Path, url: str) -> tuple[Any | None, float | None]:
    """
    Return cached data and timestamp if a valid cache exists (older than 3 days).
    If the cache exists but is newer than 3 days, return None to indicate refetch needed.
    If no cache exists, return (None, None).
    """
    cache_path = _get_cache_path(work_dir, url)
    if not cache_path.exists():
        return None, None

    # Check the age of the cache file
    cache_time = cache_path.stat().st_mtime
    now = time.time()
    age = now - cache_time

    if age > MAX_AGE_SECONDS:
        # Cache is older than 3 days: consider it permanent and return it.
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data, cache_time
        except (json.JSONDecodeError, OSError):
            # If cache is corrupted, treat as miss.
            return None, None
    else:
        # Cache is newer than 3 days: we should refetch.
        return None, None


def cache_response(work_dir: Path, url: str, data: Any) -> None:
    """Cache the response data for the given URL."""
    cache_path = _get_cache_path(work_dir, url)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        # If we can't write to cache, we just continue without caching.
        pass