from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from .profiling_settings import ProfilingSettings
from .report_settings import ReportSettings


DEFAULT_DB_SCHEMA_NAME = "public"
DEFAULT_DB_TABLE_NAME = "Post"
DEFAULT_DB_SSL_MODE = "require"
DEFAULT_DB_CONNECT_TIMEOUT_SECONDS = 30
DEFAULT_DB_STATEMENT_TIMEOUT_MS = None
DEFAULT_DB_APPLICATION_NAME = "post-dashboard-report"
DEFAULT_DB_POOL_SIZE = 5
DEFAULT_DB_MAX_OVERFLOW = 2
DEFAULT_DB_ECHO = False


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    url: str
    schema_name: str = DEFAULT_DB_SCHEMA_NAME
    table_name: str = DEFAULT_DB_TABLE_NAME
    ssl_mode: str = DEFAULT_DB_SSL_MODE
    connect_timeout_seconds: int = DEFAULT_DB_CONNECT_TIMEOUT_SECONDS
    statement_timeout_ms: int | None = DEFAULT_DB_STATEMENT_TIMEOUT_MS
    application_name: str = DEFAULT_DB_APPLICATION_NAME
    pool_size: int = DEFAULT_DB_POOL_SIZE
    max_overflow: int = DEFAULT_DB_MAX_OVERFLOW
    echo: bool = DEFAULT_DB_ECHO

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("Database url cannot be empty.")
        if not self.schema_name.strip():
            raise ValueError("Database schema_name cannot be empty.")
        if not self.table_name.strip():
            raise ValueError("Database table_name cannot be empty.")
        if self.connect_timeout_seconds <= 0:
            raise ValueError("Database connect_timeout_seconds must be greater than zero.")
        if self.statement_timeout_ms is not None and self.statement_timeout_ms <= 0:
            raise ValueError("Database statement_timeout_ms must be greater than zero when provided.")
        if self.pool_size < 1:
            raise ValueError("Database pool_size must be at least one.")
        if self.max_overflow < 0:
            raise ValueError("Database max_overflow cannot be negative.")

    @property
    def qualified_table_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"

    @property
    def connect_args(self) -> dict[str, object]:
        args: dict[str, object] = {
            "connect_timeout": self.connect_timeout_seconds,
            "application_name": self.application_name,
            "sslmode": self.ssl_mode,
        }
        if self.statement_timeout_ms is not None:
            args["options"] = f"-c statement_timeout={self.statement_timeout_ms}"
        return args

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "DatabaseSettings":
        return cls(
            url=_require_str(env, "DATABASE_URL"),
            schema_name=_get_str(env, "DB_SCHEMA", DEFAULT_DB_SCHEMA_NAME),
            table_name=_get_str(env, "DB_TABLE", DEFAULT_DB_TABLE_NAME),
            ssl_mode=_get_str(env, "DB_SSL_MODE", DEFAULT_DB_SSL_MODE),
            connect_timeout_seconds=_get_int(
                env,
                "DB_CONNECT_TIMEOUT",
                DEFAULT_DB_CONNECT_TIMEOUT_SECONDS,
            ),
            statement_timeout_ms=_get_optional_int(
                env,
                "DB_STATEMENT_TIMEOUT_MS",
                DEFAULT_DB_STATEMENT_TIMEOUT_MS,
            ),
            application_name=_get_str(
                env,
                "DB_APPLICATION_NAME",
                DEFAULT_DB_APPLICATION_NAME,
            ),
            pool_size=_get_int(env, "DB_POOL_SIZE", DEFAULT_DB_POOL_SIZE),
            max_overflow=_get_int(env, "DB_MAX_OVERFLOW", DEFAULT_DB_MAX_OVERFLOW),
            echo=_get_bool(env, "DB_ECHO", DEFAULT_DB_ECHO),
        )


@dataclass(frozen=True, slots=True)
class AppSettings:
    environment: str
    debug: bool
    base_dir: Path
    database: DatabaseSettings
    report: ReportSettings
    profiling: ProfilingSettings

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "AppSettings":
        return cls(
            environment=_get_str(env, "APP_ENV", "development"),
            debug=_get_bool(env, "APP_DEBUG", False),
            base_dir=Path(_get_str(env, "APP_BASE_DIR", os.getcwd())),
            database=DatabaseSettings.from_env(env),
            report=ReportSettings.from_env(env),
            profiling=ProfilingSettings.from_env(env),
        )


def get_settings(*, env_file: str | Path | None = None, refresh: bool = False) -> AppSettings:
    if refresh:
        _load_settings.cache_clear()
    return _load_settings(str(env_file) if env_file is not None else None)


@lru_cache(maxsize=4)
def _load_settings(env_file: str | None = None) -> AppSettings:
    env = _build_env_mapping(env_file)
    return AppSettings.from_env(env)


def _build_env_mapping(env_file: str | None = None) -> dict[str, str]:
    env: dict[str, str] = dict(os.environ)
    if env_file is not None:
        env.update(_read_env_file(Path(env_file)))
        return env

    default_env_path = Path.cwd() / ".env"
    if default_env_path.exists():
        env.update(_read_env_file(default_env_path))
    return env


def _read_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if not path.exists():
        return parsed

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        parsed[key.strip()] = _strip_quotes(value.strip())

    return parsed


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _require_str(env: Mapping[str, str], key: str) -> str:
    value = env.get(key)
    if value is None or not value.strip():
        raise ValueError(f"Environment variable {key} is required.")
    return value.strip()


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


def _get_optional_int(env: Mapping[str, str], key: str, default: int | None) -> int | None:
    value = env.get(key)
    if value is None:
        return default
    stripped = value.strip()
    if not stripped or stripped.lower() == "none":
        return None
    try:
        return int(stripped)
    except ValueError as exc:
        raise ValueError(f"Environment variable {key} must be an integer or 'none'.") from exc


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