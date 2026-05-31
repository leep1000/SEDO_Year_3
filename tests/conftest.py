import pytest

from app import create_app
from app.repository import InMemoryRepository


@pytest.fixture()
def app():
    repo = InMemoryRepository()
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": True,
            "REPOSITORY": repo,
        }
    )
    admin = repo.create_user("adminuser", "AdminPass123!", "admin")
    repo.create_user("regularuser", "RegularPass123!", "regular")
    repo.create_book(
        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "publication_year": 2008,
            "isbn": "9780132350884",
            "created_by_id": admin["id"],
        }
    )
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf_token(client):
    with client.session_transaction() as sess:
        token = sess.get("_csrf_token")
        if not token:
            token = "test-csrf-token"
            sess["_csrf_token"] = token
        return token


def login(client, username="adminuser", password="AdminPass123!"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "_csrf_token": csrf_token(client)},
        follow_redirects=True,
    )
