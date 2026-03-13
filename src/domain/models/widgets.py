from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..enums.report_critics import ReportCriticsEnum


class ChartType(str, Enum):
    LINE = "line"
    BAR = "bar"
    DOUGHNUT = "doughnut"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"


@dataclass(frozen=True, slots=True, kw_only=True)
class Widget:
    """Base widget rendered inside a report section."""

    widget_id: str
    title: str
    subtitle: str | None = None

    def __post_init__(self) -> None:
        if not self.widget_id.strip():
            raise ValueError("Widget widget_id cannot be empty.")
        if not self.title.strip():
            raise ValueError("Widget title cannot be empty.")


@dataclass(frozen=True, slots=True, kw_only=True)
class KpiCard(Widget):
    value: str
    delta_label: str | None = None
    trend_direction: str | None = None
    help_text: str | None = None

    def __post_init__(self) -> None:
        Widget.__post_init__(self)
        if not str(self.value).strip():
            raise ValueError("KpiCard value cannot be empty.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ChartDataset:
    label: str
    values: tuple[float | int | None, ...]

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("ChartDataset label cannot be empty.")
        object.__setattr__(self, "values", tuple(self.values))


@dataclass(frozen=True, slots=True, kw_only=True)
class ChartWidget(Widget):
    chart_type: ChartType
    labels: tuple[str, ...]
    datasets: tuple[ChartDataset, ...]
    stacked: bool = False
    height_px: int = 320

    def __post_init__(self) -> None:
        Widget.__post_init__(self)
        object.__setattr__(self, "labels", tuple(self.labels))
        object.__setattr__(self, "datasets", tuple(self.datasets))
        if not self.datasets:
            raise ValueError("ChartWidget datasets cannot be empty.")
        expected_length = len(self.labels)
        for dataset in self.datasets:
            if len(dataset.values) != expected_length:
                raise ValueError(
                    "All ChartWidget datasets must have the same length as labels. "
                    f"Expected {expected_length}, got {len(dataset.values)} for {dataset.label!r}."
                )
        if self.height_px <= 0:
            raise ValueError("ChartWidget height_px must be greater than zero.")


@dataclass(frozen=True, slots=True, kw_only=True)
class TableWidget(Widget):
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...] = field(default_factory=tuple)
    compact: bool = False

    def __post_init__(self) -> None:
        Widget.__post_init__(self)
        object.__setattr__(self, "columns", tuple(self.columns))
        normalized_rows = tuple(tuple(row) for row in self.rows)
        object.__setattr__(self, "rows", normalized_rows)

        if not self.columns:
            raise ValueError("TableWidget columns cannot be empty.")
        column_count = len(self.columns)
        for row in self.rows:
            if len(row) != column_count:
                raise ValueError(
                    "Each TableWidget row must match the number of columns. "
                    f"Expected {column_count}, got {len(row)}."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertWidget(Widget):
    message: str
    critic_level: ReportCriticsEnum = ReportCriticsEnum.NON_CRITICAL
    details: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        Widget.__post_init__(self)
        if not self.message.strip():
            raise ValueError("AlertWidget message cannot be empty.")
        object.__setattr__(self, "details", tuple(detail for detail in self.details if detail.strip()))


@dataclass(frozen=True, slots=True, kw_only=True)
class TextBlockWidget(Widget):
    body: str

    def __post_init__(self) -> None:
        Widget.__post_init__(self)
        if not self.body.strip():
            raise ValueError("TextBlockWidget body cannot be empty.")
