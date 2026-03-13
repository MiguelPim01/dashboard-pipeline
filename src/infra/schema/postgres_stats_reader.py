from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.app.contracts.database import DatabaseExecutor


@dataclass(frozen=True, slots=True)
class PostgresStatsReader:
    """Convenience reader for PostgreSQL relation and planner statistics."""

    def read_table_storage(
        self,
        executor: DatabaseExecutor,
        *,
        schema_name: str,
        table_name: str,
    ) -> dict[str, Any]:
        row = executor.fetch_one(
            _TABLE_STORAGE_QUERY,
            {"schema_name": schema_name, "table_name": table_name},
        )
        return dict(row or {})

    def read_table_runtime_stats(
        self,
        executor: DatabaseExecutor,
        *,
        schema_name: str,
        table_name: str,
    ) -> dict[str, Any]:
        row = executor.fetch_one(
            _TABLE_RUNTIME_STATS_QUERY,
            {"schema_name": schema_name, "table_name": table_name},
        )
        return dict(row or {})

    def is_partitioned_table(
        self,
        executor: DatabaseExecutor,
        *,
        schema_name: str,
        table_name: str,
    ) -> bool:
        value = executor.fetch_scalar(
            _IS_PARTITIONED_QUERY,
            {"schema_name": schema_name, "table_name": table_name},
        )
        return bool(value)


_IS_PARTITIONED_QUERY = """
SELECT EXISTS (
    SELECT 1
    FROM pg_class cls
    JOIN pg_namespace ns
      ON ns.oid = cls.relnamespace
    WHERE ns.nspname = :schema_name
      AND cls.relname = :table_name
      AND cls.relkind = 'p'
)
"""

_TABLE_STORAGE_QUERY = """
WITH target AS (
    SELECT format('%I.%I', :schema_name, :table_name)::regclass AS relid
),
size_targets AS (
    SELECT t.relid
    FROM target t
    WHERE NOT EXISTS (
        SELECT 1
        FROM pg_partitioned_table ppt
        WHERE ppt.partrelid = t.relid
    )

    UNION ALL

    SELECT pt.relid
    FROM target t
    JOIN pg_partitioned_table ppt
      ON ppt.partrelid = t.relid
    JOIN LATERAL pg_partition_tree(t.relid) pt
      ON pt.isleaf
)
SELECT
    COALESCE(SUM(pg_relation_size(relid)), 0) AS table_size_bytes,
    COALESCE(SUM(pg_indexes_size(relid)), 0) AS index_size_bytes,
    COALESCE(SUM(pg_total_relation_size(relid)), 0) AS total_size_bytes
FROM size_targets
"""

_TABLE_RUNTIME_STATS_QUERY = """
WITH target AS (
    SELECT format('%I.%I', :schema_name, :table_name)::regclass AS relid
),
stat_targets AS (
    SELECT t.relid
    FROM target t
    WHERE NOT EXISTS (
        SELECT 1
        FROM pg_partitioned_table ppt
        WHERE ppt.partrelid = t.relid
    )

    UNION ALL

    SELECT pt.relid
    FROM target t
    JOIN pg_partitioned_table ppt
      ON ppt.partrelid = t.relid
    JOIN LATERAL pg_partition_tree(t.relid) pt
      ON pt.isleaf
)
SELECT
    COALESCE(SUM(stat.seq_scan), 0) AS seq_scan,
    COALESCE(SUM(stat.seq_tup_read), 0) AS seq_tup_read,
    COALESCE(SUM(stat.idx_scan), 0) AS idx_scan,
    COALESCE(SUM(stat.idx_tup_fetch), 0) AS idx_tup_fetch,
    COALESCE(SUM(stat.n_live_tup), 0) AS n_live_tup,
    COALESCE(SUM(stat.n_dead_tup), 0) AS n_dead_tup,
    MAX(stat.last_vacuum) AS last_vacuum,
    MAX(stat.last_autovacuum) AS last_autovacuum,
    MAX(stat.last_analyze) AS last_analyze,
    MAX(stat.last_autoanalyze) AS last_autoanalyze
FROM stat_targets t
LEFT JOIN pg_stat_all_tables stat
  ON stat.relid = t.relid
"""