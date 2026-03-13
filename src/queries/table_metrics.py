from __future__ import annotations

from . import SqlQuery, qualified_table_name, quote_ident


def count_rows(*, schema_name: str, table_name: str) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    return SqlQuery(sql=f"SELECT COUNT(*) AS row_count FROM {table_ref}")


def min_max_timestamp(
    *,
    schema_name: str,
    table_name: str,
    timestamp_column: str,
) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    ts = quote_ident(timestamp_column)
    return SqlQuery(
        sql=f"""
        SELECT
            MIN({ts}) AS min_value,
            MAX({ts}) AS max_value
        FROM {table_ref}
        """
    )


def recent_row_counts(
    *,
    schema_name: str,
    table_name: str,
    timestamp_column: str,
    windows_in_days: tuple[int, ...] = (1, 7, 30),
) -> SqlQuery:
    if not windows_in_days:
        raise ValueError("windows_in_days cannot be empty.")
    if any(days <= 0 for days in windows_in_days):
        raise ValueError("All windows_in_days values must be greater than zero.")

    table_ref = qualified_table_name(schema_name, table_name)
    ts = quote_ident(timestamp_column)
    select_parts = []
    for days in windows_in_days:
        alias = f"rows_last_{days}d"
        select_parts.append(
            f"SUM(CASE WHEN {ts} >= NOW() - INTERVAL '{int(days)} days' THEN 1 ELSE 0 END) AS {quote_ident(alias)}"
        )

    return SqlQuery(
        sql=f"""
        SELECT
            {', '.join(select_parts)}
        FROM {table_ref}
        WHERE {ts} IS NOT NULL
        """
    )


def temporal_coverage(
    *,
    schema_name: str,
    table_name: str,
    timestamp_column: str,
) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    ts = quote_ident(timestamp_column)
    return SqlQuery(
        sql=f"""
        SELECT
            COUNT(*) AS non_null_rows,
            MIN({ts}) AS min_value,
            MAX({ts}) AS max_value,
            COUNT(DISTINCT DATE_TRUNC('day', {ts})) AS active_days
        FROM {table_ref}
        WHERE {ts} IS NOT NULL
        """
    )
