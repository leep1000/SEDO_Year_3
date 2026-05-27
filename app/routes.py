from sqlalchemy.exc import IntegrityError

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import db
from .forms import BookForm, LoginForm, RegisterForm, UserEditForm
from .models import Book, User
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
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if form.validate() and user and user.check_password(form.password.data):
            session.clear()
            session.permanent = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
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
        username = form.username.data.strip() if form.username.data else ""
        if User.query.filter_by(username=username).first():
            form.username.errors.append("Username already exists.")
        if form.validate() and not form.username.errors:
            user = User(username=username, role="regular")
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("library.login"))
        _flash_form_errors(form)
    return render_template("register.html", form=form)


@bp.route("/books")
@login_required
def books():
    query = request.args.get("q", "").strip()
    books_query = Book.query.order_by(Book.title.asc())
    if query:
        search = f"%{query}%"
        books_query = books_query.filter(
            db.or_(Book.title.ilike(search), Book.author.ilike(search), Book.isbn.ilike(search))
        )
    return render_template(
        "books.html",
        books=books_query.all(),
        users=User.query.order_by(User.username.asc()).all(),
        query=query,
    )


@bp.route("/books/add", methods=["POST"])
@login_required
@admin_required
def add_book():
    validate_csrf()
    form = BookForm(request.form)
    if form.validate():
        book = Book(
            title=form.title.data.strip(),
            author=form.author.data.strip(),
            publication_year=form.publication_year.data,
            isbn=form.isbn.data.strip(),
            created_by_id=session["user_id"],
        )
        _apply_checkout(book, form.checked_out_by_id.data)
        db.session.add(book)
        if _commit_or_flash("Book added successfully."):
            return redirect(url_for("library.books"))
    _flash_form_errors(form)
    return redirect(url_for("library.books"))


@bp.route("/books/<int:book_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_book(book_id):
    validate_csrf()
    book = db.get_or_404(Book, book_id)
    form = BookForm(request.form)
    if form.validate():
        book.title = form.title.data.strip()
        book.author = form.author.data.strip()
        book.publication_year = form.publication_year.data
        book.isbn = form.isbn.data.strip()
        _apply_checkout(book, form.checked_out_by_id.data)
        if _commit_or_flash("Book updated successfully."):
            return redirect(url_for("library.books"))
    _flash_form_errors(form)
    return redirect(url_for("library.books"))


@bp.route("/books/<int:book_id>/checkout", methods=["POST"])
@login_required
def checkout_book(book_id):
    validate_csrf()
    book = db.get_or_404(Book, book_id)
    if book.status == "checked_out":
        flash("This book is already checked out.", "warning")
        return redirect(url_for("library.books"))
    book.status = "checked_out"
    book.checked_out_by_id = session["user_id"]
    db.session.commit()
    flash("Book checked out successfully.", "success")
    return redirect(url_for("library.books"))


@bp.route("/books/<int:book_id>/return", methods=["POST"])
@login_required
def return_book(book_id):
    validate_csrf()
    book = db.get_or_404(Book, book_id)
    if book.checked_out_by_id != session["user_id"] and session.get("role") != "admin":
        flash("Only the borrower or an admin can return this book.", "danger")
        return redirect(url_for("library.books"))
    book.status = "available"
    book.checked_out_by_id = None
    db.session.commit()
    flash("Book returned successfully.", "success")
    return redirect(url_for("library.books"))


@bp.route("/books/<int:book_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_book(book_id):
    validate_csrf()
    book = db.get_or_404(Book, book_id)
    db.session.delete(book)
    db.session.commit()
    flash(f"Book '{book.title}' deleted.", "success")
    return redirect(url_for("library.books"))


@bp.route("/users")
@login_required
@admin_required
def users():
    return render_template("users.html", users=User.query.order_by(User.username.asc()).all())


@bp.route("/users/<int:user_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_user(user_id):
    validate_csrf()
    user = db.get_or_404(User, user_id)
    form = UserEditForm(request.form)
    if form.validate():
        existing = User.query.filter(User.username == form.username.data.strip(), User.id != user.id).first()
        if existing:
            form.username.errors.append("Username already exists.")
        else:
            user.username = form.username.data.strip()
            user.role = form.role.data
            db.session.commit()
            if session["user_id"] == user.id:
                session["username"] = user.username
                session["role"] = user.role
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
    user = db.get_or_404(User, user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' deleted.", "success")
    return redirect(url_for("library.users"))


def _apply_checkout(book, checked_out_by_id):
    if checked_out_by_id:
        checked_out_user = db.session.get(User, checked_out_by_id)
        if checked_out_user:
            book.checked_out_by_id = checked_out_user.id
            book.status = "checked_out"
            return
    book.checked_out_by_id = None
    book.status = "available"


def _commit_or_flash(success_message):
    try:
        db.session.commit()
        flash(success_message, "success")
        return True
    except IntegrityError:
        db.session.rollback()
        flash("The record could not be saved. Check for duplicate ISBNs or invalid data.", "danger")
        return False


def _flash_form_errors(form):
    for field_name, errors in form.errors.items():
        for error in errors:
            flash(f"{field_name.replace('_', ' ').title()}: {error}", "danger")
