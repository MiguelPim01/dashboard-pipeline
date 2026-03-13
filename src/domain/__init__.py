"""Pure domain layer for the reporting application.

This package contains immutable models and enums that represent the table
schema, profiling decisions, and report structure. It intentionally has no
knowledge of database engines, SQLAlchemy, HTML templating, or rendering.
"""

from .models.profiling import (
    ColumnProfile,
    ColumnProfilingRule,
    ProfilingPlan,
    ProfilingScope,
    TopValue,
)
from .models.report import Report, ReportMetadata
from .models.schema import ColumnSchema, LogicalColumnType, TableSchema
from .models.section import ReportSection, SectionGroup
from .models.widgets import (
    AlertWidget,
    ChartDataset,
    ChartType,
    ChartWidget,
    KpiCard,
    TableWidget,
    TextBlockWidget,
    Widget,
)

__all__ = [
    "AlertWidget",
    "ChartDataset",
    "ChartType",
    "ChartWidget",
    "ColumnProfile",
    "ColumnProfilingRule",
    "ColumnSchema",
    "KpiCard",
    "LogicalColumnType",
    "ProfilingPlan",
    "ProfilingScope",
    "Report",
    "ReportMetadata",
    "ReportSection",
    "SectionGroup",
    "TableSchema",
    "TableWidget",
    "TextBlockWidget",
    "TopValue",
    "Widget",
]
