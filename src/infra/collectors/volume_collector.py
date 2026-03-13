from __future__ import annotations

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.widgets import ChartDataset, ChartType, ChartWidget

from ._helpers import qualified_table_name, quote_ident, select_reference_timestamp_column


class VolumeTrendCollector(MetricCollector):
    @property
    def name(self) -> str:
        return "volume_trends"

    @property
    def section_key(self) -> str:
        return "volume_trends"

    @property
    def order(self) -> int:
        return 30

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.MEDIUM

    def collect(self, context: CollectionContext) -> MetricResult:
        timestamp_column = select_reference_timestamp_column(context)
        if timestamp_column is None:
            return MetricResult(
                collector_name=self.name,
                section_key=self.section_key,
                section_title="Volume trends",
                section_subtitle="Row growth over time.",
                section_order=self.order,
                skipped=True,
                warnings=("No temporal column is available for trend analysis.",),
            )

        table_name = qualified_table_name(context)
        quoted_ts = quote_ident(timestamp_column.name)
        rows = context.executor.fetch_all(
            f"""
            SELECT
                DATE_TRUNC('day', {quoted_ts})::date AS bucket_day,
                COUNT(*) AS row_count
            FROM {table_name}
            WHERE {quoted_ts} IS NOT NULL
            GROUP BY 1
            ORDER BY 1
            LIMIT 365
            """
        )
        if not rows:
            return MetricResult(
                collector_name=self.name,
                section_key=self.section_key,
                section_title="Volume trends",
                section_subtitle="Row growth over time.",
                section_order=self.order,
                skipped=True,
                warnings=("No data is available to build volume trends.",),
            )

        labels = tuple(str(row["bucket_day"]) for row in rows)
        counts = tuple(int(row["row_count"]) for row in rows)
        cumulative: list[int] = []
        running = 0
        for count in counts:
            running += count
            cumulative.append(running)

        widgets = (
            ChartWidget(
                widget_id="volume-by-day",
                title="Rows per day",
                subtitle=f"Grouped by {timestamp_column.name}",
                chart_type=ChartType.LINE,
                labels=labels,
                datasets=(ChartDataset(label="Rows", values=counts),),
            ),
            ChartWidget(
                widget_id="volume-cumulative",
                title="Cumulative rows",
                subtitle="Running cumulative count within the sampled trend window",
                chart_type=ChartType.LINE,
                labels=labels,
                datasets=(ChartDataset(label="Cumulative rows", values=tuple(cumulative)),),
            ),
        )
        return MetricResult(
            collector_name=self.name,
            section_key=self.section_key,
            section_title="Volume trends",
            section_subtitle="Row growth over time.",
            section_order=self.order,
            widgets=widgets,
            metadata={"reference_timestamp_column": timestamp_column.name},
        )
