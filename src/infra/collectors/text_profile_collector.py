from __future__ import annotations

from dataclasses import dataclass

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.profiling import ProfilingScope
from src.domain.models.widgets import TableWidget

from ._helpers import qualified_table_name, quote_ident


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
        rows = []
        for rule in candidates:
            quoted = quote_ident(rule.column_name)
            where_clause = f"WHERE {quoted} IS NOT NULL"
            stats_row = context.executor.fetch_one(
                f"""
                SELECT
                    AVG(LENGTH(CAST({quoted} AS TEXT))) AS avg_length,
                    MAX(LENGTH(CAST({quoted} AS TEXT))) AS max_length,
                    COUNT(*) FILTER (WHERE LENGTH(TRIM(CAST({quoted} AS TEXT))) = 0) AS empty_strings
                FROM {table_name}
                {where_clause}
                """
            ) or {}
            rows.append(
                (
                    rule.column_name,
                    rule.scope.value,
                    f"{float(stats_row.get('avg_length') or 0):.1f}",
                    str(int(stats_row.get("max_length") or 0)),
                    str(int(stats_row.get("empty_strings") or 0)),
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
                    widget_id="column-text-profile",
                    title="Text length profile",
                    columns=("Column", "Scope", "Avg length", "Max length", "Empty strings"),
                    rows=tuple(rows),
                ),
            ),
        )
