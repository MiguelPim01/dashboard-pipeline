from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from src.app.contracts.collector import CollectorCostLevel
from src.app.dto.collection_context import CollectionContext
from src.domain.models.profiling import ColumnProfilingRule, ProfilingScope, TopValue
from src.domain.models.schema import ColumnSchema


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def qualified_table_name(context: CollectionContext) -> str:
    return f'{quote_ident(context.table_schema.schema_name)}.{quote_ident(context.table_schema.table_name)}'


def select_reference_timestamp_column(context: CollectionContext) -> ColumnSchema | None:
    preferred = ("createdAt", "time", "updatedAt")
    for name in preferred:
        column = context.table_schema.find_column(name)
        if column is not None and column.is_temporal:
            return column
    for column in context.table_schema.columns:
        if column.is_temporal:
            return column
    return None


def build_sampling_clause(rule: ColumnProfilingRule) -> str:
    if rule.scope is ProfilingScope.SAMPLE and rule.sample_rows:
        return f" TABLESAMPLE SYSTEM (1) LIMIT {int(rule.sample_rows)}"
    return ""


def format_human_count(value: Any) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    magnitude = abs(number)
    if magnitude >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    if magnitude >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if magnitude >= 1_000:
        return f"{number / 1_000:.1f}K"
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}"


def format_bytes(value: Any) -> str:
    if value is None:
        return "—"
    try:
        size = float(value)
    except (TypeError, ValueError):
        return str(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    return f"{size:.1f} {units[idx]}"


def format_percent(value: Any) -> str:
    if value is None:
        return "—"
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{ratio * 100:.1f}%"


def format_temporal(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ", timespec="seconds") if isinstance(value, datetime) else value.isoformat()
    return str(value)


def non_empty_rows(rows: Iterable[tuple[Any, ...]]) -> tuple[tuple[Any, ...], ...]:
    return tuple(row for row in rows)


def top_value_from_row(row: dict[str, Any], *, total_rows: int | None = None) -> TopValue:
    count = int(row.get("value_count") or 0)
    ratio = (count / total_rows) if total_rows and total_rows > 0 else None
    return TopValue(value=row.get("value"), count=count, ratio=ratio)


def choose_cost(rule: ColumnProfilingRule) -> CollectorCostLevel:
    if rule.scope is ProfilingScope.EXACT:
        return CollectorCostLevel.HIGH
    if rule.scope is ProfilingScope.SAMPLE:
        return CollectorCostLevel.MEDIUM
    return CollectorCostLevel.LOW
