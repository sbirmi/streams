"""Application factory for Stream."""

from flask import Flask

from .config import Settings
from .db import Database
from .logging_config import configure_logging
from .repositories import Repository
from .routes import register_routes


def create_app(settings: Settings | None = None) -> Flask:
    """Create and configure the Flask application."""

    app_settings = settings or Settings.from_environment()
    configure_logging(app_settings.log_level)

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(
        APP_NAME=app_settings.app_name,
        ENVIRONMENT=app_settings.environment,
        DATABASE_PATH=app_settings.database_path,
    )
    database = Database(app_settings.database_path)
    database.migrate()
    app.extensions["repository"] = Repository(database)
    register_routes(app)
    app.logger.info("application configured", extra={"environment": app_settings.environment})
    return app
