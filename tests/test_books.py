from app.models import Book
from app import db

from .conftest import csrf_token, login


def test_regular_user_can_browse_and_checkout_books(client):
    login(client, "regularuser", "RegularPass123!")
    response = client.get("/books")
    assert b"Clean Code" in response.data

    response = client.post(
        "/books/1/checkout",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )
    assert b"Book checked out successfully" in response.data


def test_regular_user_cannot_add_book(client):
    login(client, "regularuser", "RegularPass123!")
    response = client.post(
        "/books/add",
        data={
            "title": "Accelerate",
            "author": "Nicole Forsgren",
            "publication_year": 2018,
            "isbn": "9781942788331",
            "_csrf_token": csrf_token(client),
        },
        follow_redirects=True,
    )
    assert b"You do not have permission" in response.data


def test_admin_can_add_book(client, app):
    login(client)
    response = client.post(
        "/books/add",
        data={
            "title": "Accelerate",
            "author": "Nicole Forsgren",
            "publication_year": 2018,
            "isbn": "9781942788331",
            "_csrf_token": csrf_token(client),
        },
        follow_redirects=True,
    )
    assert b"Book added successfully" in response.data
    with app.app_context():
        assert Book.query.filter_by(isbn="9781942788331").first() is not None


def test_xss_payload_is_escaped_in_book_table(client, app):
    with app.app_context():
        book = Book.query.first()
        book.title = "<script>alert('xss')</script>"
        db.session.commit()

    login(client)
    response = client.get("/books")
    assert b"<script>alert" not in response.data
    assert b"&lt;script&gt;" in response.data
