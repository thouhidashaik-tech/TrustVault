

import os

from flask import Flask, redirect, url_for
from flask_login import current_user
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.config import Config
from app.extensions import db, login_manager, csrf, migrate


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # Load configuration
    app.config.from_object(Config)
    # Apply test configuration before initializing extensions
    if test_config is not None:
        app.config.update(test_config)

    # Validate configuration
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not configured")

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not configured")

    # Create private upload directory
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Flask-Login settings
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    # Import models
    from app import models

    # Register user creation CLI command
    from app.commands import register_commands
    register_commands(app)

    # Import blueprints
    from app.auth.routes import auth_bp
    from app.documents.routes import documents_bp
    from app.admin.routes import admin_bp

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(admin_bp)

    # Temporary home page
    @app.route("/")
    def home():

        if current_user.is_authenticated:
            return (
                f"TrustVault authentication is working. "
                f"Welcome, {current_user.full_name}!"
            )

        return redirect(url_for("auth.login"))

    return app
