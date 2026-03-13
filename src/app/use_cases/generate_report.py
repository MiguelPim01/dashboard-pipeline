from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Iterable

from src.app.contracts import DatabaseExecutor, MetricCollector, ReportRenderer
from src.app.dto import (
    CollectionContext,
    CollectorExecutionRecord,
    CollectorRunStatus,
    ExecutionSummary,
    MetricResult,
)
from src.config import AppSettings
from src.domain.enums.report_critics import ReportCriticsEnum
from src.domain.models.report import Report, ReportMetadata
from src.domain.models.section import ReportSection
from src.domain.models.widgets import AlertWidget

from .build_profiling_plan import BuildProfilingPlanUseCase
from .inspect_schema import InspectSchemaUseCase

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GenerateReportResult:
    """Return object for the full report-generation workflow."""

    report: Report
    html: str
    execution_summary: ExecutionSummary
    output_path: Path | None = None


@dataclass(slots=True)
class _SectionAccumulator:
    key: str
    title: str
    subtitle: str | None
    order: int
    widgets: list = None
    alerts: list = None

    def __post_init__(self) -> None:
        if self.widgets is None:
            self.widgets = []
        if self.alerts is None:
            self.alerts = []

    def add_result(self, result: MetricResult) -> None:
        if not self.title and result.section_title:
            self.title = result.section_title
        if self.subtitle is None and result.section_subtitle is not None:
            self.subtitle = result.section_subtitle
        self.order = min(self.order, result.section_order)
        self.widgets.extend(result.widgets)
        self.alerts.extend(result.alerts)

    def build(self) -> ReportSection:
        return ReportSection(
            key=self.key,
            title=self.title,
            subtitle=self.subtitle,
            order=self.order,
            widgets=tuple(self.widgets),
            alerts=tuple(self.alerts),
        )


class GenerateReportUseCase:
    """Orchestrate schema inspection, profiling, collection, and rendering."""

    def __init__(
        self,
        inspect_schema_use_case: InspectSchemaUseCase,
        build_profiling_plan_use_case: BuildProfilingPlanUseCase,
        collectors: Iterable[MetricCollector],
        renderer: ReportRenderer,
        *,
        fail_fast: bool = False,
        write_output_file: bool = True,
    ) -> None:
        self._inspect_schema_use_case = inspect_schema_use_case
        self._build_profiling_plan_use_case = build_profiling_plan_use_case
        self._collectors = tuple(collectors)
        self._renderer = renderer
        self._fail_fast = fail_fast
        self._write_output_file = write_output_file

    def execute(
        self,
        settings: AppSettings,
        executor: DatabaseExecutor,
    ) -> GenerateReportResult:
        started_at = datetime.now(timezone.utc)
        logger.info("Starting report-generation workflow")

        schema = self._inspect_schema_use_case.execute(executor, settings)
        logger.info("Schema inspection complete")
        logger.debug("Schema details", extra={"table": schema.qualified_name, "column_count": len(schema.columns)})

        profiling_plan = self._build_profiling_plan_use_case.execute(schema, settings)
        logger.info("Profiling plan built")
        logger.debug("Profiling plan details", extra={"rule_count": len(profiling_plan.rules)})

        context = CollectionContext(
            settings=settings,
            executor=executor,
            table_schema=schema,
            profiling_plan=profiling_plan,
            run_started_at=started_at,
        )

        metric_results: list[MetricResult] = []
        execution_records: list[CollectorExecutionRecord] = []

        logger.info("Executing collectors")
        logger.debug("Collectors configured", extra={"collector_count": len(self._collectors), "fail_fast": self._fail_fast})

        for collector in sorted(self._collectors, key=lambda item: (item.order, item.name)):
            if not collector.is_enabled(context):
                logger.debug(
                    "Collector skipped",
                    extra={"collector": collector.name, "section": collector.section_key, "reason": "disabled"},
                )
                execution_records.append(
                    CollectorExecutionRecord(
                        collector_name=collector.name,
                        section_key=collector.section_key,
                        status=CollectorRunStatus.SKIPPED,
                    )
                )
                continue

            collector_started = datetime.now(timezone.utc)
            try:
                logger.debug("Collector started", extra={"collector": collector.name, "section": collector.section_key})
                result = collector.collect(context)
                collector_finished = datetime.now(timezone.utc)
                duration_ms = int((collector_finished - collector_started).total_seconds() * 1000)

                if result.execution_duration_ms is None:
                    result = MetricResult(
                        collector_name=result.collector_name,
                        section_key=result.section_key,
                        section_title=result.section_title,
                        section_subtitle=result.section_subtitle,
                        section_order=result.section_order,
                        widgets=result.widgets,
                        alerts=result.alerts,
                        warnings=result.warnings,
                        execution_duration_ms=duration_ms,
                        metadata=result.metadata,
                        skipped=result.skipped,
                    )

                metric_results.append(result)
                execution_records.append(
                    CollectorExecutionRecord(
                        collector_name=result.collector_name,
                        section_key=result.section_key,
                        status=CollectorRunStatus.SKIPPED if result.skipped else CollectorRunStatus.SUCCESS,
                        duration_ms=result.execution_duration_ms,
                        warnings=result.warnings,
                    )
                )
                logger.debug(
                    "Collector completed",
                    extra={
                        "collector": result.collector_name,
                        "section": result.section_key,
                        "duration_ms": result.execution_duration_ms,
                        "status": "skipped" if result.skipped else "success",
                    },
                )
            except Exception as exc:
                collector_finished = datetime.now(timezone.utc)
                duration_ms = int((collector_finished - collector_started).total_seconds() * 1000)
                execution_records.append(
                    CollectorExecutionRecord(
                        collector_name=collector.name,
                        section_key=collector.section_key,
                        status=CollectorRunStatus.FAILED,
                        duration_ms=duration_ms,
                        error_message=str(exc),
                    )
                )
                logger.exception(
                    "Collector failed",
                    extra={"collector": collector.name, "section": collector.section_key, "duration_ms": duration_ms},
                )
                if self._fail_fast:
                    logger.warning("Fail-fast enabled; aborting after collector failure")
                    raise

        finished_at = datetime.now(timezone.utc)
        execution_summary = ExecutionSummary(
            started_at=started_at,
            finished_at=finished_at,
            records=tuple(execution_records),
        )

        logger.info(
            "Collector execution finished",
            extra={
                "successful": len(execution_summary.successful_records),
                "skipped": len(execution_summary.skipped_records),
                "failed": len(execution_summary.failed_records),
                "duration_ms": execution_summary.total_duration_ms,
            },
        )

        report = Report(
            metadata=ReportMetadata(
                title=settings.report.title,
                subtitle=settings.report.subtitle,
                generated_at=finished_at,
                table_qualified_name=schema.qualified_name,
                row_count=self._resolve_row_count(schema, context),
                execution_duration_ms=execution_summary.total_duration_ms,
            ),
            sections=self._build_sections(metric_results),
            global_alerts=self._build_global_alerts(execution_summary),
        )

        html = self._renderer.render(report)
        output_path: Path | None = None
        if self._write_output_file:
            output_path = self._renderer.render_to_file(report, settings.report.output_path)
            logger.info("Report rendered to file", extra={"output_path": str(output_path)})
        else:
            logger.info("Report rendered without file output")

        return GenerateReportResult(
            report=report,
            html=html,
            execution_summary=execution_summary,
            output_path=output_path,
        )

    @staticmethod
    def _resolve_row_count(schema, context: CollectionContext) -> int | None:
        shared_row_count = context.get_shared("row_count")
        if isinstance(shared_row_count, int) and shared_row_count >= 0:
            return shared_row_count
        return schema.estimated_row_count

    @staticmethod
    def _build_sections(metric_results: Iterable[MetricResult]) -> tuple[ReportSection, ...]:
        sections: dict[str, _SectionAccumulator] = {}
        for result in metric_results:
            if result.skipped:
                continue
            accumulator = sections.get(result.section_key)
            if accumulator is None:
                accumulator = _SectionAccumulator(
                    key=result.section_key,
                    title=result.section_title,
                    subtitle=result.section_subtitle,
                    order=result.section_order,
                )
                sections[result.section_key] = accumulator
            accumulator.add_result(result)

        built_sections = tuple(
            accumulator.build()
            for accumulator in sorted(sections.values(), key=lambda item: (item.order, item.key))
        )
        return tuple(section for section in built_sections if not section.is_empty)

    @staticmethod
    def _build_global_alerts(execution_summary: ExecutionSummary) -> tuple[AlertWidget, ...]:
        alerts: list[AlertWidget] = []
        for failed_record in execution_summary.failed_records:
            message = f"Collector '{failed_record.collector_name}' failed and its section may be incomplete."
            details = []
            if failed_record.error_message:
                details.append(failed_record.error_message)
            alerts.append(
                AlertWidget(
                    widget_id=f"collector-failure-{failed_record.collector_name}",
                    title="Collector failure",
                    message=message,
                    critic_level=ReportCriticsEnum.NON_CRITICAL,
                    details=tuple(details),
                )
            )
        return tuple(alerts)
