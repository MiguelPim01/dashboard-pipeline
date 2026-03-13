from __future__ import annotations

from dataclasses import dataclass

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.widgets import ChartWidget, ChartType, ChartDataset

from ._helpers import qualified_table_name, quote_ident


@dataclass(frozen=True, slots=True)
class CategoricalDistributionCollector(MetricCollector):
    max_columns: int = 5

    @property
    def name(self) -> str:
        return "column_distributions"

    @property
    def section_key(self) -> str:
        return "column_profiles"

    @property
    def order(self) -> int:
        return 55

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.MEDIUM

    @staticmethod
    def _short_label(value: str, max_len: int = 40) -> str:
        value = value.replace("\n", " ").strip()
        return value if len(value) <= max_len else value[: max_len - 1] + "…"

    def collect(self, context: CollectionContext) -> MetricResult:
        candidates = [
            rule
            for rule in context.profiling_plan.rules
            if rule.compute_top_values
            and context.table_schema.get_column(rule.column_name).is_categorical_candidate
        ][: self.max_columns]

        if not candidates:
            return MetricResult(
                collector_name=self.name,
                section_key=self.section_key,
                section_title="Column profiles",
                section_subtitle="Per-column data quality and distribution summaries.",
                section_order=self.order,
                skipped=True,
                warnings=("No categorical columns were eligible for top-value profiling.",),
            )

        table_name = qualified_table_name(context)
        widgets = []
        limit = context.profiling_settings.max_top_values_per_column

        for rule in candidates:
            quoted = quote_ident(rule.column_name)
            rows = context.executor.fetch_all(
                f"""
                SELECT CAST({quoted} AS TEXT) AS value, COUNT(*) AS value_count
                FROM {table_name}
                WHERE {quoted} IS NOT NULL
                GROUP BY CAST({quoted} AS TEXT)
                ORDER BY value_count DESC, value ASC
                LIMIT {int(limit)}
                """
            )

            if not rows:
                continue

            labels = tuple(
                self._short_label(str(row["value"]) if row["value"] is not None else "<NULL>")
                for row in rows
            )
            counts = tuple(int(row["value_count"]) for row in rows)

            widgets.append(
                ChartWidget(
                    widget_id=f"column-top-values-{rule.column_name}",
                    title=f"Top values: {rule.column_name}",
                    subtitle=f"Top {len(labels)} values for a categorical-like column",
                    chart_type=ChartType.BAR,
                    labels=labels,
                    datasets=(
                        ChartDataset(
                            label="Count",
                            values=counts,
                        ),
                    ),
                    height_px=max(280, 42 * len(labels) + 80),
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
