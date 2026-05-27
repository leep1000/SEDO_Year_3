import secrets
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
        return view(**kwargs)

    return wrapped_view


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

