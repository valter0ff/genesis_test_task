"""Command-line interface for wikitrends."""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    work_dir: Path | None = None,
) -> None:
    """Print JSON response and exit with given code."""
    # Ensure data is a dictionary so we can add work_dir
    if not isinstance(data, dict):
        data = {"result": data} if data is not None else {}

    # Add work_dir to data if provided
    if work_dir is not None:
        data["work_dir"] = str(work_dir)

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

    # Analyze subcommand
    analyze_parser = subparsers.add_parser("analyze", help="Analyze cached pageviews data")
    analyze_parser.add_argument(
        "--work-dir",
        help="Work directory for cached data (defaults to work/ based on last fetch)",
    )

    # Report subcommand
    report_parser = subparsers.add_parser("report", help="Generate PDF report from analyzed data")
    report_parser.add_argument(
        "--work-dir",
        help="Work directory for cached data (defaults to work/ based on last fetch)",
    )

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Execute full workflow: fetch → analyze → report")
    run_parser.add_argument(
        "--spec",
        required=True,
        help="Path to spec.json file containing workflow configuration",
    )
    run_parser.add_argument(
        "--work-dir",
        help="Work directory for caching (overrides work directory from spec)",
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
            # Fetch article views
            article_items, article_warnings = api.get_article_views_daily(
                project=args.project,
                article=args.article,
                start_date=args.start,
                end_date=args.end,
                work_dir=work_dir,
            )

            # Fetch project views for normalization
            project_items, project_warnings = api.get_project_views_monthly(
                project=args.project,
                start_date=args.start,
                end_date=args.end,
                work_dir=work_dir,
            )

            # Combine warnings
            warnings = article_warnings + project_warnings
        except Exception as e:  # noqa: BLE001
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=[f"Unexpected error: {e!s}"],
                next_step="Check your parameters and network connection.",
                exit_code=3,
                work_dir=work_dir,
            )

        # Save article views to work directory for analyze step
        article_views_file = work_dir / "article_views.json"
        with article_views_file.open("w", encoding="utf-8") as f:
            json.dump(article_items, f, indent=None)

        # Save project views to work directory for analyze step
        project_views_file = work_dir / "project_views.json"
        with project_views_file.open("w", encoding="utf-8") as f:
            json.dump(project_items, f, indent=None)

        _print_json_and_exit(
            ok=True,
            data={"article_views": article_items, "project_views": project_items},
            warnings=warnings,
            next_step="Run 'wikitrends analyze' to compute metrics from this data.",
            exit_code=0,
            work_dir=work_dir,
        )

    elif args.command == "analyze":
        work_dir = _get_work_dir(args)
        if not work_dir.exists():
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=[f"Work directory {work_dir} does not exist."],
                next_step="Run 'wikitrends fetch' first to generate data.",
                exit_code=2,
            )

        try:
            from . import analyze
            result = analyze.analyze_data(work_dir)
        except ImportError as e:
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=[f"Failed to import analysis module: {e}"],
                next_step="Check that analyze.py is properly implemented.",
                exit_code=3,
            )
        except Exception as e:  # noqa: BLE001
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=[f"Unexpected error during analysis: {e!s}"],
                next_step="Check your work directory and try again.",
                exit_code=3,
            )

        # Save result to work directory for report step
        result_file = work_dir / "result.json"
        with result_file.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=None)

        # Determine exit code based on result
        exit_code = 0 if result.get("ok", False) else 1
        _print_json_and_exit(
            ok=result.get("ok", False),
            data=result.get("data", {}),
            warnings=result.get("warnings", []),
            next_step=result.get("next_step", ""),
            exit_code=exit_code,
            work_dir=work_dir,
        )

    elif args.command == "report":
        work_dir = _get_work_dir(args)
        if not work_dir.exists():
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=[f"Work directory {work_dir} does not exist."],
                next_step="Run 'wikitrends fetch' and 'wikitrends analyze' first.",
                exit_code=2,
            )

        try:
            from . import report
            result = report.generate_report(work_dir)
        except ImportError as e:
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=[f"Failed to import report module: {e}"],
                next_step="Check that report.py is properly implemented.",
                exit_code=3,
            )
        except Exception as e:  # noqa: BLE001
            _print_json_and_exit(
                ok=False,
                data=[],
                warnings=[f"Unexpected error during report generation: {e!s}"],
                next_step="Check your work directory and try again.",
                exit_code=3,
            )

        # Determine exit code based on result
        exit_code = 0 if result.get("ok", False) else 1
        _print_json_and_exit(
            ok=result.get("ok", False),
            data=result.get("data", {}),
            warnings=result.get("warnings", []),
            next_step=result.get("next_step", ""),
            exit_code=exit_code,
            work_dir=work_dir,
        )

    elif args.command == "run":
        # Load spec file
        spec_path = Path(args.spec)
        if not spec_path.exists():
            _print_json_and_exit(
                ok=False,
                data={},
                warnings=[f"Spec file not found: {spec_path}"],
                next_step="Check the path to your spec.json file.",
                exit_code=2,
            )

        try:
            with spec_path.open(encoding="utf-8") as f:
                spec = json.load(f)
        except json.JSONDecodeError as exc:
            _print_json_and_exit(
                ok=False,
                data={},
                warnings=[f"Failed to parse spec.json: {exc}"],
                next_step="Check that your spec.json is valid JSON.",
                exit_code=2,
            )
        except Exception as exc:  # noqa: BLE001
            _print_json_and_exit(
                ok=False,
                data={},
                warnings=[f"Unexpected error reading spec file: {exc!s}"],
                next_step="Check your spec file and try again.",
                exit_code=2,
            )

        # Validate required fields in spec
        required_fields = ["topic", "languages", "window"]
        for field in required_fields:
            if field not in spec:
                _print_json_and_exit(
                    ok=False,
                    data={},
                    warnings=[f"Missing required field in spec: {field}"],
                    next_step=f"Add '{field}' to your spec.json file.",
                    exit_code=2,
                )

        # Validate window format
        if not isinstance(spec["window"], list) or len(spec["window"]) != 2:
            _print_json_and_exit(
                ok=False,
                data={},
                warnings=["Window must be a list of two dates [start, end] in YYYYMMDD format"],
                next_step="Fix the window field in your spec.json.",
                exit_code=2,
            )

        start_date, end_date = spec["window"]
        if not (_validate_date(start_date) and _validate_date(end_date)):
            _print_json_and_exit(
                ok=False,
                data={},
                warnings=["Start and end dates must be in YYYYMMDD format and valid dates."],
                next_step="Check the date format in your spec.json window field.",
                exit_code=2,
            )

        # Determine work directory
        if args.work_dir:
            work_dir = Path(args.work_dir)
        else:
            # Generate a slug from the spec for default work directory
            # Using the first language and creating a representative slug
            lang_rep = spec["languages"][0] if spec["languages"] else "multi"
            topic_slug = spec["topic"].lower().replace(" ", "_")
            work_dir = Path.cwd() / "work" / f"{topic_slug}_{lang_rep}_{start_date}_{end_date}"

        work_dir.mkdir(parents=True, exist_ok=True)

        # Save spec to work directory for future reference
        spec_file = work_dir / "spec.json"
        with spec_file.open("w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2)

        # Track all warnings and errors
        all_warnings = []
        failed_languages = []
        language_results = {}

        # Process each language
        for lang in spec["languages"]:
            # Determine project (language code + .wikipedia)
            # Handle special cases like uk -> uk.wikipedia, en -> en.wikipedia, etc.
            project = f"{lang}.wikipedia"

            # Create language-specific subdirectory in work dir
            lang_work_dir = work_dir / lang
            lang_work_dir.mkdir(exist_ok=True)

            try:
                # Step 1: Fetch article views and project views
                # We need to resolve the topic to article titles for each language
                # For now, we'll use the topic as the article title (with underscores)
                # In a full implementation, this would use Wikidata/resolve step
                article_title = spec["topic"].replace(" ", "_")

                # Fetch data
                article_items, article_warnings = api.get_article_views_daily(
                    project=project,
                    article=article_title,
                    start_date=start_date,
                    end_date=end_date,
                    work_dir=lang_work_dir,
                )

                project_items, project_warnings = api.get_project_views_monthly(
                    project=project,
                    start_date=start_date,
                    end_date=end_date,
                    work_dir=lang_work_dir,
                )

                # Combine warnings
                lang_warnings = article_warnings + project_warnings
                all_warnings.extend([f"[{lang}] {w}" for w in lang_warnings])

                # Save article views
                article_views_file = lang_work_dir / "article_views.json"
                with article_views_file.open("w", encoding="utf-8") as f:
                    json.dump(article_items, f, indent=None)

                # Save project views
                project_views_file = lang_work_dir / "project_views.json"
                with project_views_file.open("w", encoding="utf-8") as f:
                    json.dump(project_items, f, indent=None)

                # Step 2: Analyze the data
                try:
                    from . import analyze
                    analyze_result = analyze.analyze_data(lang_work_dir)
                except ImportError as e:
                    all_warnings.append(f"[{lang}] Failed to import analysis module: {e}")
                    failed_languages.append(lang)
                    continue
                except (FileNotFoundError, ValueError) as e:
                    all_warnings.append(f"[{lang}] Analysis failed due to missing/invalid data: {e}")
                    failed_languages.append(lang)
                    continue
                except Exception as e:  # noqa: BLE001
                    # Broad exception catch intentional to continue processing other languages
                    all_warnings.append(f"[{lang}] Unexpected error during analysis: {e!s}")
                    failed_languages.append(lang)
                    continue

                # Save analysis result
                result_file = lang_work_dir / "result.json"
                with result_file.open("w", encoding="utf-8") as f:
                    json.dump(analyze_result, f, indent=None)

                # Step 3: Generate report
                try:
                    from . import report
                    report_result = report.generate_report(lang_work_dir)
                except ImportError as e:
                    all_warnings.append(f"[{lang}] Failed to import report module: {e}")
                    failed_languages.append(lang)
                    continue
                except FileNotFoundError as e:
                    all_warnings.append(f"[{lang}] Report generation failed due to missing data: {e}")
                    failed_languages.append(lang)
                    continue
                except Exception as e:  # noqa: BLE001
                    # Broad exception catch intentional to continue processing other languages
                    all_warnings.append(f"[{lang}] Unexpected error during report generation: {e!s}")
                    failed_languages.append(lang)
                    continue

                # Store results for this language
                language_results[lang] = {
                    "ok": analyze_result.get("ok", False),
                    "analysis": analyze_result,
                    "report": report_result,
                    "work_dir": str(lang_work_dir),
                }

                if not analyze_result.get("ok", False):
                    failed_languages.append(lang)
                    all_warnings.extend([f"[{lang}] Analysis failed: {w}"
                                       for w in analyze_result.get("warnings", [])])
                if not report_result.get("ok", False):
                    failed_languages.append(lang)
                    all_warnings.extend([f"[{lang}] Report generation failed: {w}"
                                       for w in report_result.get("warnings", [])])

            except Exception as exc:  # noqa: BLE001
                failed_languages.append(lang)
                all_warnings.append(f"[{lang}] Unexpected error: {exc!s}")

        # Determine overall success
        overall_ok = len(failed_languages) == 0
        exit_code = 0 if overall_ok else 1

        # Prepare final data
        final_data = {
            "work_dir": str(work_dir),
            "language_results": language_results,
            "charts_and_reports": {},
        }

        # Collect chart and report paths for easy access
        for lang, results in language_results.items():
            if results.get("report", {}).get("ok", False):
                report_data = results["report"].get("data", {})
                if report_data:
                    final_data["charts_and_reports"][lang] = {
                        "chart_path": report_data.get("chart_path"),
                        "report_path": report_data.get("report_path"),
                    }

        # Determine next step
        if overall_ok:
            next_step = f"Workflow completed successfully. Reports generated in {work_dir}/"
        else:
            next_step = f"Workflow partially failed. Check warnings and fix issues for languages: {', '.join(failed_languages)}"

        _print_json_and_exit(
            ok=overall_ok,
            data=final_data,
            warnings=all_warnings,
            next_step=next_step,
            exit_code=exit_code,
            work_dir=work_dir,
        )


if __name__ == "__main__":
    main()
