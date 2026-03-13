from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LogicalColumnType(str, Enum):
    """Logical categories used by collectors and profiling rules."""

    IDENTIFIER = "identifier"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    TEXT = "text"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"
    BINARY = "binary"
    UUID = "uuid"
    UNKNOWN = "unknown"

    @property
    def is_numeric(self) -> bool:
        return self in {self.INTEGER, self.FLOAT, self.DECIMAL}

    @property
    def is_temporal(self) -> bool:
        return self in {self.DATE, self.DATETIME}

    @property
    def is_textual(self) -> bool:
        return self is self.TEXT


@dataclass(frozen=True, slots=True)
class ColumnSchema:
    """Metadata describing a single table column."""

    name: str
    db_type: str
    logical_type: LogicalColumnType = LogicalColumnType.UNKNOWN
    nullable: bool = True
    indexed: bool = False
    is_primary_key: bool = False
    estimated_cardinality: int | None = None
    estimated_null_fraction: float | None = None
    default_expression: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ColumnSchema name cannot be empty.")
        if not self.db_type.strip():
            raise ValueError("ColumnSchema db_type cannot be empty.")
        if self.estimated_cardinality is not None and self.estimated_cardinality < 0:
            raise ValueError("ColumnSchema estimated_cardinality cannot be negative.")
        if self.estimated_null_fraction is not None and not 0 <= self.estimated_null_fraction <= 1:
            raise ValueError("ColumnSchema estimated_null_fraction must be between 0 and 1.")

    @property
    def is_numeric(self) -> bool:
        return self.logical_type.is_numeric

    @property
    def is_temporal(self) -> bool:
        return self.logical_type.is_temporal

    @property
    def is_textual(self) -> bool:
        return self.logical_type.is_textual

    @property
    def is_categorical_candidate(self) -> bool:
        return self.logical_type in {
            LogicalColumnType.CATEGORICAL,
            LogicalColumnType.BOOLEAN,
        }


@dataclass(frozen=True, slots=True)
class TableSchema:
    """Metadata describing the target PostgreSQL table."""

    schema_name: str
    table_name: str
    columns: tuple[ColumnSchema, ...] = field(default_factory=tuple)
    estimated_row_count: int | None = None
    table_comment: str | None = None

    def __post_init__(self) -> None:
        if not self.schema_name.strip():
            raise ValueError("TableSchema schema_name cannot be empty.")
        if not self.table_name.strip():
            raise ValueError("TableSchema table_name cannot be empty.")
        if self.estimated_row_count is not None and self.estimated_row_count < 0:
            raise ValueError("TableSchema estimated_row_count cannot be negative.")

        object.__setattr__(self, "columns", tuple(self.columns))

        seen: set[str] = set()
        duplicates = {column.name for column in self.columns if column.name in seen or seen.add(column.name)}
        if duplicates:
            duplicate_list = ", ".join(sorted(duplicates))
            raise ValueError(f"TableSchema contains duplicate column names: {duplicate_list}")

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)

    @property
    def primary_key_columns(self) -> tuple[ColumnSchema, ...]:
        return tuple(column for column in self.columns if column.is_primary_key)

    def get_column(self, column_name: str) -> ColumnSchema:
        for column in self.columns:
            if column.name == column_name:
                return column
        raise KeyError(f"Column {column_name!r} does not exist in {self.qualified_name}.")

    def find_column(self, column_name: str) -> ColumnSchema | None:
        for column in self.columns:
            if column.name == column_name:
                return column
        return None

    def has_column(self, column_name: str) -> bool:
        return self.find_column(column_name) is not None
