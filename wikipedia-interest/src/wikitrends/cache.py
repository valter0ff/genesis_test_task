"""Shared on-disk cache for API responses."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

RECENT_TTL_SECONDS = 3600  # 1 hour
CACHE_DIR_NAME = ".cache"


def cache_dir(work_dir: Path | None = None) -> Path:
    """Return the cache dir: work_dir/.cache or default .cache/wikitrends."""
    if work_dir is not None:
        path = work_dir / CACHE_DIR_NAME
    else:
        path = Path(os.environ.get("WIKITRENDS_CACHE_DIR", ".cache/wikitrends"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path_for(url: str, work_dir: Path | None = None) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir(work_dir) / f"{digest}.json"


def get(url: str, work_dir: Path | None = None) -> tuple[Any, int] | None:
    """Return (body, status) for a fresh cache entry, otherwise None."""
    try:
        entry = json.loads(_path_for(url, work_dir).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    expires_at = entry.get("expires_at")
    if expires_at is not None and time.time() > expires_at:
        return None
    return entry["body"], entry["status"]


def put(url: str, body: Any, status: int, *, permanent: bool, work_dir: Path | None = None) -> None:
    """Store a response."""
    entry = {
        "url": url,
        "status": status,
        "body": body,
        "expires_at": None if permanent else time.time() + RECENT_TTL_SECONDS,
    }
    with contextlib.suppress(OSError):
        _path_for(url, work_dir).write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
