from __future__ import annotations

from . import SqlQuery, qualified_table_name, quote_ident


_ALLOWED_BUCKETS = {"day", "week", "month", "hour"}


def row_counts_by_time_bucket(
    *,
    schema_name: str,
    table_name: str,
    timestamp_column: str,
    bucket: str = "day",
    limit: int = 365,
) -> SqlQuery:
    if bucket not in _ALLOWED_BUCKETS:
        allowed = ", ".join(sorted(_ALLOWED_BUCKETS))
        raise ValueError(f"bucket must be one of: {allowed}")
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    table_ref = qualified_table_name(schema_name, table_name)
    ts = quote_ident(timestamp_column)
    return SqlQuery(
        sql=f"""
        SELECT
            DATE_TRUNC('{bucket}', {ts}) AS bucket_start,
            COUNT(*) AS row_count
        FROM {table_ref}
        WHERE {ts} IS NOT NULL
        GROUP BY 1
        ORDER BY 1
        LIMIT :limit
        """,
        params={"limit": int(limit)},
    )


def row_counts_by_category_over_time(
    *,
    schema_name: str,
    table_name: str,
    timestamp_column: str,
    category_column: str,
    bucket: str = "day",
    top_categories: int = 5,
    limit: int = 365,
) -> SqlQuery:
    if bucket not in _ALLOWED_BUCKETS:
        allowed = ", ".join(sorted(_ALLOWED_BUCKETS))
        raise ValueError(f"bucket must be one of: {allowed}")
    if top_categories <= 0:
        raise ValueError("top_categories must be greater than zero.")
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    table_ref = qualified_table_name(schema_name, table_name)
    ts = quote_ident(timestamp_column)
    category = quote_ident(category_column)

    return SqlQuery(
        sql=f"""
        WITH ranked_categories AS (
            SELECT {category} AS category_value
            FROM {table_ref}
            WHERE {category} IS NOT NULL
            GROUP BY {category}
            ORDER BY COUNT(*) DESC
            LIMIT :top_categories
        )
        SELECT
            DATE_TRUNC('{bucket}', source.{ts}) AS bucket_start,
            source.{category} AS category_value,
            COUNT(*) AS row_count
        FROM {table_ref} AS source
        INNER JOIN ranked_categories rc
            ON source.{category} = rc.category_value
        WHERE source.{ts} IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 3 DESC, 2
        LIMIT :limit
        """,
        params={"top_categories": int(top_categories), "limit": int(limit)},
    )
