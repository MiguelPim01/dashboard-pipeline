from __future__ import annotations

from dataclasses import dataclass, field

from .widgets import AlertWidget, Widget


@dataclass(frozen=True, slots=True)
class ReportSection:
    """A logical block inside the final dashboard report."""

    key: str
    title: str
    subtitle: str | None = None
    order: int = 0
    widgets: tuple[Widget, ...] = field(default_factory=tuple)
    alerts: tuple[AlertWidget, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("ReportSection key cannot be empty.")
        if not self.title.strip():
            raise ValueError("ReportSection title cannot be empty.")
        object.__setattr__(self, "widgets", tuple(self.widgets))
        object.__setattr__(self, "alerts", tuple(self.alerts))

    @property
    def is_empty(self) -> bool:
        return not self.widgets and not self.alerts


@dataclass(frozen=True, slots=True)
class SectionGroup:
    """Optional grouping for related report sections."""

    key: str
    title: str
    sections: tuple[ReportSection, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("SectionGroup key cannot be empty.")
        if not self.title.strip():
            raise ValueError("SectionGroup title cannot be empty.")
        object.__setattr__(self, "sections", tuple(self.sections))

    @property
    def sorted_sections(self) -> tuple[ReportSection, ...]:
        return tuple(sorted(self.sections, key=lambda section: section.order))
