"""Application factory for Stream."""

from pathlib import Path

from flask import Flask

from .config import Settings
from .db import Database
from .logging_config import configure_logging
from .repositories import Repository
from .routes import register_routes


DEFAULT_SHORTCUTS = {"insert_before": "i", "insert_after": "o", "insert_child": "O"}


def load_shortcuts(path: str) -> dict[str, str]:
    """Load the deliberately small flat shortcut YAML format without a new dependency."""

    shortcuts = dict(DEFAULT_SHORTCUTS)
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            key, separator, value = line.partition(":")
            if not separator or key.strip() not in DEFAULT_SHORTCUTS:
                raise ValueError(f"invalid shortcut entry: {line}")
            value = value.strip()
            if len(value) != 1:
                raise ValueError(f"shortcut must be one key: {line}")
            shortcuts[key.strip()] = value
    except (OSError, ValueError) as error:
        # Defaults keep a missing or invalid local config from preventing startup.
        import logging
        logging.getLogger(__name__).warning("using default shortcuts: %s", error)
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
