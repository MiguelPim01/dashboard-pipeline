from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from src.domain.models.section import ReportSection
from src.domain.models.widgets import AlertWidget, Widget


@dataclass(frozen=True, slots=True)
class MetricResult:
    """Normalized result returned by a single metric collector."""

    collector_name: str
    section_key: str
    section_title: str
    section_subtitle: str | None = None
    section_order: int = 0
    widgets: tuple[Widget, ...] = field(default_factory=tuple)
    alerts: tuple[AlertWidget, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    execution_duration_ms: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    skipped: bool = False

    def __post_init__(self) -> None:
        if not self.collector_name.strip():
            raise ValueError("MetricResult collector_name cannot be empty.")
        if not self.section_key.strip():
            raise ValueError("MetricResult section_key cannot be empty.")
        if not self.section_title.strip():
            raise ValueError("MetricResult section_title cannot be empty.")
        if self.execution_duration_ms is not None and self.execution_duration_ms < 0:
            raise ValueError("MetricResult execution_duration_ms cannot be negative.")
        object.__setattr__(self, "widgets", tuple(self.widgets))
        object.__setattr__(self, "alerts", tuple(self.alerts))
        object.__setattr__(self, "warnings", tuple(warning for warning in self.warnings if warning.strip()))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def is_empty(self) -> bool:
        return not self.widgets and not self.alerts

    def to_section(self) -> ReportSection:
        return ReportSection(
            key=self.section_key,
            title=self.section_title,
            subtitle=self.section_subtitle,
            order=self.section_order,
            widgets=self.widgets,
            alerts=self.alerts,
        )
