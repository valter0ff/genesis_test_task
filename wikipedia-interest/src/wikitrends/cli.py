"""Command-line interface for wikitrends."""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from .cache import CACHE_DIR_NAME

from . import api


def _slug_from_params(project: str, article: str, start: str, end: str) -> str:
    """Generate a slug for the work directory based on parameters."""
    key = f"{project}/{article}/{start}/{end}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:12]


def _get_work_dir(args: argparse.Namespace) -> Path:
    """Determine the work directory to use."""
    if args.work_dir:
        return Path(args.work_dir)
    slug = _slug_from_params(args.project, args.article, args.start, args.end)
    return Path.cwd() / "work" / slug


def _validate_date(date_str: str) -> bool:
    """Validate that date_str is in YYYYMMDD format and a valid date."""
    try:
        datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=UTC)
        return True
    except ValueError:
        return False


def _print_json_and_exit(
    ok: bool,
    data: Any,
    warnings: list[str],
    next_step: str,
    exit_code: int = 0,
) -> None:
    """Print JSON response and exit with given code."""
    response: dict[str, Any] = {
        "ok": ok,
        "data": data,
        "warnings": warnings,
        "next_step": next_step,
    }
    print(json.dumps(response, indent=None))
    sys.exit(exit_code)


def main() -> None:
    """Entry point for the wikitrends CLI."""
    parser = argparse.ArgumentParser(description="Wikipedia interest analysis tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch pageviews data for an article")
    fetch_parser.add_argument("--project", required=True, help="Wikimedia project")
    fetch_parser.add_argument("--article", required=True, help="Article title")
    fetch_parser.add_argument("--start", required=True, help="Start date (YYYYMMDD)")
    fetch_parser.add_argument("--end", required=True, help="End date (YYYYMMDD)")
    fetch_parser.add_argument(
        "--granularity",
        choices=["daily", "monthly"],
        default="daily",
        help="Granularity of data",
    )
    fetch_parser.add_argument(
        "--work-dir",
        help="Work directory for caching",
    )

    args = parser.parse_args()

    if args.command == "fetch":
        if not _validate_date(args.start) or not _validate_date(args.end):
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=["Start and end dates must be in YYYYMMDD format and valid dates."],
                next_step="Check the date format and try again.",
                exit_code=2,
            )

        if args.granularity == "monthly":
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=["Granularity 'monthly' not implemented for fetch command. Use 'daily'."],
                next_step="Remove --granularity or set it to 'daily'.",
                exit_code=2,
            )

        work_dir = _get_work_dir(args)
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            items, warnings = api.get_article_views_daily(
                project=args.project,
                article=args.article,
                start_date=args.start,
                end_date=args.end,
                work_dir=work_dir,
            )
        except Exception as e:  # noqa: BLE001
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=[f"Unexpected error: {e!s}"],
                next_step="Check your parameters and network connection.",
                exit_code=3,
            )

        _print_json_and_exit(
            ok=True,
            data=items,
            warnings=warnings,
            next_step="Run 'wikitrends analyze' to compute metrics from this data.",
            exit_code=0,
        )


if __name__ == "__main__":
    main()
