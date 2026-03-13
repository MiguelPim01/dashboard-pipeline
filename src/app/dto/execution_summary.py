from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CollectorRunStatus(str, Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CollectorExecutionRecord:
    """Execution status for one collector."""

    collector_name: str
    section_key: str
    status: CollectorRunStatus
    duration_ms: int | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.collector_name.strip():
            raise ValueError("CollectorExecutionRecord collector_name cannot be empty.")
        if not self.section_key.strip():
            raise ValueError("CollectorExecutionRecord section_key cannot be empty.")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("CollectorExecutionRecord duration_ms cannot be negative.")
        object.__setattr__(self, "warnings", tuple(warning for warning in self.warnings if warning.strip()))


@dataclass(frozen=True, slots=True)
class ExecutionSummary:
    """Aggregated execution details for a report generation run."""

    started_at: datetime
    finished_at: datetime
    records: tuple[CollectorExecutionRecord, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        if self.finished_at < self.started_at:
            raise ValueError("ExecutionSummary finished_at cannot be earlier than started_at.")

    @property
    def total_duration_ms(self) -> int:
        return int((self.finished_at - self.started_at).total_seconds() * 1000)

    @property
    def successful_records(self) -> tuple[CollectorExecutionRecord, ...]:
        return tuple(record for record in self.records if record.status is CollectorRunStatus.SUCCESS)

    @property
    def skipped_records(self) -> tuple[CollectorExecutionRecord, ...]:
        return tuple(record for record in self.records if record.status is CollectorRunStatus.SKIPPED)

    @property
    def failed_records(self) -> tuple[CollectorExecutionRecord, ...]:
        return tuple(record for record in self.records if record.status is CollectorRunStatus.FAILED)
