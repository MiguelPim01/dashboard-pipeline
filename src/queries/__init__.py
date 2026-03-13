from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class SqlQuery:
    """Small immutable value object representing a parameterized SQL query."""

    sql: str
    params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        sql = self.sql.strip()
        if not sql:
            raise ValueError("SqlQuery.sql cannot be empty.")
        object.__setattr__(self, "sql", sql)
        object.__setattr__(self, "params", dict(self.params))


def quote_ident(identifier: str) -> str:
    """Safely quote a PostgreSQL identifier."""
    if not identifier.strip():
        raise ValueError("Identifier cannot be empty.")
    return '"' + identifier.replace('"', '""') + '"'


def qualified_table_name(schema_name: str, table_name: str) -> str:
    if not schema_name.strip():
        raise ValueError("schema_name cannot be empty.")
    if not table_name.strip():
        raise ValueError("table_name cannot be empty.")
    return f"{quote_ident(schema_name)}.{quote_ident(table_name)}"


def column_list(*columns: str) -> str:
    if not columns:
        raise ValueError("At least one column must be provided.")
    return ", ".join(quote_ident(column) for column in columns)


from . import column_metrics, metadata, quality, storage, table_metrics, trends

__all__ = [
    "SqlQuery",
    "quote_ident",
    "qualified_table_name",
    "column_list",
    "table_metrics",
    "column_metrics",
    "trends",
    "quality",
    "storage",
    "metadata",
]
