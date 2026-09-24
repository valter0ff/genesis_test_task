"""Command-line interface for wikitrends."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from . import api
from .cache import CACHE_DIR_NAME


def _slug_from_params(project: str, article: str, start: str, end: str) -> str:
    """Generate a slug for the work directory based on parameters."""
    # Use a hash to avoid filesystem issues and keep it short.
    key = f"{project}/{article}/{start}/{end}"
    # Use MD5 to get a fixed-length hex string.
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:12]


def _get_work_dir(args: argparse.Namespace) -> Path:
    """Determine the work directory to use."""
    if args.work_dir:
        return Path(args.work_dir)
    # Default: ./work/<slug>
    slug = _slug_from_params(args.project, args.article, args.start, args.end)
    return Path.cwd() / "work" / slug


def _validate_date(date_str: str) -> bool:
    """Validate that date_str is in YYYYMMDD format and a valid date."""
    if len(date_str) != 8 or not date_str.isdigit():
        return False
    try:
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        # Basic range checks - return conditions directly
        return (1 <= month <= 12) and (1 <= day <= 31)
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
    print(json.dumps(response, indent=None))  # Compact JSON as per spec
    sys.exit(exit_code)


def main() -> None:
    """Entry point for the wikitrends CLI."""
    parser = argparse.ArgumentParser(description="Wikipedia interest analysis tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch pageviews data for an article")
    fetch_parser.add_argument("--project", required=True, help="Wikimedia project (e.g., uk.wikipedia)")
    fetch_parser.add_argument("--article", required=True, help="Article title (with spaces and underscores)")
    fetch_parser.add_argument("--start", required=True, help="Start date (YYYYMMDD)")
    fetch_parser.add_argument("--end", required=True, help="End date (YYYYMMDD)")
    fetch_parser.add_argument(
        "--granularity",
        choices=["daily", "monthly"],
        default="daily",
        help="Granularity of data (default: daily)",
    )
    fetch_parser.add_argument(
        "--work-dir",
        help="Work directory for caching (default: ./work/<slug>)",
    )

    args = parser.parse_args()

    if args.command == "fetch":
        # Validate dates
        if not _validate_date(args.start) or not _validate_date(args.end):
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=["Start and end dates must be in YYYYMMDD format and valid dates."],
                next_step="Check the date format and try again.",
                exit_code=2,
            )

        # Validate granularity: fetch command currently only supports daily?
        # The spec says fetch returns per-article DAILY fetch. We'll implement both for completeness.
        if args.granularity == "monthly":
            # For monthly, we need to use the aggregate endpoint? Actually, per-article monthly is also available.
            # But the plan says aggregate (project total) fetch, monthly.
            # Let's stick to per-article for fetch command, and we can use the same endpoint with granularity=monthly.
            # However, the api.py currently only has get_article_views_daily and get_project_views_monthly.
            # We'll need to extend api.py for per-article monthly? But the spec says fetch is for per-article DAILY.
            # We'll assume the user will only use daily for fetch, and we'll error on monthly for now.
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=["Granularity 'monthly' not implemented for fetch command. Use 'daily'."],
                next_step="Remove --granularity or set it to 'daily'.",
                exit_code=2,
            )

        # Determine work directory
        work_dir = _get_work_dir(args)
        # Ensure work directory exists (for cache)
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / CACHE_DIR_NAME).mkdir(parents=True, exist_ok=True)

        # Fetch data
        try:
            items, warnings = api.get_article_views_daily(
                project=args.project,
                article=args.article,
                start_date=args.start,
                end_date=args.end,
                work_dir=work_dir,
            )
        except Exception as e:  # Catch any unexpected error # noqa: BLE001
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=[f"Unexpected error: {e!s}"],
                next_step="Check your parameters and network connection.",
                exit_code=3,
            )

        # Determine next step
        next_step = "Run 'wikitrends analyze' to compute metrics from this data."

        # Output JSON
        _print_json_and_exit(
            ok=True,
            data=items,
            warnings=warnings,
            next_step=next_step,
            exit_code=0,
        )

    else:
        # Should not happen due to required subcommand
        _print_json_and_exit(
            ok=False,
            data=[],
            warnings=[f"Unknown command: {args.command}"],
            next_step="Available commands: fetch",
            exit_code=2,
        )


if __name__ == "__main__":
    main()