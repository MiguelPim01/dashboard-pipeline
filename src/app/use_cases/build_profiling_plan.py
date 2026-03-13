from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Protocol

from src.config import AppSettings, ProfilingSettings
from src.domain.models.profiling import ColumnProfilingRule, ProfilingPlan, ProfilingScope
from src.domain.models.schema import LogicalColumnType, TableSchema

logger = logging.getLogger(__name__)


class ProfilingPlanBuilder(Protocol):
    """Protocol implemented by infrastructure planners."""

    def build(self, table_schema: TableSchema, settings: ProfilingSettings) -> ProfilingPlan: ...


@dataclass(frozen=True, slots=True)
class BuildProfilingPlanUseCase:
    """Create a per-column profiling plan for the report run.

    If an infrastructure planner is supplied, the use case delegates to it.
    Otherwise it falls back to a deterministic default strategy suitable for a
    large table with a mix of exact, sample-based, and skipped profiling.
    """

    plan_builder: ProfilingPlanBuilder | None = None

    def execute(
        self,
        table_schema: TableSchema,
        settings: AppSettings | ProfilingSettings,
    ) -> ProfilingPlan:
        profiling_settings = settings.profiling if isinstance(settings, AppSettings) else settings
        if self.plan_builder is not None:
            logger.debug("Using injected profiling plan builder")
            plan = self.plan_builder.build(table_schema, profiling_settings)
            logger.info("Profiling plan generated", extra={"rule_count": len(plan.rules)})
            return plan

        logger.debug("Using default profiling plan strategy")
        plan = self._build_default_plan(table_schema, profiling_settings)
        logger.info("Profiling plan generated", extra={"rule_count": len(plan.rules)})
        return plan

    def _build_default_plan(
        self,
        table_schema: TableSchema,
        settings: ProfilingSettings,
    ) -> ProfilingPlan:
        rules: list[ColumnProfilingRule] = []
        full_text_columns_used = 0
        exact_distinct_columns_used = 0

        for column in table_schema.columns:
            notes: list[str] = []

            if settings.should_skip(column.name):
                rules.append(
                    ColumnProfilingRule(
                        column_name=column.name,
                        logical_type=column.logical_type,
                        scope=ProfilingScope.SKIP,
                        compute_nulls=False,
                        notes=("Skipped explicitly by configuration.",),
                    )
                )
                continue

            scope = ProfilingScope.EXACT
            sample_rows: int | None = None

            if settings.is_heavy(column.name):
                if settings.sampling_enabled:
                    scope = ProfilingScope.SAMPLE
                    sample_rows = settings.sample_rows
                    notes.append("Heavy column profiled using configured sampling.")
                else:
                    scope = ProfilingScope.METADATA
                    notes.append("Heavy column limited to metadata-derived profiling.")

            elif column.logical_type in {LogicalColumnType.JSON, LogicalColumnType.ARRAY, LogicalColumnType.BINARY}:
                if settings.sampling_enabled:
                    scope = ProfilingScope.SAMPLE
                    sample_rows = settings.sample_rows
                    notes.append("Complex column type profiled using sampling.")
                else:
                    scope = ProfilingScope.METADATA
                    notes.append("Complex column type limited to metadata-derived profiling.")

            elif column.is_textual and not settings.is_critical(column.name):
                if full_text_columns_used < settings.max_text_columns_full_scan:
                    full_text_columns_used += 1
                elif settings.sampling_enabled:
                    scope = ProfilingScope.SAMPLE
                    sample_rows = settings.sample_rows
                    notes.append("Text column downgraded to sampling to control scan cost.")
                else:
                    scope = ProfilingScope.METADATA
                    notes.append("Text column downgraded to metadata only to control scan cost.")

            compute_distinct = False
            distinct_is_exact = False
            if column.is_categorical_candidate or column.is_primary_key or settings.use_exact_distinct(column.name):
                if settings.use_exact_distinct(column.name) and exact_distinct_columns_used < settings.max_distinct_columns_exact:
                    compute_distinct = True
                    distinct_is_exact = True
                    exact_distinct_columns_used += 1
                elif column.is_categorical_candidate:
                    compute_distinct = True
                    notes.append("Distinct count may be approximate depending on collector strategy.")

            rules.append(
                ColumnProfilingRule(
                    column_name=column.name,
                    logical_type=column.logical_type,
                    scope=scope,
                    compute_nulls=scope is not ProfilingScope.SKIP,
                    compute_distinct=compute_distinct,
                    compute_top_values=column.is_categorical_candidate or settings.is_critical(column.name),
                    compute_numeric_summary=column.is_numeric,
                    compute_temporal_summary=column.is_temporal,
                    compute_text_summary=column.is_textual,
                    sample_rows=sample_rows,
                    notes=tuple(self._build_notes(column_type=column.logical_type, exact_distinct=distinct_is_exact, notes=notes)),
                )
            )

        return ProfilingPlan(rules=tuple(rules))

    @staticmethod
    def _build_notes(
        *,
        column_type: LogicalColumnType,
        exact_distinct: bool,
        notes: list[str],
    ) -> tuple[str, ...]:
        derived_notes = list(notes)
        if column_type.is_numeric:
            derived_notes.append("Numeric summary enabled.")
        if column_type.is_temporal:
            derived_notes.append("Temporal summary enabled.")
        if column_type.is_textual:
            derived_notes.append("Text length summary enabled.")
        if exact_distinct:
            derived_notes.append("Exact distinct count requested by configuration.")
        return tuple(dict.fromkeys(note for note in derived_notes if note.strip()))
