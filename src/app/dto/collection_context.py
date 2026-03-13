from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.app.contracts.database import DatabaseExecutor
from src.config import AppSettings
from src.domain.models.profiling import ProfilingPlan
from src.domain.models.schema import TableSchema


@dataclass(slots=True)
class CollectionContext:
    """Shared runtime state passed to every metric collector."""

    settings: AppSettings
    executor: DatabaseExecutor
    table_schema: TableSchema
    profiling_plan: ProfilingPlan | None = None
    run_started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    shared_state: dict[str, Any] = field(default_factory=dict)

    @property
    def database_settings(self):
        return self.settings.database

    @property
    def report_settings(self):
        return self.settings.report

    @property
    def profiling_settings(self):
        return self.settings.profiling

    @property
    def qualified_table_name(self) -> str:
        return self.table_schema.qualified_name

    def is_section_enabled(self, section_key: str) -> bool:
        return self.settings.report.is_section_enabled(section_key)

    def put_shared(self, key: str, value: Any) -> None:
        self.shared_state[key] = value

    def get_shared(self, key: str, default: Any = None) -> Any:
        return self.shared_state.get(key, default)
