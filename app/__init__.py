import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _normalise_database_url(url):
    if url and url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    database_url = _normalise_database_url(
        os.getenv("DATABASE_URL", "sqlite:///library_dev.db")
    )
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-secret-key"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
        WTF_CSRF_ENABLED=True,
        DEBUG=os.getenv("FLASK_ENV") != "production",
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from .routes import bp

    app.register_blueprint(bp)

    from .security import generate_csrf_token

    @app.context_processor
    def inject_template_helpers():
        return {"csrf_token": generate_csrf_token}

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "object-src 'none'; frame-ancestors 'none'",
        )
        return response

    @app.cli.command("init-db")
    def init_db_command():
        from .models import Book, User

        db.create_all()
        print("Database tables created.")

    @app.cli.command("seed-db")
    def seed_db_command():
        from .seed import seed_database

        seed_database()
        print("Database seeded.")

    return app
