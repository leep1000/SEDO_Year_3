import secrets
import time
from functools import wraps

from flask import abort, flash, redirect, request, session, url_for


def current_user_id():
    return session.get("user_id")


def is_admin():
    return session.get("role") == "admin"


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not current_user_id():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("library.login"))
        refresh_supabase_session_if_needed()
        return view(**kwargs)

    return wrapped_view


def refresh_supabase_session_if_needed():
    expires_at = session.get("supabase_expires_at")
    refresh_token = session.get("supabase_refresh_token")
    if not expires_at or not refresh_token or expires_at > int(time.time()) + 60:
        return

    from .repository import get_repository

    refreshed = get_repository().refresh_auth_session(refresh_token)
    if refreshed:
        session["supabase_access_token"] = refreshed["access_token"]
        session["supabase_refresh_token"] = refreshed["refresh_token"]
        session["supabase_expires_at"] = refreshed["expires_at"]


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not is_admin():
            flash("You do not have permission to perform that action.", "danger")
            return redirect(url_for("library.books"))
        return view(**kwargs)

    return wrapped_view


def generate_csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf():
    expected = session.get("_csrf_token")
    supplied = request.form.get("_csrf_token")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        abort(400, description="Invalid CSRF token.")
