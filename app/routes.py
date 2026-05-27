from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .forms import BookForm, LoginForm, RegisterForm, UserEditForm
from .repository import get_repository
from .security import admin_required, login_required, validate_csrf

bp = Blueprint("library", __name__)


@bp.route("/")
def home():
    return render_template("home.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        validate_csrf()
        repo = get_repository()
        user = repo.find_user_by_username(form.username.data.strip())
        if form.validate() and user and check_password_hash(user["password_hash"], form.password.data):
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash("Login successful.", "success")
            return redirect(url_for("library.books"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    validate_csrf()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("library.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST":
        validate_csrf()
        repo = get_repository()
        username = form.username.data.strip() if form.username.data else ""
        if repo.find_user_by_username(username):
            form.username.errors.append("Username already exists.")
        if form.validate() and not form.username.errors:
            repo.create_user(username, generate_password_hash(form.password.data), "regular")
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("library.login"))
        _flash_form_errors(form)
    return render_template("register.html", form=form)


@bp.route("/books")
@login_required
def books():
    query = request.args.get("q", "").strip()
    repo = get_repository()
    return render_template(
        "books.html",
        books=repo.list_books(query),
        users=repo.list_users(),
        query=query,
    )


@bp.route("/books/add", methods=["POST"])
@login_required
@admin_required
def add_book():
    validate_csrf()
    repo = get_repository()
    form = BookForm(request.form)
    if form.validate():
        values = {
            "title": form.title.data.strip(),
            "author": form.author.data.strip(),
            "publication_year": form.publication_year.data,
            "isbn": form.isbn.data.strip(),
            "created_by_id": session["user_id"],
        }
        _apply_checkout_values(values, form.checked_out_by_id.data, repo)
        repo.create_book(values)
        flash("Book added successfully.", "success")
        return redirect(url_for("library.books"))
    _flash_form_errors(form)
    return redirect(url_for("library.books"))


@bp.route("/books/<int:book_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_book(book_id):
    validate_csrf()
    repo = get_repository()
    book = repo.get_book(book_id)
    if not book:
        abort(404)
    form = BookForm(request.form)
    if form.validate():
        values = {
            "title": form.title.data.strip(),
            "author": form.author.data.strip(),
            "publication_year": form.publication_year.data,
            "isbn": form.isbn.data.strip(),
        }
        _apply_checkout_values(values, form.checked_out_by_id.data, repo)
        repo.update_book(book_id, values)
        flash("Book updated successfully.", "success")
        return redirect(url_for("library.books"))
    _flash_form_errors(form)
    return redirect(url_for("library.books"))


@bp.route("/books/<int:book_id>/checkout", methods=["POST"])
@login_required
def checkout_book(book_id):
    validate_csrf()
    repo = get_repository()
    book = repo.get_book(book_id)
    if not book:
        abort(404)
    if book["status"] == "checked_out":
        flash("This book is already checked out.", "warning")
        return redirect(url_for("library.books"))
    repo.update_book(book_id, {"status": "checked_out", "checked_out_by_id": session["user_id"]})
    repo.create_loan(book_id, session["user_id"], session["user_id"])
    flash("Book checked out successfully.", "success")
    return redirect(url_for("library.books"))


@bp.route("/books/<int:book_id>/return", methods=["POST"])
@login_required
def return_book(book_id):
    validate_csrf()
    repo = get_repository()
    book = repo.get_book(book_id)
    if not book:
        abort(404)
    if book["checked_out_by_id"] != session["user_id"] and session.get("role") != "admin":
        flash("Only the borrower or an admin can return this book.", "danger")
        return redirect(url_for("library.books"))
    repo.close_active_loan(book_id, session["user_id"])
    repo.update_book(book_id, {"status": "available", "checked_out_by_id": None})
    flash("Book returned successfully.", "success")
    return redirect(url_for("library.books"))


@bp.route("/books/<int:book_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_book(book_id):
    validate_csrf()
    repo = get_repository()
    book = repo.get_book(book_id)
    if not book:
        abort(404)
    repo.delete_book(book_id)
    flash(f"Book '{book['title']}' deleted.", "success")
    return redirect(url_for("library.books"))


@bp.route("/users")
@login_required
@admin_required
def users():
    return render_template("users.html", users=get_repository().list_users())


@bp.route("/users/<int:user_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_user(user_id):
    validate_csrf()
    repo = get_repository()
    user = repo.get_user(user_id)
    if not user:
        abort(404)
    form = UserEditForm(request.form)
    if form.validate():
        existing = repo.find_user_by_username(form.username.data.strip())
        if existing and existing["id"] != int(user_id):
            form.username.errors.append("Username already exists.")
        else:
            repo.update_user(user_id, {"username": form.username.data.strip(), "role": form.role.data})
            if session["user_id"] == int(user_id):
                session["username"] = form.username.data.strip()
                session["role"] = form.role.data
            flash("User updated successfully.", "success")
            return redirect(url_for("library.users"))
    _flash_form_errors(form)
    return redirect(url_for("library.users"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    validate_csrf()
    if user_id == session["user_id"]:
        flash("You cannot delete your own admin account while logged in.", "danger")
        return redirect(url_for("library.users"))
    repo = get_repository()
    user = repo.get_user(user_id)
    if not user:
        abort(404)
    repo.delete_user(user_id)
    flash(f"User '{user['username']}' deleted.", "success")
    return redirect(url_for("library.users"))


def _apply_checkout_values(values, checked_out_by_id, repo):
    if checked_out_by_id:
        checked_out_user = repo.get_user(checked_out_by_id)
        if checked_out_user:
            values["checked_out_by_id"] = checked_out_user["id"]
            values["status"] = "checked_out"
            return
    values["checked_out_by_id"] = None
    values["status"] = "available"


def _flash_form_errors(form):
    for field_name, errors in form.errors.items():
        for error in errors:
            flash(f"{field_name.replace('_', ' ').title()}: {error}", "danger")
