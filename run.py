from app import create_app
from app.config import Settings
from app.db import Database


if __name__ == "__main__":
    settings = Settings.from_environment()
    Database(settings.database_path).migrate()
    create_app(settings).run(host=settings.host, port=settings.port)
