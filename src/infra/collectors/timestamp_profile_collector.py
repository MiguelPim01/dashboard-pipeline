from __future__ import annotations

from dataclasses import dataclass

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.widgets import TableWidget

from ._helpers import format_temporal, qualified_table_name, quote_ident


@dataclass(frozen=True, slots=True)
class TimestampProfileCollector(MetricCollector):
    max_columns: int = 4

    @property
    def name(self) -> str:
        return "timestamp_profiles"

    @property
    def section_key(self) -> str:
        return "column_profiles"

    @property
    def order(self) -> int:
        return 65

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.MEDIUM

    def collect(self, context: CollectionContext) -> MetricResult:
        candidates = [rule for rule in context.profiling_plan.rules if rule.compute_temporal_summary][: self.max_columns]
        if not candidates:
            return MetricResult(
                collector_name=self.name,
                section_key=self.section_key,
                section_title="Column profiles",
                section_subtitle="Per-column data quality and distribution summaries.",
                section_order=self.order,
                skipped=True,
                warnings=("No temporal columns were eligible for profiling.",),
            )

        table_name = qualified_table_name(context)
        rows = []
        for rule in candidates:
            quoted = quote_ident(rule.column_name)
            stats_row = context.executor.fetch_one(
                f"SELECT MIN({quoted}) AS min_value, MAX({quoted}) AS max_value FROM {table_name}"
            ) or {}
            rows.append(
                (
                    rule.column_name,
                    rule.scope.value,
                    format_temporal(stats_row.get("min_value")),
                    format_temporal(stats_row.get("max_value")),
                )
            )

        return MetricResult(
            collector_name=self.name,
            section_key=self.section_key,
            section_title="Column profiles",
            section_subtitle="Per-column data quality and distribution summaries.",
            section_order=self.order,
            widgets=(
                TableWidget(
                    widget_id="column-timestamp-profile",
                    title="Temporal profile",
                    columns=("Column", "Scope", "Min value", "Max value"),
                    rows=tuple(rows),
                ),
            ),
        )
