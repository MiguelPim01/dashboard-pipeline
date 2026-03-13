from __future__ import annotations

from collections.abc import Mapping as MappingABC
import logging
from typing import Any, Mapping

from src.app.contracts.database import DatabaseExecutor

logger = logging.getLogger(__name__)


class SqlAlchemyExecutor(DatabaseExecutor):
    """Read-only SQLAlchemy implementation of :class:`DatabaseExecutor`."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        logger.debug("SqlAlchemyExecutor initialized")

    def fetch_scalar(
        self,
        query: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        logger.debug("Executing scalar query")
        text = self._sql_text(query)
        with self._engine.connect() as connection:
            result = connection.execute(text, dict(params or {}))
            return result.scalar()

    def fetch_one(
        self,
        query: str,
        params: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any] | None:
        logger.debug("Executing single-row query")
        text = self._sql_text(query)
        with self._engine.connect() as connection:
            result = connection.execute(text, dict(params or {})).mappings().first()
            return self._freeze_mapping(result) if result is not None else None

    def fetch_all(
        self,
        query: str,
        params: Mapping[str, Any] | None = None,
    ) -> tuple[Mapping[str, Any], ...]:
        logger.debug("Executing multi-row query")
        text = self._sql_text(query)
        with self._engine.connect() as connection:
            result = connection.execute(text, dict(params or {})).mappings().all()
            return tuple(self._freeze_mapping(row) for row in result)

    def close(self) -> None:
        logger.info("Disposing SQLAlchemy engine")
        dispose = getattr(self._engine, "dispose", None)
        if callable(dispose):
            dispose()

    @staticmethod
    def _sql_text(query: str) -> Any:
        try:
            from sqlalchemy import text
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "SQLAlchemy is required to use SqlAlchemyExecutor. Install it with `pip install sqlalchemy`."
            ) from exc
        return text(query)

    @staticmethod
    def _freeze_mapping(value: Mapping[str, Any] | MappingABC[str, Any]) -> Mapping[str, Any]:
        return dict(value)
