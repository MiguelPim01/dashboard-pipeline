from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .section import ReportSection
from .widgets import AlertWidget


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    """Top-level metadata displayed in the rendered report."""

    title: str
    subtitle: str | None
    generated_at: datetime
    table_qualified_name: str
    row_count: int | None = None
    execution_duration_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("ReportMetadata title cannot be empty.")
        if not self.table_qualified_name.strip():
            raise ValueError("ReportMetadata table_qualified_name cannot be empty.")
        if self.row_count is not None and self.row_count < 0:
            raise ValueError("ReportMetadata row_count cannot be negative.")
        if self.execution_duration_ms is not None and self.execution_duration_ms < 0:
            raise ValueError("ReportMetadata execution_duration_ms cannot be negative.")


@dataclass(frozen=True, slots=True)
class Report:
    """The full report model consumed by the HTML renderer."""

    metadata: ReportMetadata
    sections: tuple[ReportSection, ...] = field(default_factory=tuple)
    global_alerts: tuple[AlertWidget, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "global_alerts", tuple(self.global_alerts))

    @property
    def sorted_sections(self) -> tuple[ReportSection, ...]:
        return tuple(sorted(self.sections, key=lambda section: section.order))

    def get_section(self, section_key: str) -> ReportSection:
        for section in self.sections:
            if section.key == section_key:
                return section
        raise KeyError(f"Report section {section_key!r} does not exist.")

    def find_section(self, section_key: str) -> ReportSection | None:
        for section in self.sections:
            if section.key == section_key:
                return section
        return None
