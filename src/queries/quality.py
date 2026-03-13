from __future__ import annotations

from . import SqlQuery, qualified_table_name, quote_ident


def duplicate_groups(
    *,
    schema_name: str,
    table_name: str,
    column_name: str,
    limit_groups: int = 100,
) -> SqlQuery:
    if limit_groups <= 0:
        raise ValueError("limit_groups must be greater than zero.")

    table_ref = qualified_table_name(schema_name, table_name)
    column = quote_ident(column_name)
    return SqlQuery(
        sql=f"""
        SELECT COUNT(*) AS duplicate_groups
        FROM (
            SELECT {column}
            FROM {table_ref}
            WHERE {column} IS NOT NULL
            GROUP BY {column}
            HAVING COUNT(*) > 1
            LIMIT :limit_groups
        ) duplicates
        """,
        params={"limit_groups": int(limit_groups)},
    )


def future_timestamp_rows(
    *,
    schema_name: str,
    table_name: str,
    timestamp_column: str,
    grace_interval: str = "1 day",
) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    ts = quote_ident(timestamp_column)
    return SqlQuery(
        sql=f"""
        SELECT COUNT(*) AS future_rows
        FROM {table_ref}
        WHERE {ts} > NOW() + CAST(:grace_interval AS interval)
        """,
        params={"grace_interval": grace_interval},
    )


def blank_text_rows(
    *,
    schema_name: str,
    table_name: str,
    column_name: str,
) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    column = quote_ident(column_name)
    return SqlQuery(
        sql=f"""
        SELECT COUNT(*) AS blank_rows
        FROM {table_ref}
        WHERE {column} IS NOT NULL
          AND LENGTH(BTRIM({column})) = 0
        """
    )


def critical_column_nulls(
    *,
    schema_name: str,
    table_name: str,
    critical_columns: tuple[str, ...],
) -> SqlQuery:
    if not critical_columns:
        raise ValueError("critical_columns cannot be empty.")

    table_ref = qualified_table_name(schema_name, table_name)
    select_parts = [
        f"SUM(CASE WHEN {quote_ident(column)} IS NULL THEN 1 ELSE 0 END) AS {quote_ident(column)}"
        for column in critical_columns
    ]
    return SqlQuery(sql=f"SELECT {', '.join(select_parts)} FROM {table_ref}")
