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


def test_checkout_and_return_records_loan_history(client, app):
    login(client, "regularuser", "RegularPass123!")

    client.post(
        "/books/1/checkout",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )
    loan = app.config["REPOSITORY"].loans[0]
    assert loan is not None
    assert loan["user_id"] == 2
    assert loan["returned_at"] is None

    response = client.post(
        "/books/1/return",
        data={"_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )

    assert b"Book returned successfully" in response.data
    assert app.config["REPOSITORY"].loans[0]["returned_at"] is not None


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
    assert any(book["isbn"] == "9781942788331" for book in app.config["REPOSITORY"].books)


def test_xss_payload_is_escaped_in_book_table(client, app):
    app.config["REPOSITORY"].books[0]["title"] = "<script>alert('xss')</script>"

    login(client)
    response = client.get("/books")
    assert b"<script>alert" not in response.data
    assert b"&lt;script&gt;" in response.data
