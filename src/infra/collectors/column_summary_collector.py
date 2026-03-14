from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.widgets import TableWidget

from ._helpers import qualified_table_name, quote_ident


@dataclass(frozen=True, slots=True)
class ColumnSummaryCollector(MetricCollector):
    @property
    def name(self) -> str:
        return "column_summary"

    @property
    def section_key(self) -> str:
        return "column_profiles"

    @property
    def order(self) -> int:
        return 58

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.HIGH

    @staticmethod
    def _format_int_pt(value: Any) -> str:
        if value is None:
            return "—"
        try:
            number = int(value)
        except (TypeError, ValueError):
            return str(value)
        return f"{number:,}".replace(",", ".")

    @staticmethod
    def _format_decimal_pt(value: Any, decimals: int = 2) -> str:
        if value is None:
            return "—"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        formatted = f"{number:,.{decimals}f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    @classmethod
    def _format_percent_pt(cls, ratio: float | None) -> str:
        if ratio is None:
            return "—"
        return f"{cls._format_decimal_pt(ratio * 100, 2)}%"

    @classmethod
    def _format_scalar_pt(cls, value: Any) -> str:
        if value is None:
            return "—"

        if isinstance(value, Decimal):
            if value == value.to_integral():
                return cls._format_int_pt(int(value))
            return cls._format_decimal_pt(value, 2)

        if isinstance(value, int):
            return cls._format_int_pt(value)

        if isinstance(value, float):
            if value.is_integer():
                return cls._format_int_pt(int(value))
            return cls._format_decimal_pt(value, 2)

        try:
            number = float(value)
            if number.is_integer():
                return cls._format_int_pt(int(number))
            return cls._format_decimal_pt(number, 2)
        except (TypeError, ValueError):
            return str(value)

    @classmethod
    def _format_stat_pt(cls, value: Any) -> str:
        if value is None:
            return "—"
        return cls._format_decimal_pt(value, 2)

    def collect(self, context: CollectionContext) -> MetricResult:
        table_name = qualified_table_name(context)
        total_rows = context.get_shared("row_count")

        if total_rows is None:
            total_rows = context.table_schema.estimated_row_count
        if total_rows is None:
            total_rows = context.executor.fetch_scalar(f"SELECT COUNT(*) FROM {table_name}")

        total_rows = int(total_rows or 0)
        columns = context.table_schema.columns

        # Exact null counts for all columns
        null_select_parts = [
            f"SUM(CASE WHEN {quote_ident(column.name)} IS NULL THEN 1 ELSE 0 END) AS {quote_ident(column.name)}"
            for column in columns
        ]
        null_row = context.executor.fetch_one(
            f"SELECT {', '.join(null_select_parts)} FROM {table_name}"
        ) or {}

        # Exact empty-string counts only for text columns
        text_columns = [column for column in columns if column.is_textual]
        empty_row: dict[str, Any] = {}
        if text_columns:
            empty_select_parts = [
                f"""SUM(
                        CASE
                            WHEN {quote_ident(column.name)} IS NOT NULL
                             AND LENGTH(TRIM(CAST({quote_ident(column.name)} AS TEXT))) = 0
                            THEN 1
                            ELSE 0
                        END
                    ) AS {quote_ident(column.name)}"""
                for column in text_columns
            ]
            empty_row = context.executor.fetch_one(
                f"SELECT {', '.join(empty_select_parts)} FROM {table_name}"
            ) or {}

        # Exact numeric summaries only for numeric columns
        numeric_stats: dict[str, dict[str, Any]] = {}
        for column in columns:
            if not column.is_numeric:
                continue

            quoted = quote_ident(column.name)
            stats_row = context.executor.fetch_one(
                f"""
                SELECT
                    MIN({quoted}) AS min_value,
                    MAX({quoted}) AS max_value,
                    AVG(({quoted})::numeric) AS avg_value,
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY ({quoted})::numeric) AS median_value,
                    STDDEV_POP(({quoted})::numeric) AS stddev_value
                FROM {table_name}
                WHERE {quoted} IS NOT NULL
                """
            ) or {}

            numeric_stats[column.name] = dict(stats_row)

        rows = []
        for column in columns:
            null_count = int(null_row.get(column.name) or 0)
            null_ratio = (null_count / total_rows) if total_rows else None

            if column.is_textual:
                empty_count = int(empty_row.get(column.name) or 0)
                empty_ratio = (empty_count / total_rows) if total_rows else None
                empty_count_display = self._format_int_pt(empty_count)
                empty_ratio_display = self._format_percent_pt(empty_ratio)
            else:
                empty_count_display = "—"
                empty_ratio_display = "—"

            distinct_estimated = (
                self._format_int_pt(column.estimated_cardinality)
                if column.estimated_cardinality is not None
                else "—"
            )

            stats = numeric_stats.get(column.name, {})
            min_value = self._format_scalar_pt(stats.get("min_value")) if column.is_numeric else "—"
            max_value = self._format_scalar_pt(stats.get("max_value")) if column.is_numeric else "—"
            avg_value = self._format_stat_pt(stats.get("avg_value")) if column.is_numeric else "—"
            median_value = self._format_stat_pt(stats.get("median_value")) if column.is_numeric else "—"
            stddev_value = self._format_stat_pt(stats.get("stddev_value")) if column.is_numeric else "—"

            rows.append(
                (
                    column.name,
                    self._format_int_pt(total_rows),
                    self._format_int_pt(null_count),
                    self._format_percent_pt(null_ratio),
                    empty_count_display,
                    empty_ratio_display,
                    distinct_estimated,
                    min_value,
                    max_value,
                    avg_value,
                    median_value,
                    stddev_value,
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
                    widget_id="column-catalog-summary",
                    title="Resumo consolidado por coluna",
                    subtitle="Tabela única com nulidade, strings vazias, cardinalidade estimada e estatísticas numéricas.",
                    columns=(
                        "Coluna",
                        "Total linhas",
                        "Nulos",
                        "% nulos",
                        "Strings vazias",
                        "% strings vazias",
                        "Distintos estimados",
                        "Mínimo",
                        "Máximo",
                        "Média",
                        "Mediana",
                        "Desvio padrão",
                    ),
                    rows=tuple(rows),
                ),
            ),
        )