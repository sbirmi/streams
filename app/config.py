"""Runtime configuration for the application shell."""

from __future__ import annotations

import os
import ast
import re
from dataclasses import dataclass
from pathlib import Path

from .markdown_renderer import ReferenceRule


@dataclass(frozen=True)
class Settings:
    app_name: str = "Stream"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 5000
    log_level: str = "INFO"
    database_path: str = "data/stream.sqlite3"
    shortcuts_path: str = "config/shortcuts.yaml"
    references_path: str = "config/references.yaml"

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
            shortcuts_path=os.getenv("STREAM_SHORTCUTS_PATH", cls.shortcuts_path),
            references_path=os.getenv("STREAM_REFERENCES_PATH", cls.references_path),
        )


def _positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def load_references(path: str) -> list[ReferenceRule]:
    """Load the deliberately small, reviewed references YAML subset."""

    rules: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValueError(f"cannot read reference config {path}: {error}") from error
    for raw_line in lines:
        line = raw_line.split("#", 1)[0].strip()
        if not line or line == "references:":
            continue
        if line.startswith("- "):
            current = {}
            rules.append(current)
            line = line[2:].strip()
        if current is None or ":" not in line:
            raise ValueError(f"invalid reference config line: {raw_line.strip()}")
        key, _, raw_value = line.partition(":")
        key, raw_value = key.strip(), raw_value.strip()
        if key not in {"name", "pattern", "url", "display", "case_sensitive"}:
            raise ValueError(f"unknown reference config field: {key}")
        if raw_value in {"true", "false"}:
            value: object = raw_value == "true"
        else:
            try:
                value = ast.literal_eval(raw_value)
            except (SyntaxError, ValueError):
                value = raw_value
        current[key] = value
    result = []
    for rule in rules:
        required = {"name", "pattern", "url"}
        if not required.issubset(rule) or not all(isinstance(rule[key], str) for key in required):
            raise ValueError("reference rules require string name, pattern, and url")
        try:
            result.append(ReferenceRule(name=rule["name"], pattern=rule["pattern"], url=rule["url"],
                                        display=rule.get("display", "{0}"),
                                        case_sensitive=rule.get("case_sensitive", True)))
        except (TypeError, ValueError, re.error) as error:
            raise ValueError(f"invalid reference rule {rule.get('name', '<unnamed>')}: {error}") from error
    return result
