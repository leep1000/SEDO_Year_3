import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-secret-key"),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
        WTF_CSRF_ENABLED=True,
        DEBUG=os.getenv("FLASK_ENV") != "production",
    )

    if test_config:
        app.config.update(test_config)

    if "REPOSITORY" not in app.config:
        from .repository import SupabaseRepository

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_anon_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be configured.")
        app.config["REPOSITORY"] = SupabaseRepository(
            supabase_url,
            supabase_anon_key,
            supabase_service_role_key,
        )

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
        print("Run the SQL files in supabase/migrations in order using the Supabase SQL Editor.")

    @app.cli.command("seed-db")
    def seed_db_command():
        from .seed import seed_database

        seed_database()
        print("Database seeded.")

    return app
