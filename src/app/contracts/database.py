from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class DatabaseExecutor(ABC):
    """Abstraction over the database query engine used by collectors.

    The application layer only needs a small read-only surface for dashboard
    generation: scalar values, a single row, or a result set.
    """

    @abstractmethod
    def fetch_scalar(
        self,
        query: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Execute a query and return the first scalar value."""

    @abstractmethod
    def fetch_one(
        self,
        query: str,
        params: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any] | None:
        """Execute a query and return a single row mapping, if any."""

    @abstractmethod
    def fetch_all(
        self,
        query: str,
        params: Mapping[str, Any] | None = None,
    ) -> tuple[Mapping[str, Any], ...]:
        """Execute a query and return all rows as immutable mappings."""

    def close(self) -> None:
        """Optional hook for adapters that manage connections explicitly."""
        return None
