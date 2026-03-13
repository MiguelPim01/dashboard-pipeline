"""Application layer for the PostgreSQL dashboard generator.

This package defines the orchestration contracts, runtime DTOs, and use cases
that connect configuration, domain models, infrastructure adapters, and the
final HTML renderer.
"""

from .contracts import CollectorCostLevel, DatabaseExecutor, MetricCollector, ReportRenderer, SchemaReader
from .dto import CollectionContext, CollectorExecutionRecord, CollectorRunStatus, ExecutionSummary, MetricResult
from .use_cases import (
    BuildProfilingPlanUseCase,
    GenerateReportResult,
    GenerateReportUseCase,
    InspectSchemaUseCase,
    ProfilingPlanBuilder,
)

__all__ = [
    "BuildProfilingPlanUseCase",
    "CollectionContext",
    "CollectorCostLevel",
    "CollectorExecutionRecord",
    "CollectorRunStatus",
    "DatabaseExecutor",
    "ExecutionSummary",
    "GenerateReportResult",
    "GenerateReportUseCase",
    "InspectSchemaUseCase",
    "MetricCollector",
    "MetricResult",
    "ProfilingPlanBuilder",
    "ReportRenderer",
    "SchemaReader",
]
