from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_REPORT_TITLE = "Post Database Dashboard"
DEFAULT_REPORT_SUBTITLE = "Profiling report for the PostgreSQL Post table"
DEFAULT_REPORT_OUTPUT_DIR = Path("build")
DEFAULT_REPORT_OUTPUT_FILE = "index.html"
DEFAULT_REPORT_TIMEZONE = "UTC"
DEFAULT_ENABLED_SECTIONS = (
    "overview",
    "freshness",
    "volume_trends",
    "storage",
    "quality",
    "column_profiles",
)
DEFAULT_MAX_TABLE_ROWS = 50
DEFAULT_TOP_N_VALUES = 10
DEFAULT_INCLUDE_GENERATED_AT = True
DEFAULT_INCLUDE_EXECUTION_DETAILS = True


@dataclass(frozen=True, slots=True)
class ReportSettings:
    title: str = DEFAULT_REPORT_TITLE
    subtitle: str = DEFAULT_REPORT_SUBTITLE
    output_dir: Path = DEFAULT_REPORT_OUTPUT_DIR
    output_file: str = DEFAULT_REPORT_OUTPUT_FILE
    timezone: str = DEFAULT_REPORT_TIMEZONE
    enabled_sections: tuple[str, ...] = DEFAULT_ENABLED_SECTIONS
    max_table_rows: int = DEFAULT_MAX_TABLE_ROWS
    top_n_values: int = DEFAULT_TOP_N_VALUES
    include_generated_at: bool = DEFAULT_INCLUDE_GENERATED_AT
    include_execution_details: bool = DEFAULT_INCLUDE_EXECUTION_DETAILS

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Report title cannot be empty.")
        if not self.output_file.strip():
            raise ValueError("Report output_file cannot be empty.")
        if self.max_table_rows <= 0:
            raise ValueError("Report max_table_rows must be greater than zero.")
        if self.top_n_values <= 0:
            raise ValueError("Report top_n_values must be greater than zero.")
        if not self.enabled_sections:
            raise ValueError("Report enabled_sections cannot be empty.")

    @property
    def output_path(self) -> Path:
        return self.output_dir / self.output_file

    def is_section_enabled(self, section_key: str) -> bool:
        return section_key in self.enabled_sections

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "ReportSettings":
        return cls(
            title=_get_str(env, "REPORT_TITLE", DEFAULT_REPORT_TITLE),
            subtitle=_get_str(env, "REPORT_SUBTITLE", DEFAULT_REPORT_SUBTITLE),
            output_dir=Path(_get_str(env, "REPORT_OUTPUT_DIR", str(DEFAULT_REPORT_OUTPUT_DIR))),
            output_file=_get_str(env, "REPORT_OUTPUT_FILE", DEFAULT_REPORT_OUTPUT_FILE),
            timezone=_get_str(env, "REPORT_TIMEZONE", DEFAULT_REPORT_TIMEZONE),
            enabled_sections=_get_csv(
                env,
                "REPORT_ENABLED_SECTIONS",
                DEFAULT_ENABLED_SECTIONS,
            ),
            max_table_rows=_get_int(env, "REPORT_MAX_TABLE_ROWS", DEFAULT_MAX_TABLE_ROWS),
            top_n_values=_get_int(env, "REPORT_TOP_N_VALUES", DEFAULT_TOP_N_VALUES),
            include_generated_at=_get_bool(
                env,
                "REPORT_INCLUDE_GENERATED_AT",
                DEFAULT_INCLUDE_GENERATED_AT,
            ),
            include_execution_details=_get_bool(
                env,
                "REPORT_INCLUDE_EXECUTION_DETAILS",
                DEFAULT_INCLUDE_EXECUTION_DETAILS,
            ),
        )


def _get_str(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


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