from __future__ import annotations

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.widgets import KpiCard

from ._helpers import format_human_count, format_temporal, qualified_table_name, select_reference_timestamp_column


class OverviewCollector(MetricCollector):
    @property
    def name(self) -> str:
        return "overview"

    @property
    def section_key(self) -> str:
        return "overview"

    @property
    def order(self) -> int:
        return 10

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.LOW

    def collect(self, context: CollectionContext) -> MetricResult:
        table_name = qualified_table_name(context)
        row_count = context.table_schema.estimated_row_count
        if context.profiling_settings.allow_full_table_count:
            row_count = context.executor.fetch_scalar(f"SELECT COUNT(*) FROM {table_name}")
        context.put_shared("row_count", int(row_count) if row_count is not None else None)

        timestamp_column = select_reference_timestamp_column(context)
        min_timestamp = None
        max_timestamp = None
        if timestamp_column is not None:
            quoted_column = '"' + timestamp_column.name.replace('"', '""') + '"'
            temporal_row = context.executor.fetch_one(
                f"SELECT MIN({quoted_column}) AS min_value, MAX({quoted_column}) AS max_value FROM {table_name}"
            ) or {}
            min_timestamp = temporal_row.get("min_value")
            max_timestamp = temporal_row.get("max_value")
            context.put_shared("reference_timestamp_column", timestamp_column.name)

        widgets = (
            KpiCard(widget_id="overview-row-count", title="Rows", value=format_human_count(row_count)),
            KpiCard(widget_id="overview-column-count", title="Columns", value=str(len(context.table_schema.columns))),
            KpiCard(widget_id="overview-oldest-post", title="Oldest timestamp", value=format_temporal(min_timestamp)),
            KpiCard(widget_id="overview-latest-post", title="Latest timestamp", value=format_temporal(max_timestamp)),
        )
        return MetricResult(
            collector_name=self.name,
            section_key=self.section_key,
            section_title="Overview",
            section_subtitle="High-level table information and key statistics.",
            section_order=self.order,
            widgets=widgets,
            metadata={"reference_timestamp_column": timestamp_column.name if timestamp_column else None},
        )
