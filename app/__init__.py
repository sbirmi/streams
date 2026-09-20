"""Application factory for Stream."""

from pathlib import Path

from flask import Flask

from .config import Settings
from .db import Database
from .logging_config import configure_logging
from .repositories import Repository
from .routes import register_routes


SHORTCUT_ACTIONS = {
    "move_left", "move_right", "move_up", "move_down", "move_previous_sibling", "move_next_sibling",
    "edit", "add_comment",
    "open_help", "cancel_command", "zoom_enter", "zoom_back", "delete_stream",
    "delete_comment", "delete_visual", "insert_before", "insert_after", "insert_child", "fold_open",
    "fold_open_all", "fold_close", "fold_close_all", "fold_toggle", "start_move", "start_selection",
    "move_before", "move_after", "move_child", "move_promote",
}


def _shortcut_values(value: str, line: str) -> list[str]:
    """Parse a scalar or a simple YAML flow list without a YAML dependency."""

    value = value.strip()
    if value.startswith("[") != value.endswith("]"):
        raise ValueError(f"malformed shortcut list: {line}")
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip()
        values = [] if not value else [part.strip() for part in value.split(",")]
    else:
        values = [value]
    cleaned = [item.strip().strip("'\"") for item in values]
    if not cleaned or any(not item for item in cleaned):
        raise ValueError(f"shortcut binding is empty: {line}")
    return cleaned


def load_shortcuts(path: str) -> dict[str, list[str]]:
    """Load the strict, flat action-to-bindings shortcut format."""

    shortcuts: dict[str, list[str]] = {}
    try:
        for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            key, separator, value = line.partition(":")
            key = key.strip()
            if not separator or key not in SHORTCUT_ACTIONS or key in shortcuts:
                raise ValueError(f"invalid or duplicate shortcut action: {raw_line.strip()}")
            shortcuts[key] = _shortcut_values(value, raw_line.strip())
        missing = SHORTCUT_ACTIONS - shortcuts.keys()
        if missing:
            raise ValueError(f"shortcut config is missing actions: {', '.join(sorted(missing))}")
        bindings = [binding for values in shortcuts.values() for binding in values]
        if len(bindings) != len(set(bindings)):
            raise ValueError("shortcut bindings must be unique")
    except OSError as error:
        raise ValueError(f"cannot read shortcut config {path}: {error}") from error
    return shortcuts


def create_app(settings: Settings | None = None) -> Flask:
    """Create and configure the Flask application."""

    app_settings = settings or Settings.from_environment()
    configure_logging(app_settings.log_level)

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(
        APP_NAME=app_settings.app_name,
        ENVIRONMENT=app_settings.environment,
        DATABASE_PATH=app_settings.database_path,
        SHORTCUTS=load_shortcuts(app_settings.shortcuts_path),
    )
    database = Database(app_settings.database_path)
    database.migrate()
    app.extensions["repository"] = Repository(database)
    register_routes(app)
    app.logger.info("application configured", extra={"environment": app_settings.environment})
    return app
