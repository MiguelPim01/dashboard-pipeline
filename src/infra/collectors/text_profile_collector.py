from __future__ import annotations

from dataclasses import dataclass

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.widgets import ChartDataset, ChartType, ChartWidget, TableWidget

from ._helpers import format_percent, qualified_table_name, quote_ident


@dataclass(frozen=True, slots=True)
class TextProfileCollector(MetricCollector):
    max_columns: int = 5

    @property
    def name(self) -> str:
        return "text_profiles"

    @property
    def section_key(self) -> str:
        return "column_profiles"

    @property
    def order(self) -> int:
        return 60

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.HIGH

    @staticmethod
    def _short_label(value: str, max_len: int = 28) -> str:
        value = value.replace("\n", " ").strip()
        return value if len(value) <= max_len else value[: max_len - 1] + "…"

    def collect(self, context: CollectionContext) -> MetricResult:
        candidates = [rule for rule in context.profiling_plan.rules if rule.compute_text_summary][: self.max_columns]
        if not candidates:
            return MetricResult(
                collector_name=self.name,
                section_key=self.section_key,
                section_title="Column profiles",
                section_subtitle="Per-column data quality and distribution summaries.",
                section_order=self.order,
                skipped=True,
                warnings=("No text columns were eligible for profiling.",),
            )

        table_name = qualified_table_name(context)
        table_rows = []
        chart_stats = []

        for rule in candidates:
            quoted = quote_ident(rule.column_name)
            stats_row = context.executor.fetch_one(
                f"""
                SELECT
                    COUNT(*) AS non_null_rows,
                    AVG(LENGTH(CAST({quoted} AS TEXT))) AS avg_length,
                    MAX(LENGTH(CAST({quoted} AS TEXT))) AS max_length,
                    COUNT(*) FILTER (WHERE LENGTH(TRIM(CAST({quoted} AS TEXT))) = 0) AS empty_strings
                FROM {table_name}
                WHERE {quoted} IS NOT NULL
                """
            ) or {}

            non_null_rows = int(stats_row.get("non_null_rows") or 0)
            empty_strings = int(stats_row.get("empty_strings") or 0)
            empty_ratio = (empty_strings / non_null_rows) if non_null_rows else 0.0
            avg_length = float(stats_row.get("avg_length") or 0)
            max_length = int(stats_row.get("max_length") or 0)

            table_rows.append(
                (
                    rule.column_name,
                    rule.scope.value,
                    f"{avg_length:.1f}",
                    str(max_length),
                    str(empty_strings),
                    format_percent(empty_ratio),
                )
            )

            chart_stats.append(
                {
                    "column": rule.column_name,
                    "empty_strings": empty_strings,
                    "empty_ratio": empty_ratio,
                }
            )

        chart_stats = [
            item
            for item in sorted(
                chart_stats,
                key=lambda item: (item["empty_ratio"], item["empty_strings"]),
                reverse=True,
            )
            if item["empty_strings"] > 0
        ]

        widgets = []

        if chart_stats:
            widgets.append(
                ChartWidget(
                    widget_id="column-profile-empty-string-ratio-chart",
                    title="Top columns by empty-string percentage",
                    subtitle="Percentage of empty strings among non-null text values.",
                    chart_type=ChartType.BAR,
                    labels=tuple(self._short_label(item["column"]) for item in chart_stats),
                    datasets=(
                        ChartDataset(
                            label="Empty string %",
                            values=tuple(round(item["empty_ratio"] * 100, 2) for item in chart_stats),
                        ),
                    ),
                    height_px=340,
                )
            )

        widgets.append(
            TableWidget(
                widget_id="column-text-profile",
                title="Text length profile",
                columns=("Column", "Scope", "Avg length", "Max length", "Empty strings", "Empty ratio"),
                rows=tuple(table_rows),
            )
        )

        return MetricResult(
            collector_name=self.name,
            section_key=self.section_key,
            section_title="Column profiles",
            section_subtitle="Per-column data quality and distribution summaries.",
            section_order=self.order,
            widgets=tuple(widgets),
        )