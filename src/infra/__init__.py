"""Infrastructure adapters for the PostgreSQL dashboard generator.

This package contains concrete implementations of the application-layer
contracts: SQLAlchemy-based database execution, PostgreSQL schema/statistics
readers, profiling planners, metric collectors, and HTML rendering utilities.
"""

from .collectors import (
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
from .db import EngineFactory, SqlAlchemyExecutor
from .planners import CollectorRegistry, DefaultCollectorRegistry, ProfilingPlanBuilder
from .rendering import ChartSerializer, JinjaReportRenderer
from .schema import PostgresSchemaReader, PostgresStatsReader

__all__ = [
    "CategoricalDistributionCollector",
    "ChartSerializer",
    "CollectorRegistry",
    "ColumnNullsCollector",
    "DataQualityCollector",
    "DefaultCollectorRegistry",
    "EngineFactory",
    "FreshnessCollector",
    "JinjaReportRenderer",
    "OverviewCollector",
    "PostgresSchemaReader",
    "PostgresStatsReader",
    "ProfilingPlanBuilder",
    "SqlAlchemyExecutor",
    "StorageCollector",
    "TextProfileCollector",
    "TimestampProfileCollector",
    "VolumeTrendCollector",
]
