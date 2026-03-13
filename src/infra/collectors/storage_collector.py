from __future__ import annotations

from dataclasses import dataclass

from src.app.contracts import CollectorCostLevel, MetricCollector
from src.app.dto import CollectionContext, MetricResult
from src.domain.models.widgets import KpiCard, TableWidget
from src.infra.schema import PostgresStatsReader

from ._helpers import format_bytes, format_human_count


@dataclass(frozen=True, slots=True)
class StorageCollector(MetricCollector):
    stats_reader: PostgresStatsReader

    @property
    def name(self) -> str:
        return "storage"

    @property
    def section_key(self) -> str:
        return "storage"

    @property
    def order(self) -> int:
        return 40

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.LOW

    def collect(self, context: CollectionContext) -> MetricResult:
        storage = self.stats_reader.read_table_storage(
            context.executor,
            schema_name=context.table_schema.schema_name,
            table_name=context.table_schema.table_name,
        )
        runtime = self.stats_reader.read_table_runtime_stats(
            context.executor,
            schema_name=context.table_schema.schema_name,
            table_name=context.table_schema.table_name,
        )

        widgets = [
            KpiCard(widget_id="storage-table", title="Table size", value=format_bytes(storage.get("table_size_bytes"))),
            KpiCard(widget_id="storage-index", title="Index size", value=format_bytes(storage.get("index_size_bytes"))),
            KpiCard(widget_id="storage-total", title="Total size", value=format_bytes(storage.get("total_size_bytes"))),
        ]

        runtime_rows = (
            ("Sequential scans", format_human_count(runtime.get("seq_scan"))),
            ("Index scans", format_human_count(runtime.get("idx_scan"))),
            ("Live tuples", format_human_count(runtime.get("n_live_tup"))),
            ("Dead tuples", format_human_count(runtime.get("n_dead_tup"))),
            ("Last vacuum", str(runtime.get("last_vacuum") or "—")),
            ("Last auto analyze", str(runtime.get("last_autoanalyze") or "—")),
        )
        widgets.append(
            TableWidget(
                widget_id="storage-runtime-stats",
                title="Runtime statistics",
                columns=("Metric", "Value"),
                rows=runtime_rows,
                compact=True,
            )
        )
        
        warnings = []
        if self.stats_reader.is_partitioned_table(
            context.executor,
            schema_name=context.table_schema.schema_name,
            table_name=context.table_schema.table_name,
        ):
            warnings.append(
                "This table is partitioned. Storage and runtime statistics are aggregated from leaf partitions."
            )

        return MetricResult(
            collector_name=self.name,
            section_key=self.section_key,
            section_title="Storage",
            section_subtitle="Physical storage footprint and PostgreSQL runtime statistics.",
            section_order=self.order,
            widgets=tuple(widgets),
            warnings=tuple(warnings)
        )
