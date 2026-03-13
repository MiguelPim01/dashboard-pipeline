from __future__ import annotations

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.widgets import TableWidget

from ._helpers import format_human_count, format_percent, qualified_table_name, quote_ident


class ColumnNullsCollector(MetricCollector):
    @property
    def name(self) -> str:
        return "column_nulls"

    @property
    def section_key(self) -> str:
        return "column_profiles"

    @property
    def order(self) -> int:
        return 50

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.MEDIUM

    def collect(self, context: CollectionContext) -> MetricResult:
        rules = [rule for rule in context.profiling_plan.rules if rule.compute_nulls]
        if not rules:
            return MetricResult(
                collector_name=self.name,
                section_key=self.section_key,
                section_title="Column profiles",
                section_subtitle="Per-column data quality and distribution summaries.",
                section_order=self.order,
                skipped=True,
                warnings=("No columns were eligible for null profiling.",),
            )

        table_name = qualified_table_name(context)
        select_parts = [
            f"SUM(CASE WHEN {quote_ident(rule.column_name)} IS NULL THEN 1 ELSE 0 END) AS {quote_ident(rule.column_name)}"
            for rule in rules
        ]
        row = context.executor.fetch_one(f"SELECT {', '.join(select_parts)} FROM {table_name}") or {}
        total_rows = context.get_shared("row_count") or context.table_schema.estimated_row_count or 0
        rows = []
        for rule in rules:
            null_count = int(row.get(rule.column_name) or 0)
            null_ratio = (null_count / total_rows) if total_rows else None
            rows.append((rule.column_name, format_human_count(null_count), format_percent(null_ratio), rule.scope.value))

        return MetricResult(
            collector_name=self.name,
            section_key=self.section_key,
            section_title="Column profiles",
            section_subtitle="Per-column data quality and distribution summaries.",
            section_order=self.order,
            widgets=(
                TableWidget(
                    widget_id="column-profile-nulls",
                    title="Null profile by column",
                    columns=("Column", "Null count", "Null ratio", "Scope"),
                    rows=tuple(rows),
                ),
            ),
        )
