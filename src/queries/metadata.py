from __future__ import annotations

from . import SqlQuery


def table_columns(*, schema_name: str, table_name: str) -> SqlQuery:
    return SqlQuery(
        sql="""
        SELECT
            c.column_name,
            c.data_type,
            c.udt_name,
            c.is_nullable,
            c.column_default,
            pgd.description AS column_comment
        FROM information_schema.columns c
        LEFT JOIN pg_catalog.pg_namespace pn
            ON pn.nspname = c.table_schema
        LEFT JOIN pg_catalog.pg_class pc
            ON pc.relname = c.table_name
           AND pc.relnamespace = pn.oid
        LEFT JOIN pg_catalog.pg_description pgd
            ON pgd.objoid = pc.oid
           AND pgd.objsubid = c.ordinal_position
        WHERE c.table_schema = :schema_name
          AND c.table_name = :table_name
        ORDER BY c.ordinal_position
        """,
        params={"schema_name": schema_name, "table_name": table_name},
    )


def table_indexes(*, schema_name: str, table_name: str) -> SqlQuery:
    return SqlQuery(
        sql="""
        SELECT
            i.relname AS index_name,
            idx.indisprimary AS is_primary,
            idx.indisunique AS is_unique,
            am.amname AS access_method,
            pg_get_indexdef(idx.indexrelid) AS index_definition
        FROM pg_index idx
        JOIN pg_class t
            ON t.oid = idx.indrelid
        JOIN pg_namespace ns
            ON ns.oid = t.relnamespace
        JOIN pg_class i
            ON i.oid = idx.indexrelid
        JOIN pg_am am
            ON am.oid = i.relam
        WHERE ns.nspname = :schema_name
          AND t.relname = :table_name
        ORDER BY i.relname
        """,
        params={"schema_name": schema_name, "table_name": table_name},
    )


def estimated_row_count(*, schema_name: str, table_name: str) -> SqlQuery:
    return SqlQuery(
        sql="""
        SELECT COALESCE(cls.reltuples, 0)::bigint AS estimated_row_count
        FROM pg_class cls
        JOIN pg_namespace ns
            ON ns.oid = cls.relnamespace
        WHERE ns.nspname = :schema_name
          AND cls.relname = :table_name
        """,
        params={"schema_name": schema_name, "table_name": table_name},
    )


def planner_stats_for_columns(*, schema_name: str, table_name: str) -> SqlQuery:
    return SqlQuery(
        sql="""
        SELECT
            attname AS column_name,
            null_frac,
            n_distinct,
            most_common_vals,
            most_common_freqs,
            histogram_bounds
        FROM pg_stats
        WHERE schemaname = :schema_name
          AND tablename = :table_name
        ORDER BY attname
        """,
        params={"schema_name": schema_name, "table_name": table_name},
    )
