from __future__ import annotations

import argparse
import logging
import os
import sys
import shutil
from pathlib import Path

from src.app.use_cases import (
    BuildProfilingPlanUseCase,
    GenerateReportUseCase,
    InspectSchemaUseCase,
)
from src.config import AppSettings, get_settings
from src.infra.db import EngineFactory, SqlAlchemyExecutor
from src.infra.planners import DefaultCollectorRegistry, ProfilingPlanBuilder
from src.infra.rendering import JinjaReportRenderer
from src.infra.schema import PostgresSchemaReader

logger = logging.getLogger(__name__)


def copy_assets_to_output(project_root: Path, output_html_path: Path) -> None:
    source_assets_dir = project_root / "src" / "assets"
    target_assets_dir = output_html_path.parent / "assets"

    if not source_assets_dir.exists():
        return

    if target_assets_dir.exists():
        shutil.rmtree(target_assets_dir)

    shutil.copytree(source_assets_dir, target_assets_dir)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a static HTML dashboard for the configured PostgreSQL Post table.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional path to a .env file. Defaults to ./.env when present.",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=None,
        help="Optional template directory. Defaults to ./src/presentation/templates when it exists.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop execution on the first collector failure instead of continuing.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Render the report but do not write index.html to disk.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the rendered HTML to stdout after generation.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        help="Optional log level (DEBUG, INFO, WARNING, ERROR). Defaults to APP_LOG_LEVEL or INFO.",
    )
    return parser.parse_args()


def configure_logging(level: str | None) -> None:
    configured_level = (level or os.getenv("APP_LOG_LEVEL", "INFO")).upper()
    resolved_level = getattr(logging, configured_level, logging.INFO)
    logging.basicConfig(
        level=resolved_level,
        format="[%(asctime)s - %(levelname)s] %(message)s",
    )
    logger.debug("Logging configured", extra={"level": configured_level})


def resolve_template_dir(project_root: Path, explicit_template_dir: Path | None) -> Path | None:
    if explicit_template_dir is not None:
        return explicit_template_dir

    default_template_dir = project_root / "src" / "presentation" / "templates"
    if default_template_dir.exists():
        return default_template_dir
    return None


def build_use_case(
    *,
    template_dir: Path | None,
    fail_fast: bool,
    write_output_file: bool,
) -> GenerateReportUseCase:
    logger.info("Building report-generation use case")
    schema_reader = PostgresSchemaReader()
    inspect_schema_use_case = InspectSchemaUseCase(schema_reader=schema_reader)

    profiling_plan_builder = ProfilingPlanBuilder()
    build_profiling_plan_use_case = BuildProfilingPlanUseCase(plan_builder=profiling_plan_builder)

    collector_registry = DefaultCollectorRegistry()
    collectors = collector_registry.all()
    renderer = JinjaReportRenderer(template_dir=template_dir)

    logger.info("Use case dependencies prepared")
    logger.debug(
        "Collector registry loaded",
        extra={"collector_count": len(collectors), "template_dir": str(template_dir) if template_dir else None},
    )

    return GenerateReportUseCase(
        inspect_schema_use_case=inspect_schema_use_case,
        build_profiling_plan_use_case=build_profiling_plan_use_case,
        collectors=collectors,
        renderer=renderer,
        fail_fast=fail_fast,
        write_output_file=write_output_file,
    )


def print_summary(result, settings: AppSettings) -> None:
    summary = result.execution_summary
    success_count = len(summary.successful_records)
    skipped_count = len(summary.skipped_records)
    failed_count = len(summary.failed_records)

    print("Report generation finished.")
    print(f"Table: {result.report.metadata.table_qualified_name}")
    print(f"Rows: {result.report.metadata.row_count if result.report.metadata.row_count is not None else 'unknown'}")
    print(f"Sections: {len(result.report.sections)}")
    print(f"Collectors: {success_count} succeeded, {skipped_count} skipped, {failed_count} failed")
    print(f"Duration: {summary.total_duration_ms} ms")
    if result.output_path is not None:
        print(f"HTML written to: {result.output_path.resolve()}")
    else:
        print(f"HTML output was not written. Configured output would be: {(settings.report.output_path).resolve()}")

    if failed_count:
        print("Failed collectors:", file=sys.stderr)
        for record in summary.failed_records:
            message = record.error_message or "unknown error"
            print(f"  - {record.collector_name} ({record.section_key}): {message}", file=sys.stderr)

    logger.info(
        "Report summary",
        extra={
            "table": result.report.metadata.table_qualified_name,
            "sections": len(result.report.sections),
            "success_collectors": success_count,
            "skipped_collectors": skipped_count,
            "failed_collectors": failed_count,
            "duration_ms": summary.total_duration_ms,
            "output_path": str(result.output_path) if result.output_path else None,
        },
    )


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)

    project_root = Path(__file__).resolve().parent
    logger.info("Starting dashboard pipeline execution")
    logger.debug(
        "CLI arguments",
        extra={
            "env_file": str(args.env_file) if args.env_file else None,
            "template_dir": str(args.template_dir) if args.template_dir else None,
            "fail_fast": args.fail_fast,
            "no_write": args.no_write,
            "stdout": args.stdout,
        },
    )

    try:
        logger.info("Loading application settings")
        settings = get_settings(env_file=args.env_file, refresh=True)
        template_dir = resolve_template_dir(project_root, args.template_dir)

        if template_dir is not None and not template_dir.exists():
            raise FileNotFoundError(f"Template directory does not exist: {template_dir}")

        logger.info("Creating database engine")
        engine = EngineFactory(settings.database).create()
        executor = SqlAlchemyExecutor(engine)

        try:
            logger.info("Executing report generation use case")
            use_case = build_use_case(
                template_dir=template_dir,
                fail_fast=args.fail_fast,
                write_output_file=not args.no_write,
            )
            result = use_case.execute(settings=settings, executor=executor)
            
            if result.output_path is not None:
                copy_assets_to_output(project_root, result.output_path)
        finally:
            logger.info("Closing database executor")
            executor.close()

        print_summary(result, settings)

        if args.stdout:
            print("\n----- BEGIN HTML -----\n")
            print(result.html)
            print("\n----- END HTML -----")

        return 0
    except KeyboardInterrupt:
        logger.warning("Execution cancelled by user")
        print("Execution cancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        logger.exception("Unhandled execution error")
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
