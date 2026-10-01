"""Create and configure the inventory application."""

import os
import secrets
from pathlib import Path

from flask import Flask

from app.db import initialise_database


def create_app(test_config=None):
    """Create the application with configurable settings."""
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        DATABASE=os.environ.get(
            "DATABASE_PATH",
            str(Path(app.instance_path) / "inventory.db"),
        ),
        APP_ENV=os.environ.get("APP_ENV", "development"),
        APP_VERSION=os.environ.get("APP_VERSION", "local"),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )

    if test_config is not None:
        app.config.update(test_config)

    initialise_database(app.config["DATABASE"])

    from app.routes import bp

    app.register_blueprint(bp)

    return app