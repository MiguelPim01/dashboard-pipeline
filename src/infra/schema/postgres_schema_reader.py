from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping

from src.app.contracts.database import DatabaseExecutor
from src.app.contracts.schema_reader import SchemaReader
from src.domain.models.schema import ColumnSchema, LogicalColumnType, TableSchema

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PostgresSchemaReader(SchemaReader):
    """Read PostgreSQL table metadata and convert it into domain models."""

    def read_table_schema(
        self,
        executor: DatabaseExecutor,
        *,
        schema_name: str,
        table_name: str,
    ) -> TableSchema:
        logger.debug("Fetching PostgreSQL column metadata", extra={"schema": schema_name, "table": table_name})
        params = {"schema_name": schema_name, "table_name": table_name}
        rows = executor.fetch_all(_COLUMN_METADATA_QUERY, params)
        if not rows:
            logger.error("Table metadata query returned no columns", extra={"schema": schema_name, "table": table_name})
            raise ValueError(f"Table {schema_name}.{table_name} was not found or has no visible columns.")
        
        seen = set()
        duplicates = set()

        for row in rows:
            name = str(row["column_name"])
            if name in seen:
                duplicates.add(name)
            seen.add(name)

        if duplicates:
            logger.error(
                "Duplicate column metadata returned",
                extra={"schema": schema_name, "table": table_name, "duplicates": sorted(duplicates)},
            )
            raise ValueError(
                f"Schema query returned duplicate column metadata rows for: {', '.join(sorted(duplicates))}"
            )

        table_row = executor.fetch_one(_TABLE_METADATA_QUERY, params) or {}
        columns = tuple(self._map_column(row) for row in rows)
        estimated_row_count = self._coerce_non_negative_int(table_row.get("estimated_row_count"))
        table_comment = self._coerce_str(table_row.get("table_comment"))

        logger.info(
            "Schema metadata loaded",
            extra={
                "qualified_name": f"{schema_name}.{table_name}",
                "column_count": len(columns),
                "estimated_row_count": estimated_row_count,
            },
        )

        return TableSchema(
            schema_name=schema_name,
            table_name=table_name,
            columns=columns,
            estimated_row_count=estimated_row_count,
            table_comment=table_comment,
        )

    def _map_column(self, row: Mapping[str, Any]) -> ColumnSchema:
        data_type = self._coerce_str(row.get("data_type")) or "unknown"
        udt_name = self._coerce_str(row.get("udt_name")) or data_type
        db_type = self._normalize_db_type(data_type=data_type, udt_name=udt_name)
        logical_type = self._classify_logical_type(data_type=data_type, udt_name=udt_name)

        estimated_cardinality = None
        n_distinct = row.get("n_distinct")
        if isinstance(n_distinct, (int, float)):
            if n_distinct >= 0:
                estimated_cardinality = int(n_distinct)

        estimated_null_fraction = None
        null_frac = row.get("null_frac")
        if isinstance(null_frac, (int, float)):
            estimated_null_fraction = float(null_frac)

        return ColumnSchema(
            name=self._coerce_str(row.get("column_name")) or "unknown",
            db_type=db_type,
            logical_type=logical_type,
            nullable=(self._coerce_str(row.get("is_nullable")) or "YES").upper() == "YES",
            indexed=bool(row.get("is_indexed")),
            is_primary_key=bool(row.get("is_primary_key")),
            estimated_cardinality=estimated_cardinality,
            estimated_null_fraction=estimated_null_fraction,
            default_expression=self._coerce_str(row.get("column_default")),
            comment=self._coerce_str(row.get("column_comment")),
        )
    
    @staticmethod
    def _coerce_non_negative_int(value: Any) -> int | None:
        coerced = PostgresSchemaReader._coerce_int(value)
        if coerced is None:
            return None
        return coerced if coerced >= 0 else None

    @staticmethod
    def _normalize_db_type(*, data_type: str, udt_name: str) -> str:
        if data_type == "ARRAY":
            return f"{udt_name}[]"
        return udt_name if udt_name and udt_name != data_type else data_type

    @staticmethod
    def _classify_logical_type(*, data_type: str, udt_name: str) -> LogicalColumnType:
        normalized_data_type = (data_type or "").lower()
        normalized_udt = (udt_name or "").lower()

        if normalized_data_type in {"smallint", "integer", "bigint"} or normalized_udt in {"int2", "int4", "int8"}:
            return LogicalColumnType.INTEGER
        if normalized_data_type in {"real", "double precision"} or normalized_udt in {"float4", "float8"}:
            return LogicalColumnType.FLOAT
        if normalized_data_type in {"numeric", "decimal", "money"}:
            return LogicalColumnType.DECIMAL
        if normalized_data_type in {"boolean"} or normalized_udt == "bool":
            return LogicalColumnType.BOOLEAN
        if normalized_data_type in {"date"}:
            return LogicalColumnType.DATE
        if normalized_data_type.startswith("timestamp") or normalized_data_type.startswith("time"):
            return LogicalColumnType.DATETIME
        if normalized_data_type in {"json", "jsonb"} or normalized_udt in {"json", "jsonb"}:
            return LogicalColumnType.JSON
        if normalized_data_type == "array" or normalized_udt.startswith("_"):
            return LogicalColumnType.ARRAY
        if normalized_data_type in {"bytea"}:
            return LogicalColumnType.BINARY
        if normalized_data_type in {"uuid"} or normalized_udt == "uuid":
            return LogicalColumnType.UUID
        if normalized_data_type in {"character varying", "character", "text", "citext", "name"}:
            return LogicalColumnType.TEXT
        if normalized_data_type in {"smallserial", "serial", "bigserial"}:
            return LogicalColumnType.IDENTIFIER
        if normalized_data_type in {"USER-DEFINED".lower(), "enum"}:
            return LogicalColumnType.CATEGORICAL
        return LogicalColumnType.UNKNOWN

    @staticmethod
    def _coerce_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None


_COLUMN_METADATA_QUERY = """
SELECT
    cols.column_name,
    cols.data_type,
    cols.udt_name,
    (cols.is_nullable = 'YES') AS is_nullable,
    cols.ordinal_position,
    pgd.description AS column_comment,
    EXISTS (
        SELECT 1
        FROM pg_index idx
        JOIN pg_class tbl
          ON tbl.oid = idx.indrelid
        JOIN pg_namespace ns
          ON ns.oid = tbl.relnamespace
        JOIN pg_attribute attr
          ON attr.attrelid = tbl.oid
         AND attr.attnum = ANY(idx.indkey)
        WHERE ns.nspname = cols.table_schema
          AND tbl.relname = cols.table_name
          AND attr.attname = cols.column_name
    ) AS is_indexed,
    EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
         AND tc.table_name = kcu.table_name
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = cols.table_schema
          AND tc.table_name = cols.table_name
          AND kcu.column_name = cols.column_name
    ) AS is_primary_key
FROM information_schema.columns cols
LEFT JOIN pg_class cls
  ON cls.relname = cols.table_name
LEFT JOIN pg_namespace ns
  ON ns.oid = cls.relnamespace
 AND ns.nspname = cols.table_schema
LEFT JOIN pg_attribute attr
  ON attr.attrelid = cls.oid
 AND attr.attname = cols.column_name
LEFT JOIN pg_description pgd
  ON pgd.objoid = cls.oid
 AND pgd.objsubid = attr.attnum
WHERE cols.table_schema = :schema_name
  AND cols.table_name = :table_name
  AND ns.nspname = :schema_name
ORDER BY cols.ordinal_position
"""

_TABLE_METADATA_QUERY = """
SELECT
    cls.reltuples::bigint AS estimated_row_count,
    obj_description(cls.oid) AS table_comment
FROM pg_class cls
JOIN pg_namespace ns
  ON ns.oid = cls.relnamespace
WHERE ns.nspname = :schema_name
  AND cls.relname = :table_name
LIMIT 1
"""
