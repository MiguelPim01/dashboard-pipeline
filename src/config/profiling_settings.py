from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


DEFAULT_CRITICAL_COLUMNS = (
    "id",
    "time",
    "socialNetwork",
    "postType",
    "urlPost",
    "usernameAuthor",
    "message",
    "createdAt",
    "updatedAt",
)

DEFAULT_HEAVY_COLUMNS = (
    "message",
    "sumary",
    "transcription",
    "embedding_openclip_text",
    "embedding_openclip_image",
    "videoComments",
    "words",
    "frequency",
)

DEFAULT_ALLOW_FULL_TABLE_COUNT = True
DEFAULT_SAMPLING_ENABLED = True
DEFAULT_SAMPLE_ROWS = 100_000
DEFAULT_MAX_TOP_VALUES_PER_COLUMN = 10
DEFAULT_MAX_TEXT_COLUMNS_FULL_SCAN = 3
DEFAULT_MAX_DISTINCT_COLUMNS_EXACT = 5
DEFAULT_SKIP_COLUMNS: tuple[str, ...] = ()
DEFAULT_EXACT_DISTINCT_COLUMNS: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProfilingSettings:
    allow_full_table_count: bool = DEFAULT_ALLOW_FULL_TABLE_COUNT
    sampling_enabled: bool = DEFAULT_SAMPLING_ENABLED
    sample_rows: int = DEFAULT_SAMPLE_ROWS
    max_top_values_per_column: int = DEFAULT_MAX_TOP_VALUES_PER_COLUMN
    max_text_columns_full_scan: int = DEFAULT_MAX_TEXT_COLUMNS_FULL_SCAN
    max_distinct_columns_exact: int = DEFAULT_MAX_DISTINCT_COLUMNS_EXACT
    critical_columns: tuple[str, ...] = DEFAULT_CRITICAL_COLUMNS
    heavy_columns: tuple[str, ...] = DEFAULT_HEAVY_COLUMNS
    skip_columns: tuple[str, ...] = DEFAULT_SKIP_COLUMNS
    exact_distinct_columns: tuple[str, ...] = DEFAULT_EXACT_DISTINCT_COLUMNS

    def __post_init__(self) -> None:
        if self.sample_rows <= 0:
            raise ValueError("Profiling sample_rows must be greater than zero.")
        if self.max_top_values_per_column <= 0:
            raise ValueError("Profiling max_top_values_per_column must be greater than zero.")
        if self.max_text_columns_full_scan < 0:
            raise ValueError("Profiling max_text_columns_full_scan cannot be negative.")
        if self.max_distinct_columns_exact < 0:
            raise ValueError("Profiling max_distinct_columns_exact cannot be negative.")

    def is_critical(self, column_name: str) -> bool:
        return column_name in self.critical_columns

    def is_heavy(self, column_name: str) -> bool:
        return column_name in self.heavy_columns

    def should_skip(self, column_name: str) -> bool:
        return column_name in self.skip_columns

    def use_exact_distinct(self, column_name: str) -> bool:
        return column_name in self.exact_distinct_columns

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "ProfilingSettings":
        return cls(
            allow_full_table_count=_get_bool(
                env,
                "PROFILING_ALLOW_FULL_TABLE_COUNT",
                DEFAULT_ALLOW_FULL_TABLE_COUNT,
            ),
            sampling_enabled=_get_bool(
                env,
                "PROFILING_SAMPLING_ENABLED",
                DEFAULT_SAMPLING_ENABLED,
            ),
            sample_rows=_get_int(env, "PROFILING_SAMPLE_ROWS", DEFAULT_SAMPLE_ROWS),
            max_top_values_per_column=_get_int(
                env,
                "PROFILING_MAX_TOP_VALUES_PER_COLUMN",
                DEFAULT_MAX_TOP_VALUES_PER_COLUMN,
            ),
            max_text_columns_full_scan=_get_int(
                env,
                "PROFILING_MAX_TEXT_COLUMNS_FULL_SCAN",
                DEFAULT_MAX_TEXT_COLUMNS_FULL_SCAN,
            ),
            max_distinct_columns_exact=_get_int(
                env,
                "PROFILING_MAX_DISTINCT_COLUMNS_EXACT",
                DEFAULT_MAX_DISTINCT_COLUMNS_EXACT,
            ),
            critical_columns=_get_csv(
                env,
                "PROFILING_CRITICAL_COLUMNS",
                DEFAULT_CRITICAL_COLUMNS,
            ),
            heavy_columns=_get_csv(
                env,
                "PROFILING_HEAVY_COLUMNS",
                DEFAULT_HEAVY_COLUMNS,
            ),
            skip_columns=_get_csv(env, "PROFILING_SKIP_COLUMNS", DEFAULT_SKIP_COLUMNS),
            exact_distinct_columns=_get_csv(
                env,
                "PROFILING_EXACT_DISTINCT_COLUMNS",
                DEFAULT_EXACT_DISTINCT_COLUMNS,
            ),
        )


def _get_int(env: Mapping[str, str], key: str, default: int) -> int:
    value = env.get(key)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {key} must be an integer.") from exc


def _get_bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    value = env.get(key)
    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()
    truthy = {"1", "true", "t", "yes", "y", "on"}
    falsy = {"0", "false", "f", "no", "n", "off"}

    if normalized in truthy:
        return True
    if normalized in falsy:
        return False

    raise ValueError(f"Environment variable {key} must be a boolean value.")


def _get_csv(
    env: Mapping[str, str],
    key: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = env.get(key)
    if value is None or not value.strip():
        return default

    items = tuple(part.strip() for part in value.split(",") if part.strip())
    return items or default