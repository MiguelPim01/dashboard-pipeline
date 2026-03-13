from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.schema import TableSchema

from .database import DatabaseExecutor


class SchemaReader(ABC):
    """Reads metadata for the target PostgreSQL table."""

    @abstractmethod
    def read_table_schema(
        self,
        executor: DatabaseExecutor,
        *,
        schema_name: str,
        table_name: str,
    ) -> TableSchema:
        """Return a domain-level :class:`TableSchema` for the configured table."""
