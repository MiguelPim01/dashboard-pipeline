from __future__ import annotations

from dataclasses import dataclass

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.enums.report_critics import ReportCriticsEnum
from src.domain.models.widgets import AlertWidget, TableWidget

from ._helpers import format_human_count, format_percent, qualified_table_name, quote_ident, select_reference_timestamp_column


@dataclass(frozen=True, slots=True)
class DataQualityCollector(MetricCollector):
    duplicate_check_limit: int = 5

    @property
    def name(self) -> str:
        return "quality"

    @property
    def section_key(self) -> str:
        return "quality"

    @property
    def order(self) -> int:
        return 45

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.MEDIUM

    def collect(self, context: CollectionContext) -> MetricResult:
        table_name = qualified_table_name(context)
        critical_columns = [
            column_name
            for column_name in context.profiling_settings.critical_columns
            if context.table_schema.has_column(column_name)
        ]
        widgets = []
        alerts = []

        if critical_columns:
            select_parts = [
                f"SUM(CASE WHEN {quote_ident(column_name)} IS NULL THEN 1 ELSE 0 END) AS {quote_ident(column_name)}"
                for column_name in critical_columns
            ]
            row = context.executor.fetch_one(f"SELECT {', '.join(select_parts)} FROM {table_name}") or {}
            total_rows = context.get_shared("row_count") or context.table_schema.estimated_row_count or 0
            rows = []
            for column_name in critical_columns:
                null_count = int(row.get(column_name) or 0)
                ratio = (null_count / total_rows) if total_rows else None
                rows.append((column_name, format_human_count(null_count), format_percent(ratio)))
                if ratio is not None and ratio >= 0.5:
                    alerts.append(
                        AlertWidget(
                            widget_id=f"quality-null-{column_name}",
                            title="High null ratio",
                            message=f"Critical column '{column_name}' is null in {format_percent(ratio)} of rows.",
                            critic_level=ReportCriticsEnum.NON_CRITICAL,
                        )
                    )
            widgets.append(
                TableWidget(
                    widget_id="quality-critical-nulls",
                    title="Nulls in critical columns",
                    columns=("Column", "Null count", "Null ratio"),
                    rows=tuple(rows),
                    compact=True,
                )
            )

        duplicate_candidate = None
        for candidate in ("id", "urlPost", "externalId"):
            if context.table_schema.has_column(candidate):
                duplicate_candidate = candidate
                break
        if duplicate_candidate is not None:
            quoted = quote_ident(duplicate_candidate)
            duplicate_row = context.executor.fetch_one(
                f"""
                SELECT COUNT(*) AS duplicate_groups
                FROM (
                    SELECT {quoted}
                    FROM {table_name}
                    WHERE {quoted} IS NOT NULL
                    GROUP BY {quoted}
                    HAVING COUNT(*) > 1
                    LIMIT {self.duplicate_check_limit}
                ) duplicates
                """
            ) or {}
            duplicate_groups = int(duplicate_row.get("duplicate_groups") or 0)
            widgets.append(
                TableWidget(
                    widget_id="quality-duplicate-summary",
                    title="Duplicate candidate summary",
                    columns=("Column", "Duplicate groups (capped query)"),
                    rows=((duplicate_candidate, format_human_count(duplicate_groups)),),
                    compact=True,
                )
            )
            if duplicate_groups > 0:
                alerts.append(
                    AlertWidget(
                        widget_id=f"quality-duplicates-{duplicate_candidate}",
                        title="Potential duplicates detected",
                        message=f"At least {duplicate_groups} duplicate value groups were found for '{duplicate_candidate}'.",
                        critic_level=ReportCriticsEnum.NON_CRITICAL,
                    )
                )

        timestamp_column = select_reference_timestamp_column(context)
        if timestamp_column is not None:
            quoted_ts = quote_ident(timestamp_column.name)
            future_row = context.executor.fetch_one(
                f"SELECT COUNT(*) AS future_rows FROM {table_name} WHERE {quoted_ts} > NOW() + INTERVAL '1 day'"
            ) or {}
            future_rows = int(future_row.get("future_rows") or 0)
            widgets.append(
                TableWidget(
                    widget_id="quality-time-anomalies",
                    title="Temporal anomaly checks",
                    columns=("Check", "Value"),
                    rows=((f"Rows where {timestamp_column.name} is > now + 1 day", format_human_count(future_rows)),),
                    compact=True,
                )
            )
            if future_rows > 0:
                alerts.append(
                    AlertWidget(
                        widget_id="quality-future-timestamps",
                        title="Future timestamps detected",
                        message=f"{future_rows} rows have {timestamp_column.name} in the future.",
                        critic_level=ReportCriticsEnum.NON_CRITICAL,
                    )
                )

        return MetricResult(
            collector_name=self.name,
            section_key=self.section_key,
            section_title="Data quality",
            section_subtitle="Basic null, duplicate, and anomaly checks.",
            section_order=self.order,
            widgets=tuple(widgets),
            alerts=tuple(alerts),
        )
