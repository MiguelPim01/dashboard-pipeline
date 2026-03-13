from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.dto.collection_context import CollectionContext
    from src.app.dto.metric_result import MetricResult


class CollectorCostLevel(str, Enum):
    """Rough relative execution cost used for planning and filtering."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MetricCollector(ABC):
    """Contract implemented by every report metric collector."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable collector identifier."""

    @property
    @abstractmethod
    def section_key(self) -> str:
        """Report section key the collector contributes to."""

    @property
    def order(self) -> int:
        """Ordering hint for both collector execution and section rendering."""
        return 0

    @property
    def cost_level(self) -> CollectorCostLevel:
        return CollectorCostLevel.MEDIUM

    def is_enabled(self, context: CollectionContext) -> bool:
        """Allow collectors to opt out dynamically for a given execution context."""
        return context.is_section_enabled(self.section_key)

    @abstractmethod
    def collect(self, context: CollectionContext) -> MetricResult:
        """Compute metrics and return a structured application-layer result."""
