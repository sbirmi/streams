"""Runtime configuration for the application shell."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Stream"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 5000
    log_level: str = "INFO"
    database_path: str = "data/stream.sqlite3"

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build settings from environment variables with safe local defaults."""

        return cls(
            app_name=os.getenv("STREAM_APP_NAME", cls.app_name),
            environment=os.getenv("STREAM_ENVIRONMENT", cls.environment),
            host=os.getenv("STREAM_HOST", cls.host),
            port=_positive_int(os.getenv("STREAM_PORT"), cls.port),
            log_level=os.getenv("STREAM_LOG_LEVEL", cls.log_level).upper(),
            database_path=os.getenv("STREAM_DATABASE_PATH", cls.database_path),
        )


def _positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default
