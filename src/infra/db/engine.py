from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from src.config import DatabaseSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EngineFactory:
    """Build SQLAlchemy engines from immutable database settings."""

    settings: DatabaseSettings

    def create(self) -> Any:
        logger.info("Creating SQLAlchemy engine")
        try:
            from sqlalchemy import create_engine
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "SQLAlchemy is required to use EngineFactory. Install it with `pip install sqlalchemy`."
            ) from exc

        connect_args: dict[str, Any] = dict(self.settings.connect_args)
        logger.debug(
            "Engine configuration prepared",
            extra={
                "schema": self.settings.schema_name,
                "table": self.settings.table_name,
                "pool_size": self.settings.pool_size,
                "max_overflow": self.settings.max_overflow,
                "echo": self.settings.echo,
            },
        )

        return create_engine(
            self.settings.url,
            echo=self.settings.echo,
            future=True,
            pool_pre_ping=True,
            pool_size=self.settings.pool_size,
            max_overflow=self.settings.max_overflow,
            connect_args=connect_args,
        )
