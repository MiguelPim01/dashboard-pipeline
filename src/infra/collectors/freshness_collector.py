from __future__ import annotations

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.widgets import AlertWidget, KpiCard
from src.domain.enums.report_critics import ReportCriticsEnum

from ._helpers import format_human_count, qualified_table_name, quote_ident, select_reference_timestamp_column


class FreshnessCollector(MetricCollector):
    @property
    def name(self) -> str:
        return "freshness"

    @property
    def section_key(self) -> str:
        return "freshness"

    @property
    def order(self) -> int:
        return 20

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.MEDIUM

    def collect(self, context: CollectionContext) -> MetricResult:
        timestamp_column = select_reference_timestamp_column(context)
        if timestamp_column is None:
            return MetricResult(
                collector_name=self.name,
                section_key=self.section_key,
                section_title="Freshness",
                section_subtitle="Recent-ingestion and timestamp coverage metrics.",
                section_order=self.order,
                skipped=True,
                warnings=("No temporal column is available for freshness analysis.",),
            )

        table_name = qualified_table_name(context)
        quoted_column = quote_ident(timestamp_column.name)
        query = f"""
        SELECT
            COUNT(*) FILTER (WHERE {quoted_column} >= NOW() - INTERVAL '24 hours') AS last_24h,
            COUNT(*) FILTER (WHERE {quoted_column} >= NOW() - INTERVAL '7 days') AS last_7d,
            COUNT(*) FILTER (WHERE {quoted_column} >= NOW() - INTERVAL '30 days') AS last_30d,
            MAX({quoted_column}) AS latest_value
        FROM {table_name}
        """
        row = context.executor.fetch_one(query) or {}
        latest_value = row.get("latest_value")
        alerts = ()
        if latest_value is None:
            alerts = (
                AlertWidget(
                    widget_id="freshness-empty-table",
                    title="No recent timestamps found",
                    message=f"The selected timestamp column '{timestamp_column.name}' has no values.",
                    critic_level=ReportCriticsEnum.NON_CRITICAL,
                ),
            )

        return MetricResult(
            collector_name=self.name,
            section_key=self.section_key,
            section_title="Freshness",
            section_subtitle="Recent-ingestion and timestamp coverage metrics.",
            section_order=self.order,
            widgets=(
                KpiCard(widget_id="freshness-24h", title="Rows in last 24h", value=format_human_count(row.get("last_24h"))),
                KpiCard(widget_id="freshness-7d", title="Rows in last 7 days", value=format_human_count(row.get("last_7d"))),
                KpiCard(widget_id="freshness-30d", title="Rows in last 30 days", value=format_human_count(row.get("last_30d"))),
            ),
            alerts=alerts,
            metadata={"reference_timestamp_column": timestamp_column.name},
        )
