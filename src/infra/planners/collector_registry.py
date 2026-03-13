from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from src.app.contracts import MetricCollector

from ..collectors import (
    CategoricalDistributionCollector,
    ColumnNullsCollector,
    DataQualityCollector,
    FreshnessCollector,
    OverviewCollector,
    StorageCollector,
    TextProfileCollector,
    TimestampProfileCollector,
    VolumeTrendCollector,
)
from ..schema import PostgresStatsReader


@dataclass(slots=True)
class CollectorRegistry:
    """Simple container for concrete collector instances."""

    collectors: tuple[MetricCollector, ...] = field(default_factory=tuple)

    def all(self) -> tuple[MetricCollector, ...]:
        return tuple(self.collectors)

    def enabled_for_sections(self, section_keys: Iterable[str]) -> tuple[MetricCollector, ...]:
        enabled = set(section_keys)
        return tuple(collector for collector in self.collectors if collector.section_key in enabled)


class DefaultCollectorRegistry(CollectorRegistry):
    """Opinionated default collector set for the first report version."""

    def __init__(self) -> None:
        stats_reader = PostgresStatsReader()
        super().__init__(
            collectors=(
                OverviewCollector(),
                FreshnessCollector(),
                VolumeTrendCollector(),
                StorageCollector(stats_reader=stats_reader),
                DataQualityCollector(),
                ColumnNullsCollector(),
                CategoricalDistributionCollector(),
                TextProfileCollector(),
                TimestampProfileCollector(),
            )
        )
