from __future__ import annotations

from . import SqlQuery, qualified_table_name, quote_ident


def null_counts_for_columns(
    *,
    schema_name: str,
    table_name: str,
    columns: tuple[str, ...],
) -> SqlQuery:
    if not columns:
        raise ValueError("columns cannot be empty.")

    table_ref = qualified_table_name(schema_name, table_name)
    select_parts = [
        f"SUM(CASE WHEN {quote_ident(column)} IS NULL THEN 1 ELSE 0 END) AS {quote_ident(column)}"
        for column in columns
    ]
    return SqlQuery(sql=f"SELECT {', '.join(select_parts)} FROM {table_ref}")


def distinct_count_exact(
    *,
    schema_name: str,
    table_name: str,
    column_name: str,
    ignore_nulls: bool = True,
) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    column = quote_ident(column_name)
    where_clause = f"WHERE {column} IS NOT NULL" if ignore_nulls else ""
    return SqlQuery(
        sql=f"""
        SELECT COUNT(DISTINCT {column}) AS distinct_count
        FROM {table_ref}
        {where_clause}
        """
    )


def top_values(
    *,
    schema_name: str,
    table_name: str,
    column_name: str,
    limit: int = 10,
    ignore_nulls: bool = True,
) -> SqlQuery:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    table_ref = qualified_table_name(schema_name, table_name)
    column = quote_ident(column_name)
    where_clause = f"WHERE {column} IS NOT NULL" if ignore_nulls else ""
    return SqlQuery(
        sql=f"""
        SELECT
            {column} AS value,
            COUNT(*) AS value_count
        FROM {table_ref}
        {where_clause}
        GROUP BY {column}
        ORDER BY value_count DESC, value ASC NULLS LAST
        LIMIT :limit
        """,
        params={"limit": int(limit)},
    )


def numeric_summary(
    *,
    schema_name: str,
    table_name: str,
    column_name: str,
) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    column = quote_ident(column_name)
    return SqlQuery(
        sql=f"""
        SELECT
            COUNT(*) FILTER (WHERE {column} IS NOT NULL) AS non_null_rows,
            MIN({column}) AS min_value,
            MAX({column}) AS max_value,
            AVG({column}) AS avg_value,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {column}) AS p50_value,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY {column}) AS p95_value
        FROM {table_ref}
        """
    )


def temporal_summary(
    *,
    schema_name: str,
    table_name: str,
    column_name: str,
) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    column = quote_ident(column_name)
    return SqlQuery(
        sql=f"""
        SELECT
            COUNT(*) FILTER (WHERE {column} IS NOT NULL) AS non_null_rows,
            MIN({column}) AS min_value,
            MAX({column}) AS max_value,
            COUNT(DISTINCT DATE_TRUNC('day', {column})) AS active_days
        FROM {table_ref}
        """
    )


def text_length_summary(
    *,
    schema_name: str,
    table_name: str,
    column_name: str,
    sample_rows: int | None = None,
) -> SqlQuery:
    table_ref = qualified_table_name(schema_name, table_name)
    column = quote_ident(column_name)

    if sample_rows is None:
        source_sql = f"SELECT {column} AS value FROM {table_ref} WHERE {column} IS NOT NULL"
        params: dict[str, object] = {}
    else:
        if sample_rows <= 0:
            raise ValueError("sample_rows must be greater than zero when provided.")
        source_sql = (
            f"SELECT {column} AS value FROM {table_ref} WHERE {column} IS NOT NULL ORDER BY RANDOM() LIMIT :sample_rows"
        )
        params = {"sample_rows": int(sample_rows)}

    return SqlQuery(
        sql=f"""
        WITH source AS (
            {source_sql}
        )
        SELECT
            COUNT(*) AS non_null_rows,
            AVG(LENGTH(value)) AS average_length,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY LENGTH(value)) AS p50_length,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(value)) AS p95_length,
            SUM(CASE WHEN LENGTH(BTRIM(value)) = 0 THEN 1 ELSE 0 END) AS blank_string_rows
        FROM source
        """,
        params=params,
    )
