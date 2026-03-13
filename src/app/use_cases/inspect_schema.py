from __future__ import annotations

import logging

from src.app.contracts.database import DatabaseExecutor
from src.app.contracts.schema_reader import SchemaReader
from src.config import AppSettings, DatabaseSettings
from src.domain.models.schema import TableSchema

logger = logging.getLogger(__name__)


class InspectSchemaUseCase:
    """Load table metadata from the configured database adapter."""

    def __init__(self, schema_reader: SchemaReader) -> None:
        self._schema_reader = schema_reader

    def execute(
        self,
        executor: DatabaseExecutor,
        settings: AppSettings | DatabaseSettings,
    ) -> TableSchema:
        db_settings = settings.database if isinstance(settings, AppSettings) else settings
        logger.info("Reading table schema", extra={"schema": db_settings.schema_name, "table": db_settings.table_name})

        table_schema = self._schema_reader.read_table_schema(
            executor,
            schema_name=db_settings.schema_name,
            table_name=db_settings.table_name,
        )

        logger.info("Table schema loaded", extra={"qualified_name": table_schema.qualified_name, "columns": len(table_schema.columns)})
        return table_schema
