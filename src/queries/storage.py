from __future__ import annotations

from . import SqlQuery, qualified_table_name


def relation_sizes(*, schema_name: str, table_name: str) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    return SqlQuery(
        sql=f"""
        SELECT
            pg_relation_size('{table_ref}') AS table_bytes,
            pg_indexes_size('{table_ref}') AS index_bytes,
            pg_total_relation_size('{table_ref}') AS total_bytes
        """
    )


def table_activity_stats(*, schema_name: str, table_name: str) -> SqlQuery:
    return SqlQuery(
        sql="""
        SELECT
            seq_scan,
            seq_tup_read,
            idx_scan,
            idx_tup_fetch,
            n_tup_ins,
            n_tup_upd,
            n_tup_del,
            n_live_tup,
            n_dead_tup,
            vacuum_count,
            autovacuum_count,
            analyze_count,
            autoanalyze_count,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        WHERE schemaname = :schema_name
          AND relname = :table_name
        """,
        params={"schema_name": schema_name, "table_name": table_name},
    )
