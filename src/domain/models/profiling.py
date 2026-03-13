from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .schema import LogicalColumnType


class ProfilingScope(str, Enum):
    """How a metric should be computed for a column."""

    METADATA = "metadata"
    EXACT = "exact"
    SAMPLE = "sample"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class TopValue:
    value: Any
    count: int
    ratio: float | None = None

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError("TopValue count cannot be negative.")
        if self.ratio is not None and not 0 <= self.ratio <= 1:
            raise ValueError("TopValue ratio must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class ColumnProfilingRule:
    """Execution plan for profiling a single column."""

    column_name: str
    logical_type: LogicalColumnType
    scope: ProfilingScope
    compute_nulls: bool = True
    compute_distinct: bool = False
    compute_top_values: bool = False
    compute_numeric_summary: bool = False
    compute_temporal_summary: bool = False
    compute_text_summary: bool = False
    sample_rows: int | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.column_name.strip():
            raise ValueError("ColumnProfilingRule column_name cannot be empty.")
        if self.sample_rows is not None and self.sample_rows <= 0:
            raise ValueError("ColumnProfilingRule sample_rows must be greater than zero when provided.")
        object.__setattr__(self, "notes", tuple(note for note in self.notes if note.strip()))


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    """Result of profiling a single column."""

    column_name: str
    logical_type: LogicalColumnType
    scope: ProfilingScope
    row_count: int | None = None
    null_count: int | None = None
    null_ratio: float | None = None
    distinct_count: int | None = None
    distinct_count_is_estimated: bool = False
    top_values: tuple[TopValue, ...] = field(default_factory=tuple)
    min_value: Any | None = None
    max_value: Any | None = None
    average_length: float | None = None
    p50_length: float | None = None
    p95_length: float | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.column_name.strip():
            raise ValueError("ColumnProfile column_name cannot be empty.")
        if self.row_count is not None and self.row_count < 0:
            raise ValueError("ColumnProfile row_count cannot be negative.")
        if self.null_count is not None and self.null_count < 0:
            raise ValueError("ColumnProfile null_count cannot be negative.")
        if self.null_ratio is not None and not 0 <= self.null_ratio <= 1:
            raise ValueError("ColumnProfile null_ratio must be between 0 and 1.")
        if self.distinct_count is not None and self.distinct_count < 0:
            raise ValueError("ColumnProfile distinct_count cannot be negative.")
        if self.average_length is not None and self.average_length < 0:
            raise ValueError("ColumnProfile average_length cannot be negative.")
        if self.p50_length is not None and self.p50_length < 0:
            raise ValueError("ColumnProfile p50_length cannot be negative.")
        if self.p95_length is not None and self.p95_length < 0:
            raise ValueError("ColumnProfile p95_length cannot be negative.")
        object.__setattr__(self, "top_values", tuple(self.top_values))
        object.__setattr__(self, "notes", tuple(note for note in self.notes if note.strip()))


@dataclass(frozen=True, slots=True)
class ProfilingPlan:
    """Collection of per-column rules used by collectors."""

    rules: tuple[ColumnProfilingRule, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", tuple(self.rules))
        seen: set[str] = set()
        duplicates = {rule.column_name for rule in self.rules if rule.column_name in seen or seen.add(rule.column_name)}
        if duplicates:
            duplicate_list = ", ".join(sorted(duplicates))
            raise ValueError(f"ProfilingPlan contains duplicate rules for columns: {duplicate_list}")

    def get_rule(self, column_name: str) -> ColumnProfilingRule:
        for rule in self.rules:
            if rule.column_name == column_name:
                return rule
        raise KeyError(f"Profiling rule for column {column_name!r} does not exist.")

    def find_rule(self, column_name: str) -> ColumnProfilingRule | None:
        for rule in self.rules:
            if rule.column_name == column_name:
                return rule
        return None

    def should_profile(self, column_name: str) -> bool:
        rule = self.find_rule(column_name)
        return rule is not None and rule.scope is not ProfilingScope.SKIP
